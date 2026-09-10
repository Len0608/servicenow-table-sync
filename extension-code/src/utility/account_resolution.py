"""Account Resolution Handler - resolves source objects to ServiceNow customer accounts."""

import logging
from typing import Any, Dict, Optional

from exceptions import ValidationException, MappingException
from utility.connection_servicenow import ServiceNowConnectionHandler

logger = logging.getLogger("UNV")


class AccountResolutionHandler:
    """Resolves source objects to target ServiceNow customer accounts."""

    def __init__(
        self,
        servicenow_conn: ServiceNowConnectionHandler,
        config: Dict[str, Any],
    ) -> None:
        """
        Initialize account resolution handler.

        Args:
            servicenow_conn: ServiceNow connection handler
            config: Account association configuration (account_association_config)
        """
        self._servicenow = servicenow_conn
        self._config = config
        logger.debug("Initialized AccountResolutionHandler")

    def resolve_account(
        self,
        business_service_id: str,
        source_object: Dict[str, Any],
        customer_record_override: Optional[str] = None,
    ) -> str:
        """
        Resolve a source object to a target ServiceNow customer account.

        Args:
            business_service_id: Business Service ID from source object
            source_object: Source object data
            customer_record_override: Explicit customer record sys_id (optional)

        Returns:
            Target account sys_id

        Raises:
            MappingException: If account resolution fails
            ValidationException: If resolution is ambiguous or invalid
        """
        if customer_record_override:
            logger.debug("Using customer record override: %s", customer_record_override)
            return customer_record_override

        try:
            bs_mappings = self._config.get("business_service_to_account", {})

            if business_service_id not in bs_mappings:
                raise MappingException(
                    f"Business Service {business_service_id} not mapped to account"
                )

            account_mapping = bs_mappings[business_service_id]
            account_sys_id = account_mapping.get("account_sys_id")

            if not account_sys_id:
                raise MappingException(
                    f"No account sys_id configured for Business Service {business_service_id}"
                )

            logger.debug(
                "Resolved Business Service %s to account %s",
                business_service_id,
                account_sys_id,
            )
            return account_sys_id

        except MappingException:
            raise
        except Exception as e:
            logger.error("Account resolution failed: %s", str(e))
            raise MappingException(f"Failed to resolve account: {str(e)}")

    def validate_business_service_mapping(
        self, business_service_id: str, uac_conn: Any
    ) -> bool:
        """
        Validate that a Business Service exists and is properly mapped.

        Args:
            business_service_id: Business Service ID to validate
            uac_conn: UAC connection handler

        Returns:
            True if valid and mapped, False otherwise

        Raises:
            ValidationException: If validation fails
        """
        try:
            bs_mappings = self._config.get("business_service_to_account", {})

            if business_service_id not in bs_mappings:
                logger.warning("Business Service %s not in mappings", business_service_id)
                raise ValidationException(
                    f"Business Service {business_service_id} not configured"
                )

            account_sys_id = bs_mappings[business_service_id].get("account_sys_id")

            if not account_sys_id:
                logger.warning("No account mapped for Business Service %s", business_service_id)
                raise ValidationException(
                    f"No account sys_id for Business Service {business_service_id}"
                )

            logger.info(
                "Validated Business Service %s mapping to account %s",
                business_service_id,
                account_sys_id,
            )
            return True

        except ValidationException:
            raise
        except Exception as e:
            logger.error("Business Service validation failed: %s", str(e))
            raise ValidationException(f"Failed to validate Business Service: {str(e)}")

    def resolve_external_key(
        self, customer_table: str, external_key_field: str, external_key_value: str
    ) -> Optional[str]:
        """
        Resolve an external key to a customer account sys_id.

        Args:
            customer_table: Target customer table name
            external_key_field: Field name to match on
            external_key_value: Value to match

        Returns:
            Account sys_id if found, None if not found

        Raises:
            ValidationException: If resolution is ambiguous or fails
        """
        try:
            logger.debug(
                "Resolving external key: table=%s, field=%s, value=%s",
                customer_table,
                external_key_field,
                external_key_value,
            )

            query = f"{external_key_field}={external_key_value}"
            response = self._servicenow.get(customer_table, query=query, limit=2)

            results = response.get("result", [])
            logger.debug("Found %d results for external key lookup", len(results))

            if len(results) == 0:
                logger.warning("No account found for external key %s=%s", external_key_field, external_key_value)
                return None

            if len(results) > 1:
                logger.error("Multiple accounts found for external key %s=%s", external_key_field, external_key_value)
                raise ValidationException(
                    f"Ambiguous external key: {external_key_field}={external_key_value} "
                    f"matches {len(results)} accounts"
                )

            sys_id = results[0].get("sys_id")
            logger.info("Resolved external key to account %s", sys_id)
            return sys_id

        except ValidationException:
            raise
        except Exception as e:
            logger.error("External key resolution failed: %s", str(e))
            raise ValidationException(f"Failed to resolve external key: {str(e)}")
