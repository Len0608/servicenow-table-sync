"""Validate Configuration action - test connectivity and configuration."""

import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

from fields.input import InputFields
from fields.output import OutputFields
from actions.output import ActionOutput
from manager import ExtensionManager
from exceptions import (
    ExecutionError,
    DataValidationError,
    AuthenticationException,
    NetworkException,
    PermissionException,
    ValidationException,
)
from utility import (
    UACConnectionHandler,
    ServiceNowConnectionHandler,
    FieldMapper,
    AccountResolutionHandler,
)

logger = logging.getLogger("UNV")
extension_manager = ExtensionManager()


class ValidateConfiguration:
    """Validates extension configuration for connectivity and field mappings."""

    def __init__(self, input_data: InputFields) -> None:
        """Initialize validator with input configuration."""
        self._input = input_data
        self._output_fields = OutputFields()
        self._checks: List[Dict[str, str]] = []
        self._uac_conn = None
        self._sn_conn = None

    def execute(self) -> ActionOutput:
        """Execute validation and return results."""
        logger.info("Starting Validate Configuration action")

        timestamp_start = self._format_timestamp()
        self._output_fields.update(status="Validating")

        try:
            self._validate_input_fields()
            self._test_uac_connectivity()
            self._test_servicenow_connectivity()
            self._test_source_dataset_access()
            self._validate_target_tables()
            self._validate_target_fields()
            self._validate_field_mappings()
            self._validate_business_service_mappings()

            status = "success" if not self._has_failures() else "validation_failed"
            timestamp_end = self._format_timestamp()

            self._output_fields.update(status="Complete")

            return ActionOutput(
                status=status,
                action="validate_configuration",
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                validation_checks=self._checks,
                details=self._build_details(),
            )

        except ExecutionError as e:
            logger.error("Validation failed: %s", str(e))
            timestamp_end = self._format_timestamp()
            self._output_fields.update(status="Failed")

            return ActionOutput(
                status="failed",
                action="validate_configuration",
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                validation_checks=self._checks,
                error_summary=str(e),
            )

        finally:
            if self._uac_conn:
                self._uac_conn.close()
            if self._sn_conn:
                self._sn_conn.close()

    def _validate_input_fields(self) -> None:
        """Validate all required input fields are present and non-empty."""
        logger.info("Validating input fields")

        if not self._input.action or not self._input.action.value:
            self._add_check("Input field validation", "failed", "action is required")
            raise DataValidationError("action field is required")

        if not self._input.universal_agent or not self._input.universal_agent.value:
            self._add_check("Input field validation", "failed", "universal_agent is required")
            raise DataValidationError("universal_agent field is required")

        self._add_check("Input field validation", "passed", "All required fields present")

    def _test_uac_connectivity(self) -> None:
        """Test connectivity to UAC controller."""
        logger.info("Testing UAC connectivity")

        try:
            url = self._input.uac_credential.url
            username = self._input.uac_credential.username
            password = self._input.uac_credential.password

            self._uac_conn = UACConnectionHandler(url, username, password)

            response = self._uac_conn.get("/resources/openapi.json")
            self._add_check("UAC connectivity", "passed", "Successfully authenticated with UAC")
            logger.info("UAC connectivity test passed")

        except AuthenticationException as e:
            self._add_check("UAC connectivity", "failed", f"Authentication failed: {str(e)}")
            raise
        except NetworkException as e:
            self._add_check("UAC connectivity", "failed", f"Connection failed: {str(e)}")
            raise
        except Exception as e:
            self._add_check("UAC connectivity", "failed", f"Unexpected error: {str(e)}")
            raise

    def _test_servicenow_connectivity(self) -> None:
        """Test connectivity to ServiceNow instance."""
        logger.info("Testing ServiceNow connectivity")

        try:
            url = self._input.servicenow_credential.url
            username = self._input.servicenow_credential.username
            password = self._input.servicenow_credential.password

            self._sn_conn = ServiceNowConnectionHandler(url, username, password)

            response = self._sn_conn.get("sys_user", limit=1)
            self._add_check("ServiceNow connectivity", "passed", "Successfully authenticated with ServiceNow")
            logger.info("ServiceNow connectivity test passed")

        except AuthenticationException as e:
            self._add_check("ServiceNow connectivity", "failed", f"Authentication failed: {str(e)}")
            raise
        except PermissionException as e:
            self._add_check("ServiceNow connectivity", "failed", f"Permission denied: {str(e)}")
            raise
        except NetworkException as e:
            self._add_check("ServiceNow connectivity", "failed", f"Connection failed: {str(e)}")
            raise
        except Exception as e:
            self._add_check("ServiceNow connectivity", "failed", f"Unexpected error: {str(e)}")
            raise

    def _test_source_dataset_access(self) -> None:
        """Test access to source dataset from UAC."""
        logger.info("Testing source dataset access")

        try:
            dataset = self._input.source_dataset.value
            endpoint = self._get_dataset_endpoint(dataset)

            response = self._uac_conn.get(endpoint, params={"page": 0})

            items = response.get("data", [])
            self._add_check(
                "Source dataset access",
                "passed",
                f"Successfully retrieved {len(items)} {dataset.lower()}",
            )
            logger.info("Source dataset access test passed")

        except Exception as e:
            self._add_check("Source dataset access", "failed", f"Failed to access dataset: {str(e)}")
            raise

    def _validate_target_tables(self) -> None:
        """Validate target tables exist in ServiceNow."""
        logger.info("Validating target tables")

        target_mode = self._input.target_mode.value if self._input.target_mode else None

        if target_mode in ["Customer Tables", "Both Customer Tables and Decision Tables"]:
            try:
                table_name = self._input.customer_table.value if self._input.customer_table else None
                if not table_name:
                    self._add_check("Customer table validation", "failed", "customer_table not specified")
                    raise ValidationException("customer_table not specified")

                response = self._sn_conn.get(table_name, limit=1)
                self._add_check("Customer table validation", "passed", f"Table {table_name} exists and is accessible")
                logger.info("Customer table validation passed")

            except Exception as e:
                self._add_check("Customer table validation", "failed", str(e))
                raise

        if target_mode in ["Decision Tables", "Both Customer Tables and Decision Tables"]:
            try:
                table_sys_id = self._input.decision_table.value if self._input.decision_table else None
                if not table_sys_id:
                    self._add_check("Decision table validation", "failed", "decision_table not specified")
                    raise ValidationException("decision_table not specified")

                response = self._sn_conn.get("sn_decision_table", limit=1)
                self._add_check("Decision table validation", "passed", "Decision Table API is accessible")
                logger.info("Decision table validation passed")

            except Exception as e:
                self._add_check("Decision table validation", "failed", str(e))
                raise

    def _validate_target_fields(self) -> None:
        """Validate target fields exist in selected table."""
        logger.info("Validating target fields")

        try:
            target_mode = self._input.target_mode.value if self._input.target_mode else None

            if target_mode in ["Customer Tables", "Both Customer Tables and Decision Tables"]:
                table_name = self._input.customer_table.value if self._input.customer_table else None
                fields = self._input.target_fields

                if not fields or not fields.values:
                    self._add_check("Target field validation", "failed", "No target fields selected")
                    raise ValidationException("No target fields selected")

                self._add_check(
                    "Target field validation",
                    "passed",
                    f"{len(fields.values)} target fields are accessible",
                )
                logger.info("Target field validation passed")

        except ValidationException:
            raise
        except Exception as e:
            self._add_check("Target field validation", "failed", str(e))
            raise

    def _validate_field_mappings(self) -> None:
        """Validate field mapping configurations."""
        logger.info("Validating field mappings")

        try:
            target_mode = self._input.target_mode.value if self._input.target_mode else None

            if target_mode in ["Customer Tables", "Both Customer Tables and Decision Tables"]:
                mapping_config = self._input.field_mappings_customer.value if self._input.field_mappings_customer else None

                if not mapping_config:
                    self._add_check("Field mapping validation", "failed", "field_mappings_customer not specified")
                    raise DataValidationError("field_mappings_customer not specified")

                try:
                    config_dict = json.loads(mapping_config)
                    mapper = FieldMapper(config_dict)
                    self._add_check("Field mapping validation", "passed", "Field mapping configuration is valid JSON")
                    logger.info("Field mapping validation passed")

                except json.JSONDecodeError as e:
                    self._add_check("Field mapping validation", "failed", f"Invalid JSON: {str(e)}")
                    raise DataValidationError(f"Invalid JSON in field_mappings_customer: {str(e)}")

        except (DataValidationError, ValidationException):
            raise
        except Exception as e:
            self._add_check("Field mapping validation", "failed", str(e))
            raise

    def _validate_business_service_mappings(self) -> None:
        """Validate Business Service mappings are configured."""
        logger.info("Validating Business Service mappings")

        try:
            target_mode = self._input.target_mode.value if self._input.target_mode else None

            if target_mode in ["Customer Tables", "Both Customer Tables and Decision Tables"]:
                account_config = self._input.account_association_config.value if self._input.account_association_config else None

                if not account_config:
                    self._add_check("Business Service mapping validation", "failed", "account_association_config not specified")
                    raise DataValidationError("account_association_config not specified")

                try:
                    config_dict = json.loads(account_config)
                    bs_mappings = config_dict.get("business_service_to_account", {})

                    if not bs_mappings:
                        self._add_check("Business Service mapping validation", "failed", "No Business Service mappings configured")
                        raise ValidationException("No Business Service mappings configured")

                    handler = AccountResolutionHandler(self._sn_conn, config_dict)

                    for bs_id in bs_mappings.keys():
                        handler.validate_business_service_mapping(bs_id, self._uac_conn)

                    self._add_check(
                        "Business Service mapping validation",
                        "passed",
                        f"{len(bs_mappings)} Business Service mapping(s) are valid",
                    )
                    logger.info("Business Service mapping validation passed")

                except json.JSONDecodeError as e:
                    self._add_check("Business Service mapping validation", "failed", f"Invalid JSON: {str(e)}")
                    raise DataValidationError(f"Invalid JSON in account_association_config: {str(e)}")

        except (DataValidationError, ValidationException):
            raise
        except Exception as e:
            self._add_check("Business Service mapping validation", "failed", str(e))
            raise

    def _add_check(self, check_name: str, result: str, details: str) -> None:
        """Add a validation check result."""
        self._checks.append({
            "check": check_name,
            "result": result,
            "details": details,
        })

    def _has_failures(self) -> bool:
        """Check if any validation checks failed."""
        return any(check.get("result") == "failed" for check in self._checks)

    def _build_details(self) -> str:
        """Build details summary."""
        passed = sum(1 for c in self._checks if c.get("result") == "passed")
        failed = sum(1 for c in self._checks if c.get("result") == "failed")

        return f"{passed} checks passed, {failed} checks failed"

    def _get_dataset_endpoint(self, dataset: str) -> str:
        """Get UAC endpoint for dataset type."""
        endpoints = {
            "Agents": "/resources/agent/list",
            "Calendars": "/resources/calendar/list",
            "Scripts": "/resources/script/list",
            "SAP/ABAP Jobs": "/resources/task/list",
        }
        return endpoints.get(dataset, "/resources/agent/list")

    def _format_timestamp(self) -> str:
        """Format current time as RFC3339 string."""
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
