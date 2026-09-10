"""UAC Connection Handler - manages HTTP connections to UAC controller."""

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
    TemporaryServiceException,
)

logger = logging.getLogger("UNV")


class UACConnectionHandler:
    """Manages authenticated HTTP connections to UAC controller."""

    _MAX_RETRIES = 3
    _BACKOFF_FACTOR = 1.0
    _TIMEOUT_DEFAULT = 30

    def __init__(self, url: str, username: str, password: str) -> None:
        """
        Initialize UAC connection handler.

        Args:
            url: Base URL of UAC controller (e.g., https://uac.example.com:8080)
            username: Username for Basic auth
            password: Password for Basic auth

        Raises:
            NetworkException: If SSL verification fails
        """
        self._url = url.rstrip("/")
        self._session = requests.Session()
        self._session.auth = (username, password)
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

        logger.info("Initialized UAC connection handler: %s", self._url)

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute GET request to UAC endpoint.

        Args:
            endpoint: Endpoint path (e.g., "/resources/agent/list")
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            NetworkException: On connection/timeout errors
            SSLException: On SSL validation errors
            AuthenticationException: On 401/407 errors
            TemporaryServiceException: On 5xx errors
        """
        url = f"{self._url}{endpoint}"
        logger.debug("GET request: %s", url)

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
            raise NetworkException(f"Connection to UAC failed: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.error("Timeout error: %s", str(e))
            raise NetworkException(f"Request to UAC timed out: {str(e)}")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error("Authentication failed: %s", str(e))
                raise AuthenticationException("UAC authentication failed (401)")
            elif response.status_code == 407:
                logger.error("Proxy authentication required: %s", str(e))
                raise AuthenticationException("Proxy authentication required (407)")
            elif 500 <= response.status_code < 600:
                logger.error("Server error: %d", response.status_code)
                raise TemporaryServiceException(f"UAC server error ({response.status_code})")
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Request error: %s", str(e))
            raise NetworkException(f"UAC request failed: {str(e)}")

    def post(
        self, endpoint: str, json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute POST request to UAC endpoint.

        Args:
            endpoint: Endpoint path (e.g., "/resources/task/list")
            json_data: JSON payload

        Returns:
            Parsed JSON response

        Raises:
            NetworkException: On connection/timeout errors
            SSLException: On SSL validation errors
            AuthenticationException: On 401/407 errors
            TemporaryServiceException: On 5xx errors
        """
        url = f"{self._url}{endpoint}"
        logger.debug("POST request: %s", url)

        try:
            response = self._session.post(
                url, json=json_data, timeout=self._timeout
            )
            response.raise_for_status()
            logger.debug("POST response status: %d", response.status_code)
            return response.json()
        except requests.exceptions.SSLError as e:
            logger.error("SSL error: %s", str(e))
            raise SSLException(f"SSL certificate validation failed: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection error: %s", str(e))
            raise NetworkException(f"Connection to UAC failed: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.error("Timeout error: %s", str(e))
            raise NetworkException(f"Request to UAC timed out: {str(e)}")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error("Authentication failed: %s", str(e))
                raise AuthenticationException("UAC authentication failed (401)")
            elif response.status_code == 407:
                logger.error("Proxy authentication required: %s", str(e))
                raise AuthenticationException("Proxy authentication required (407)")
            elif 500 <= response.status_code < 600:
                logger.error("Server error: %d", response.status_code)
                raise TemporaryServiceException(f"UAC server error ({response.status_code})")
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Request error: %s", str(e))
            raise NetworkException(f"UAC request failed: {str(e)}")

    def fetch_paginated(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> list:
        """
        Fetch all paginated results from UAC endpoint.

        Args:
            endpoint: Endpoint path
            params: Query parameters

        Returns:
            List of all items across all pages

        Raises:
            NetworkException: On connection/timeout errors
            TemporaryServiceException: On server errors
        """
        all_items = []
        page = 0
        params = params or {}

        while True:
            params["page"] = page
            logger.debug("Fetching page %d from %s", page, endpoint)

            response = self.get(endpoint, params)

            if "data" in response:
                items = response.get("data", [])
                all_items.extend(items)
                logger.debug("Retrieved %d items on page %d", len(items), page)

                if len(items) == 0 or not response.get("hasMore", False):
                    break

                page += 1
            else:
                break

        logger.info("Fetched total of %d items from %s", len(all_items), endpoint)
        return all_items

    def close(self) -> None:
        """Close the session."""
        self._session.close()
        logger.info("Closed UAC connection handler")
