"""InputFields dataclass for UAC Universal Extension.

Handles input parsing, preprocessing, and validation.
"""

from dataclasses import dataclass, fields as dataclass_fields, asdict
from typing import Optional, Dict, Any
import json
from pathlib import Path

from fields.types import (
    Credential,
    Text,
    Integer,
    Boolean,
    SingleChoice,
    MultiChoice,
)
from fields.output import OutputFields
from exceptions import DataValidationError
from manager import ExtensionManager

extension_manager = ExtensionManager()


@dataclass
class InputFields:
    """Input fields for ServiceNow Table Sync extension."""

    action: Optional[SingleChoice] = None
    universal_agent: Optional[Text] = None
    uac_credential: Optional[Credential] = None
    servicenow_credential: Optional[Credential] = None
    target_mode: Optional[SingleChoice] = None
    source_dataset: Optional[SingleChoice] = None
    source_scope: Optional[SingleChoice] = None
    business_service: Optional[SingleChoice] = None
    source_object: Optional[SingleChoice] = None
    include_calendar_custom_days: Optional[Boolean] = None
    sap_filter_strategy: Optional[SingleChoice] = None
    sap_job_name_filter: Optional[Text] = None
    customer_table: Optional[SingleChoice] = None
    target_fields: Optional[MultiChoice] = None
    decision_table: Optional[SingleChoice] = None
    decision_inputs: Optional[MultiChoice] = None
    decision_results: Optional[MultiChoice] = None
    customer_record: Optional[SingleChoice] = None
    field_mappings_customer: Optional[Text] = None
    account_association_config: Optional[Text] = None
    decision_mapping_config: Optional[Text] = None
    http_timeout_seconds: Optional[Integer] = None
    output_verbosity: Optional[SingleChoice] = None
    previous_output: Optional[OutputFields] = None
    _skip_validation: bool = False

    @staticmethod
    def preprocess_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess UAC fields before creating InputFields instance.

        Handles:
        - Filtering out flattened credential fields (dotted notation)
        - Converting single-item lists to values
        - Converting script field paths to Path objects
        - Extracting previous output fields into OutputFields instance

        Args:
            fields: Raw fields dictionary from UAC

        Returns:
            Processed fields dictionary safe for InputFields(**processed)
        """
        processed = {}
        output_fields_data = {}

        # Get OutputFields field names for automatic detection
        output_field_names = {f.name for f in dataclass_fields(OutputFields)}

        for key, value in fields.items():
            # Skip flattened credential fields (e.g., "api_credential.user")
            if "." in key:
                continue

            # Check if this field belongs to OutputFields (previous run data)
            if key in output_field_names and key != "_skip_validation":
                output_fields_data[key] = value
                continue

            # Convert single-item lists to values
            if isinstance(value, list) and len(value) == 1:
                value = value[0]

            processed[key] = value

        # Create OutputFields if previous output data exists
        if output_fields_data:
            try:
                processed["previous_output"] = OutputFields(**output_fields_data)
            except Exception:
                # If OutputFields construction fails, skip it
                pass

        return processed

    def __post_init__(self):
        """Validate all fields after initialization."""
        if self._skip_validation:
            return

        # Validate all fields
        self._validate_action()
        self._validate_universal_agent()
        self._validate_credentials()
        self._validate_target_mode()
        self._validate_source_dataset()
        self._validate_source_scope()
        self._validate_business_service()
        self._validate_source_object()
        self._validate_include_calendar_custom_days()
        self._validate_sap_filter_strategy()
        self._validate_sap_job_name_filter()
        self._validate_customer_table()
        self._validate_target_fields()
        self._validate_decision_table()
        self._validate_decision_inputs()
        self._validate_decision_results()
        self._validate_customer_record()
        self._validate_field_mappings_customer()
        self._validate_account_association_config()
        self._validate_decision_mapping_config()
        self._validate_http_timeout_seconds()
        self._validate_output_verbosity()

        # Raise all collected errors at once
        if extension_manager.has_errors():
            raise DataValidationError(
                f"{extension_manager.error_count()} validation error(s)"
            )

    def _validate_action(self):
        """Validate action field."""
        if self.action is None:
            exc = DataValidationError("action is required")
            extension_manager.add_error(exc, field="action")
            return

        valid_actions = ["Validate Configuration", "Preview", "Synchronize"]
        if self.action.value not in valid_actions:
            exc = DataValidationError(
                f"action must be one of {valid_actions}, got {self.action.value}"
            )
            extension_manager.add_error(exc, field="action", value=self.action.value)

    def _validate_universal_agent(self):
        """Validate universal_agent field."""
        if self.universal_agent is None:
            exc = DataValidationError("universal_agent is required")
            extension_manager.add_error(exc, field="universal_agent")
            return

        if not self.universal_agent.value or self.universal_agent.value == "":
            exc = DataValidationError("universal_agent must not be empty")
            extension_manager.add_error(exc, field="universal_agent")

    def _validate_credentials(self):
        """Validate credential fields."""
        if self.uac_credential is None:
            exc = DataValidationError("uac_credential is required")
            extension_manager.add_error(exc, field="uac_credential")

        if self.servicenow_credential is None:
            exc = DataValidationError("servicenow_credential is required")
            extension_manager.add_error(exc, field="servicenow_credential")

    def _validate_target_mode(self):
        """Validate target_mode field."""
        if self.target_mode is None:
            exc = DataValidationError("target_mode is required")
            extension_manager.add_error(exc, field="target_mode")
            return

        valid_modes = [
            "Customer Tables",
            "Decision Tables",
            "Both Customer Tables and Decision Tables",
        ]
        if self.target_mode.value not in valid_modes:
            exc = DataValidationError(
                f"target_mode must be one of {valid_modes}, got {self.target_mode.value}"
            )
            extension_manager.add_error(exc, field="target_mode", value=self.target_mode.value)

    def _validate_source_dataset(self):
        """Validate source_dataset field."""
        if self.source_dataset is None:
            exc = DataValidationError("source_dataset is required")
            extension_manager.add_error(exc, field="source_dataset")
            return

        valid_datasets = ["Agents", "Calendars", "Scripts", "SAP/ABAP Jobs"]
        if self.source_dataset.value not in valid_datasets:
            exc = DataValidationError(
                f"source_dataset must be one of {valid_datasets}, got {self.source_dataset.value}"
            )
            extension_manager.add_error(
                exc, field="source_dataset", value=self.source_dataset.value
            )

    def _validate_source_scope(self):
        """Validate source_scope field."""
        if self.source_scope is None:
            exc = DataValidationError("source_scope is required")
            extension_manager.add_error(exc, field="source_scope")
            return

        valid_scopes = ["All Objects", "By Business Service", "Selected Object"]
        if self.source_scope.value not in valid_scopes:
            exc = DataValidationError(
                f"source_scope must be one of {valid_scopes}, got {self.source_scope.value}"
            )
            extension_manager.add_error(
                exc, field="source_scope", value=self.source_scope.value
            )

    def _validate_business_service(self):
        """Validate business_service (conditional on source_scope)."""
        if (
            self.source_scope
            and self.source_scope.value == "By Business Service"
        ):
            if self.business_service is None or self.business_service.is_empty():
                exc = DataValidationError(
                    "business_service is required when source_scope is 'By Business Service'"
                )
                extension_manager.add_error(exc, field="business_service")

    def _validate_source_object(self):
        """Validate source_object (conditional on source_scope)."""
        if self.source_scope and self.source_scope.value == "Selected Object":
            if self.source_object is None or self.source_object.is_empty():
                exc = DataValidationError(
                    "source_object is required when source_scope is 'Selected Object'"
                )
                extension_manager.add_error(exc, field="source_object")

    def _validate_include_calendar_custom_days(self):
        """Validate include_calendar_custom_days (conditional on source_dataset)."""
        # No validation needed - UAC enforces Boolean type
        pass

    def _validate_sap_filter_strategy(self):
        """Validate sap_filter_strategy (conditional on source_dataset)."""
        if self.source_dataset and self.source_dataset.value == "SAP/ABAP Jobs":
            if self.sap_filter_strategy is None:
                exc = DataValidationError(
                    "sap_filter_strategy is required when source_dataset is 'SAP/ABAP Jobs'"
                )
                extension_manager.add_error(exc, field="sap_filter_strategy")
            elif self.sap_filter_strategy.value not in [
                "By Business Service and Type",
                "By Job Name Partial Match",
                "All SAP Tasks",
            ]:
                exc = DataValidationError(
                    f"Invalid sap_filter_strategy value: {self.sap_filter_strategy.value}"
                )
                extension_manager.add_error(
                    exc, field="sap_filter_strategy", value=self.sap_filter_strategy.value
                )

    def _validate_sap_job_name_filter(self):
        """Validate sap_job_name_filter (conditional on sap_filter_strategy)."""
        if (
            self.sap_filter_strategy
            and self.sap_filter_strategy.value == "By Job Name Partial Match"
        ):
            if (
                self.sap_job_name_filter is None
                or not self.sap_job_name_filter.value
                or self.sap_job_name_filter.value == ""
            ):
                exc = DataValidationError(
                    "sap_job_name_filter is required when sap_filter_strategy is 'By Job Name Partial Match'"
                )
                extension_manager.add_error(exc, field="sap_job_name_filter")

    def _validate_customer_table(self):
        """Validate customer_table (conditional on target_mode)."""
        if self.target_mode and self.target_mode.value in [
            "Customer Tables",
            "Both Customer Tables and Decision Tables",
        ]:
            if self.customer_table is None or self.customer_table.is_empty():
                exc = DataValidationError(
                    "customer_table is required when target_mode includes 'Customer Tables'"
                )
                extension_manager.add_error(exc, field="customer_table")

    def _validate_target_fields(self):
        """Validate target_fields (conditional on target_mode)."""
        if self.target_mode and self.target_mode.value in [
            "Customer Tables",
            "Both Customer Tables and Decision Tables",
        ]:
            if self.target_fields is None or self.target_fields.is_empty():
                exc = DataValidationError(
                    "target_fields must have at least one selection when target_mode includes 'Customer Tables'"
                )
                extension_manager.add_error(exc, field="target_fields")

    def _validate_decision_table(self):
        """Validate decision_table (conditional on target_mode)."""
        if self.target_mode and self.target_mode.value in [
            "Decision Tables",
            "Both Customer Tables and Decision Tables",
        ]:
            if self.decision_table is None or self.decision_table.is_empty():
                exc = DataValidationError(
                    "decision_table is required when target_mode includes 'Decision Tables'"
                )
                extension_manager.add_error(exc, field="decision_table")

    def _validate_decision_inputs(self):
        """Validate decision_inputs (conditional on target_mode)."""
        if self.target_mode and self.target_mode.value in [
            "Decision Tables",
            "Both Customer Tables and Decision Tables",
        ]:
            if self.decision_inputs is None or self.decision_inputs.is_empty():
                exc = DataValidationError(
                    "decision_inputs must have at least one selection when target_mode includes 'Decision Tables'"
                )
                extension_manager.add_error(exc, field="decision_inputs")

    def _validate_decision_results(self):
        """Validate decision_results (conditional on target_mode)."""
        if self.target_mode and self.target_mode.value in [
            "Decision Tables",
            "Both Customer Tables and Decision Tables",
        ]:
            if self.decision_results is None or self.decision_results.is_empty():
                exc = DataValidationError(
                    "decision_results must have at least one selection when target_mode includes 'Decision Tables'"
                )
                extension_manager.add_error(exc, field="decision_results")

    def _validate_customer_record(self):
        """Validate customer_record (optional override)."""
        # customer_record is optional - no required validation
        pass

    def _validate_field_mappings_customer(self):
        """Validate field_mappings_customer JSON (conditional on target_mode)."""
        if self.target_mode and self.target_mode.value in [
            "Customer Tables",
            "Both Customer Tables and Decision Tables",
        ]:
            if self.field_mappings_customer is None:
                exc = DataValidationError(
                    "field_mappings_customer is required when target_mode includes 'Customer Tables'"
                )
                extension_manager.add_error(exc, field="field_mappings_customer")
                return

            if not self.field_mappings_customer.value or self.field_mappings_customer.value == "":
                exc = DataValidationError(
                    "field_mappings_customer must not be empty"
                )
                extension_manager.add_error(exc, field="field_mappings_customer")
                return

            # Validate JSON syntax
            try:
                self.field_mappings_customer.validate_json()
            except ValueError as e:
                exc = DataValidationError(
                    f"field_mappings_customer is not valid JSON: {str(e)}"
                )
                extension_manager.add_error(exc, field="field_mappings_customer")

    def _validate_account_association_config(self):
        """Validate account_association_config JSON (conditional on target_mode)."""
        if self.target_mode and self.target_mode.value in [
            "Customer Tables",
            "Both Customer Tables and Decision Tables",
        ]:
            # Only required if customer_record is not specified
            if self.customer_record is None or self.customer_record.is_empty():
                if self.account_association_config is None:
                    exc = DataValidationError(
                        "account_association_config is required when target_mode includes 'Customer Tables' and customer_record is not specified"
                    )
                    extension_manager.add_error(exc, field="account_association_config")
                    return

                if not self.account_association_config.value or self.account_association_config.value == "":
                    exc = DataValidationError(
                        "account_association_config must not be empty"
                    )
                    extension_manager.add_error(exc, field="account_association_config")
                    return

                # Validate JSON syntax
                try:
                    self.account_association_config.validate_json()
                except ValueError as e:
                    exc = DataValidationError(
                        f"account_association_config is not valid JSON: {str(e)}"
                    )
                    extension_manager.add_error(exc, field="account_association_config")

    def _validate_decision_mapping_config(self):
        """Validate decision_mapping_config JSON (conditional on target_mode)."""
        if self.target_mode and self.target_mode.value in [
            "Decision Tables",
            "Both Customer Tables and Decision Tables",
        ]:
            if self.decision_mapping_config is None:
                exc = DataValidationError(
                    "decision_mapping_config is required when target_mode includes 'Decision Tables'"
                )
                extension_manager.add_error(exc, field="decision_mapping_config")
                return

            if not self.decision_mapping_config.value or self.decision_mapping_config.value == "":
                exc = DataValidationError(
                    "decision_mapping_config must not be empty"
                )
                extension_manager.add_error(exc, field="decision_mapping_config")
                return

            # Validate JSON syntax
            try:
                self.decision_mapping_config.validate_json()
            except ValueError as e:
                exc = DataValidationError(
                    f"decision_mapping_config is not valid JSON: {str(e)}"
                )
                extension_manager.add_error(exc, field="decision_mapping_config")

    def _validate_http_timeout_seconds(self):
        """Validate http_timeout_seconds field."""
        if self.http_timeout_seconds is not None:
            try:
                self.http_timeout_seconds.validate()
            except ValueError as e:
                exc = DataValidationError(str(e))
                extension_manager.add_error(
                    exc, field="http_timeout_seconds", value=self.http_timeout_seconds.value
                )

    def _validate_output_verbosity(self):
        """Validate output_verbosity field."""
        if self.output_verbosity is None:
            exc = DataValidationError("output_verbosity is required")
            extension_manager.add_error(exc, field="output_verbosity")
            return

        valid_verbosities = ["Summary Only", "Summary and Errors", "Full Details"]
        if self.output_verbosity.value not in valid_verbosities:
            exc = DataValidationError(
                f"output_verbosity must be one of {valid_verbosities}, got {self.output_verbosity.value}"
            )
            extension_manager.add_error(
                exc, field="output_verbosity", value=self.output_verbosity.value
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert InputFields to dictionary.

        Excludes internal fields and empty previous_output.

        Returns:
            Dictionary representation of fields
        """
        result = {}
        for field in dataclass_fields(self):
            if field.name.startswith("_"):
                continue

            value = getattr(self, field.name)

            if value is None:
                continue

            if field.name == "previous_output" and value is not None:
                # Convert OutputFields to dict if present
                result[field.name] = value.to_dict()
            else:
                # Convert typed fields to their values
                if hasattr(value, "value"):
                    result[field.name] = value.value
                elif hasattr(value, "values"):
                    result[field.name] = value.values
                else:
                    result[field.name] = value

        return result
