"""Decision Table Operations Handler - manages Decision Table row operations."""

import logging
from typing import Any, Dict, Optional, Tuple

from exceptions import MappingException, TemporaryServiceException
from utility.connection_servicenow import ServiceNowConnectionHandler

logger = logging.getLogger("UNV")


class DecisionTableOperationsHandler:
    """Manages Decision Table row creation, updates, and field population."""

    def __init__(
        self,
        servicenow_conn: ServiceNowConnectionHandler,
        config: Dict[str, Any],
    ) -> None:
        """
        Initialize Decision Table operations handler.

        Args:
            servicenow_conn: ServiceNow connection handler
            config: Decision mapping configuration (decision_mapping_config)
        """
        self._servicenow = servicenow_conn
        self._config = config
        self._decision_table_sys_id = config.get("decision_table_sys_id")
        logger.debug("Initialized DecisionTableOperationsHandler")

    def create_composite_key(
        self, business_service_id: str, source_object_id: str
    ) -> str:
        """
        Create a composite key for idempotent row identification.

        Args:
            business_service_id: Business Service ID
            source_object_id: Source object stable ID

        Returns:
            Composite key string
        """
        key = f"{business_service_id}_{source_object_id}"
        logger.debug("Created composite key: %s", key)
        return key

    def build_decision_row(
        self,
        mapped_data: Dict[str, Any],
        source_object: Dict[str, Any],
        composite_key: str,
    ) -> Dict[str, Any]:
        """
        Build a Decision Table row from mapped data.

        Args:
            mapped_data: Mapped source data
            source_object: Original source object
            composite_key: Composite key for the row

        Returns:
            Decision Table row data

        Raises:
            MappingException: If row building fails
        """
        try:
            row = {
                "decision_table": self._decision_table_sys_id,
                "managed_key": composite_key,
            }

            condition_mappings = self._config.get("condition_mappings", {})
            for dt_field_sys_id, source_field in condition_mappings.items():
                if source_field in mapped_data:
                    row[f"condition_{dt_field_sys_id}"] = mapped_data[source_field]

            answer_mappings = self._config.get("answer_mappings", {})
            for dt_field_sys_id, source_field in answer_mappings.items():
                if source_field in mapped_data:
                    row[f"answer_{dt_field_sys_id}"] = mapped_data[source_field]

            logger.debug("Built Decision Table row: %s", row)
            return row

        except Exception as e:
            logger.error("Failed to build Decision Table row: %s", str(e))
            raise MappingException(f"Decision Table row building failed: {str(e)}")

    def find_existing_row(
        self, composite_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find an existing Decision Table row by composite key.

        Args:
            composite_key: Composite key to search for

        Returns:
            Existing row if found, None otherwise

        Raises:
            TemporaryServiceException: If query fails
        """
        try:
            logger.debug("Searching for existing Decision Table row: %s", composite_key)

            query = f"decision_table={self._decision_table_sys_id}^managed_key={composite_key}"
            response = self._servicenow.get(
                "sn_decision_table_row", query=query, limit=1
            )

            results = response.get("result", [])

            if results:
                logger.info("Found existing Decision Table row: %s", composite_key)
                return results[0]

            logger.debug("No existing Decision Table row found: %s", composite_key)
            return None

        except Exception as e:
            logger.error("Failed to find Decision Table row: %s", str(e))
            raise TemporaryServiceException(
                f"Decision Table row lookup failed: {str(e)}"
            )

    def update_row(
        self, row_sys_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a Decision Table row.

        Args:
            row_sys_id: Row sys_id
            updates: Fields to update

        Returns:
            Updated row

        Raises:
            TemporaryServiceException: If update fails
        """
        try:
            logger.info("Updating Decision Table row: %s", row_sys_id)
            response = self._servicenow.patch(
                "sn_decision_table_row", row_sys_id, updates
            )
            logger.debug("Decision Table row updated: %s", row_sys_id)
            return response.get("result", {})

        except Exception as e:
            logger.error("Failed to update Decision Table row: %s", str(e))
            raise TemporaryServiceException(
                f"Decision Table row update failed: {str(e)}"
            )

    def create_row(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new Decision Table row.

        Args:
            row_data: Row data

        Returns:
            Created row

        Raises:
            TemporaryServiceException: If creation fails
        """
        try:
            logger.info("Creating new Decision Table row")
            response = self._servicenow.post("sn_decision_table_row", row_data)
            logger.debug("Decision Table row created")
            return response.get("result", {})

        except Exception as e:
            logger.error("Failed to create Decision Table row: %s", str(e))
            raise TemporaryServiceException(
                f"Decision Table row creation failed: {str(e)}"
            )

    def detect_api_version(self) -> Tuple[str, bool]:
        """
        Detect if native Decision Table API is available (Xanadu+) or fallback to REST adapter.

        Returns:
            Tuple of (api_version, is_native)

        Raises:
            TemporaryServiceException: If detection fails
        """
        try:
            logger.info("Detecting ServiceNow Decision Table API version")

            response = self._servicenow.get("sn_decision_table", limit=1)
            logger.info("Native Decision Table API is available (Xanadu+)")
            return ("xanadu", True)

        except Exception:
            logger.warning("Native Decision Table API not available, using REST adapter")
            return ("rest_adapter", False)
