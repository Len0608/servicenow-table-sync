"""ServiceNow Connection Handler - manages HTTP connections to ServiceNow instance."""

import logging
import os
from typing import Any, Dict, Optional
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests

from exceptions import (
    NetworkException,
    SSLException,
    AuthenticationException,
    PermissionException,
    ConcurrentEditException,
    RateLimitException,
    TemporaryServiceException,
    ResourceNotFoundException,
)

logger = logging.getLogger("UNV")


class ServiceNowConnectionHandler:
    """Manages authenticated HTTP connections to ServiceNow instance."""

    _MAX_RETRIES = 3
    _BACKOFF_FACTOR = 1.0
    _TIMEOUT_DEFAULT = 30
    _TABLE_API_BASE = "/api/now/table"

    def __init__(self, url: str, username: str, password: str) -> None:
        """
        Initialize ServiceNow connection handler.

        Args:
            url: Base URL of ServiceNow instance
            username: Username for Basic auth
            password: Password for Basic auth

        Raises:
            NetworkException: If SSL verification fails
        """
        self._url = url.rstrip("/")
        self._session = requests.Session()
        self._session.auth = (username, password)
        self._session.headers.update({"Accept": "application/json"})
        self._timeout = int(os.environ.get("UE_HTTP_TIMEOUT", self._TIMEOUT_DEFAULT))

        ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE")
        if ca_bundle:
            self._session.verify = ca_bundle

        retry_strategy = Retry(
            total=self._MAX_RETRIES,
            backoff_factor=self._BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

        logger.info("Initialized ServiceNow connection handler: %s", self._url)

    def get(
        self,
        table_name: str,
        query: Optional[str] = None,
        fields: Optional[list] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute GET request to ServiceNow table endpoint.

        Args:
            table_name: ServiceNow table name (e.g., "customer_account")
            query: Encoded query string
            fields: List of field names to retrieve
            limit: Maximum records to return

        Returns:
            Response with "result" key containing list of records

        Raises:
            NetworkException: On connection/timeout errors
            SSLException: On SSL validation errors
            AuthenticationException: On 401/407 errors
            PermissionException: On 403 errors
            ResourceNotFoundException: On 404 errors
            TemporaryServiceException: On 5xx errors
        """
        url = f"{self._url}{self._TABLE_API_BASE}/{table_name}"
        params = {}

        if query:
            params["sysparm_query"] = query
        if fields:
            params["sysparm_fields"] = ",".join(fields)
        if limit:
            params["sysparm_limit"] = limit

        logger.debug("GET table %s with params: %s", table_name, params)

        try:
            response = self._session.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
            logger.debug("GET response status: %d", response.status_code)
            return response.json()
        except requests.exceptions.SSLError as e:
            logger.error("SSL error: %s", str(e))
            raise SSLException(f"SSL certificate validation failed: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection error: %s", str(e))
            raise NetworkException(f"Connection to ServiceNow failed: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.error("Timeout error: %s", str(e))
            raise NetworkException(f"Request to ServiceNow timed out: {str(e)}")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error("Authentication failed: %s", str(e))
                raise AuthenticationException("ServiceNow authentication failed (401)")
            elif response.status_code == 403:
                logger.error("Permission denied: %s", str(e))
                raise PermissionException("ServiceNow access denied (403)")
            elif response.status_code == 404:
                logger.error("Resource not found: %s", str(e))
                raise ResourceNotFoundException(f"Table {table_name} not found (404)")
            elif response.status_code == 407:
                logger.error("Proxy authentication required: %s", str(e))
                raise AuthenticationException("Proxy authentication required (407)")
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded: %s", str(e))
                raise RateLimitException("ServiceNow rate limit exceeded (429)")
            elif 500 <= response.status_code < 600:
                logger.error("Server error: %d", response.status_code)
                raise TemporaryServiceException(
                    f"ServiceNow server error ({response.status_code})"
                )
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Request error: %s", str(e))
            raise NetworkException(f"ServiceNow request failed: {str(e)}")

    def patch(
        self, table_name: str, sys_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute PATCH request to update a ServiceNow record.

        Args:
            table_name: ServiceNow table name
            sys_id: Record system ID
            data: Fields to update

        Returns:
            Updated record

        Raises:
            NetworkException: On connection/timeout errors
            AuthenticationException: On auth errors
            PermissionException: On 403 errors
            ConcurrentEditException: On 409 conflict
            RateLimitException: On rate limit
            TemporaryServiceException: On 5xx errors
        """
        url = f"{self._url}{self._TABLE_API_BASE}/{table_name}/{sys_id}"
        logger.debug("PATCH table %s record %s with data: %s", table_name, sys_id, data)

        try:
            response = self._session.patch(url, json=data, timeout=self._timeout)
            response.raise_for_status()
            logger.debug("PATCH response status: %d", response.status_code)
            return response.json()
        except requests.exceptions.SSLError as e:
            logger.error("SSL error: %s", str(e))
            raise SSLException(f"SSL certificate validation failed: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection error: %s", str(e))
            raise NetworkException(f"Connection to ServiceNow failed: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.error("Timeout error: %s", str(e))
            raise NetworkException(f"Request to ServiceNow timed out: {str(e)}")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error("Authentication failed: %s", str(e))
                raise AuthenticationException("ServiceNow authentication failed (401)")
            elif response.status_code == 403:
                logger.error("Permission denied: %s", str(e))
                raise PermissionException("ServiceNow access denied (403)")
            elif response.status_code == 409:
                logger.warning("Concurrent edit conflict: %s", str(e))
                raise ConcurrentEditException("Record was modified by another user (409)")
            elif response.status_code == 407:
                logger.error("Proxy authentication required: %s", str(e))
                raise AuthenticationException("Proxy authentication required (407)")
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded: %s", str(e))
                raise RateLimitException("ServiceNow rate limit exceeded (429)")
            elif 500 <= response.status_code < 600:
                logger.error("Server error: %d", response.status_code)
                raise TemporaryServiceException(
                    f"ServiceNow server error ({response.status_code})"
                )
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Request error: %s", str(e))
            raise NetworkException(f"ServiceNow request failed: {str(e)}")

    def post(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute POST request to create a ServiceNow record.

        Args:
            table_name: ServiceNow table name
            data: Record fields

        Returns:
            Created record

        Raises:
            NetworkException: On connection/timeout errors
            AuthenticationException: On auth errors
            PermissionException: On 403 errors
            RateLimitException: On rate limit
            TemporaryServiceException: On 5xx errors
        """
        url = f"{self._url}{self._TABLE_API_BASE}/{table_name}"
        logger.debug("POST to table %s with data: %s", table_name, data)

        try:
            response = self._session.post(url, json=data, timeout=self._timeout)
            response.raise_for_status()
            logger.debug("POST response status: %d", response.status_code)
            return response.json()
        except requests.exceptions.SSLError as e:
            logger.error("SSL error: %s", str(e))
            raise SSLException(f"SSL certificate validation failed: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection error: %s", str(e))
            raise NetworkException(f"Connection to ServiceNow failed: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.error("Timeout error: %s", str(e))
            raise NetworkException(f"Request to ServiceNow timed out: {str(e)}")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error("Authentication failed: %s", str(e))
                raise AuthenticationException("ServiceNow authentication failed (401)")
            elif response.status_code == 403:
                logger.error("Permission denied: %s", str(e))
                raise PermissionException("ServiceNow access denied (403)")
            elif response.status_code == 407:
                logger.error("Proxy authentication required: %s", str(e))
                raise AuthenticationException("Proxy authentication required (407)")
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded: %s", str(e))
                raise RateLimitException("ServiceNow rate limit exceeded (429)")
            elif 500 <= response.status_code < 600:
                logger.error("Server error: %d", response.status_code)
                raise TemporaryServiceException(
                    f"ServiceNow server error ({response.status_code})"
                )
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Request error: %s", str(e))
            raise NetworkException(f"ServiceNow request failed: {str(e)}")

    def close(self) -> None:
        """Close the session."""
        self._session.close()
        logger.info("Closed ServiceNow connection handler")
