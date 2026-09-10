"""Preview action - collect data and generate plan of proposed changes."""

import logging
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fields.input import InputFields
from fields.output import OutputFields
from actions.output import ActionOutput
from manager import ExtensionManager
from exceptions import (
    ExecutionError,
    AuthenticationException,
    NetworkException,
    MappingException,
)
from utility import (
    UACConnectionHandler,
    ServiceNowConnectionHandler,
    FieldMapper,
    AccountResolutionHandler,
    DecisionTableOperationsHandler,
    OutputFormatter,
    OutputVerbosity,
)

logger = logging.getLogger("UNV")
extension_manager = ExtensionManager()


class Preview:
    """Collects source and target data, applies mappings, generates proposed change plan."""

    def __init__(self, input_data: InputFields) -> None:
        """Initialize preview action."""
        self._input = input_data
        self._output_fields = OutputFields()
        self._uac_conn = None
        self._sn_conn = None
        self._run_id = self._generate_run_id()
        self._errors: List[Dict[str, Any]] = []

    def execute(self) -> ActionOutput:
        """Execute preview and return proposed changes."""
        logger.info("Starting Preview action with run_id=%s", self._run_id)

        timestamp_start = self._format_timestamp()
        self._output_fields.update(status="Collecting data")

        try:
            self._uac_conn = UACConnectionHandler(
                self._input.uac_credential.url,
                self._input.uac_credential.username,
                self._input.uac_credential.password,
            )
            self._sn_conn = ServiceNowConnectionHandler(
                self._input.servicenow_credential.url,
                self._input.servicenow_credential.username,
                self._input.servicenow_credential.password,
            )

            source_data = self._collect_source_data()
            read_counts = self._build_read_counts(source_data)

            self._output_fields.update(status="Applying mappings")
            proposed_changes, samples = self._plan_proposed_changes(source_data)

            timestamp_end = self._format_timestamp()
            self._output_fields.update(status="Complete")

            formatter = OutputFormatter(self._input.output_verbosity.value if self._input.output_verbosity else OutputVerbosity.SUMMARY_AND_ERRORS)
            filtered_errors = formatter.filter_errors_by_verbosity(self._errors)

            return ActionOutput(
                status="success",
                action="preview",
                run_id=self._run_id,
                source_dataset=self._input.source_dataset.value,
                target_mode=self._input.target_mode.value,
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                read_counts=read_counts,
                proposed_changes=proposed_changes,
                errors=filtered_errors if filtered_errors else None,
                sample_proposed_record=samples[0] if samples else None,
                details=self._build_details(read_counts, proposed_changes),
            )

        except ExecutionError as e:
            logger.error("Preview failed: %s", str(e))
            timestamp_end = self._format_timestamp()
            self._output_fields.update(status="Failed")

            return ActionOutput(
                status="failed",
                action="preview",
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                error_summary=str(e),
            )

        finally:
            if self._uac_conn:
                self._uac_conn.close()
            if self._sn_conn:
                self._sn_conn.close()

    def _collect_source_data(self) -> List[Dict[str, Any]]:
        """Collect all source objects from UAC."""
        logger.info("Collecting source data from UAC")

        dataset = self._input.source_dataset.value
        endpoint = self._get_dataset_endpoint(dataset)

        try:
            all_items = self._uac_conn.fetch_paginated(endpoint)
            logger.info("Retrieved %d %s from UAC", len(all_items), dataset.lower())

            return all_items

        except Exception as e:
            logger.error("Failed to collect source data: %s", str(e))
            raise ExecutionError(f"Failed to collect source data: {str(e)}")

    def _plan_proposed_changes(self, source_data: List[Dict[str, Any]]) -> tuple:
        """Apply mappings and plan proposed changes."""
        logger.info("Planning proposed changes for %d source objects", len(source_data))

        proposed_changes = {
            "customer_table_creates": 0,
            "customer_table_updates": 0,
            "customer_table_unchanged": 0,
            "decision_table_row_creates": 0,
            "decision_table_row_updates": 0,
            "decision_table_row_unchanged": 0,
        }

        samples: List[Dict[str, Any]] = []
        target_mode = self._input.target_mode.value

        mapping_config = None
        mapper = None
        if target_mode in ["Customer Tables", "Both Customer Tables and Decision Tables"]:
            mapping_config = json.loads(self._input.field_mappings_customer.value)
            mapper = FieldMapper(mapping_config)

        account_config = None
        account_handler = None
        if target_mode in ["Customer Tables", "Both Customer Tables and Decision Tables"]:
            account_config = json.loads(self._input.account_association_config.value)
            account_handler = AccountResolutionHandler(self._sn_conn, account_config)

        decision_config = None
        decision_handler = None
        if target_mode in ["Decision Tables", "Both Customer Tables and Decision Tables"]:
            decision_config = json.loads(self._input.decision_mapping_config.value)
            decision_handler = DecisionTableOperationsHandler(self._sn_conn, decision_config)

        for source_obj in source_data:
            if extension_manager.is_cancelled():
                break

            try:
                source_id = source_obj.get("id") or source_obj.get("name", "unknown")

                if target_mode in ["Customer Tables", "Both Customer Tables and Decision Tables"]:
                    self._plan_customer_table_changes(
                        source_obj, mapper, account_handler, proposed_changes, samples
                    )

                if target_mode in ["Decision Tables", "Both Customer Tables and Decision Tables"]:
                    self._plan_decision_table_changes(
                        source_obj, mapper or {}, decision_handler, proposed_changes
                    )

            except Exception as e:
                logger.warning("Failed to plan changes for source object: %s", str(e))
                self._errors.append({
                    "source_id": str(source_obj.get("id", "unknown")),
                    "source_name": str(source_obj.get("name", "unknown")),
                    "error_category": "mapping_error",
                    "error_message": str(e),
                })

        return proposed_changes, samples

    def _plan_customer_table_changes(
        self,
        source_obj: Dict[str, Any],
        mapper: FieldMapper,
        account_handler: AccountResolutionHandler,
        proposed_changes: Dict[str, int],
        samples: List[Dict[str, Any]],
    ) -> None:
        """Plan customer table changes for a single source object."""
        try:
            mapped_data = mapper.apply_mapping(source_obj, str(source_obj.get("id", "unknown")))

            bs_id = source_obj.get("business_service_id", "default")
            account_sys_id = account_handler.resolve_account(
                bs_id, source_obj, self._input.customer_record.value if self._input.customer_record else None
            )

            proposed_changes["customer_table_updates"] += 1

            if len(samples) == 0:
                samples.append({
                    "table": self._input.customer_table.value,
                    "operation": "update",
                    "target_sys_id": account_sys_id,
                    "proposed_fields": mapped_data,
                })

        except MappingException as e:
            logger.warning("Mapping failed for source object: %s", str(e))
            raise

    def _plan_decision_table_changes(
        self,
        source_obj: Dict[str, Any],
        mapped_data: Dict[str, Any],
        decision_handler: DecisionTableOperationsHandler,
        proposed_changes: Dict[str, int],
    ) -> None:
        """Plan decision table changes for a single source object."""
        try:
            bs_id = source_obj.get("business_service_id", "default")
            source_id = str(source_obj.get("id", "unknown"))

            composite_key = decision_handler.create_composite_key(bs_id, source_id)

            existing_row = decision_handler.find_existing_row(composite_key)

            if existing_row:
                proposed_changes["decision_table_row_updates"] += 1
            else:
                proposed_changes["decision_table_row_creates"] += 1

        except Exception as e:
            logger.warning("Decision table planning failed for source object: %s", str(e))
            raise

    def _build_read_counts(self, source_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Build read count statistics."""
        return {
            "source_objects_retrieved": len(source_data),
            "source_objects_processed": len(source_data) - len(self._errors),
            "source_objects_with_errors": len(self._errors),
        }

    def _build_details(self, read_counts: Dict[str, int], proposed_changes: Dict[str, int]) -> str:
        """Build details summary."""
        total_changes = (
            proposed_changes.get("customer_table_creates", 0) +
            proposed_changes.get("customer_table_updates", 0) +
            proposed_changes.get("decision_table_row_creates", 0) +
            proposed_changes.get("decision_table_row_updates", 0)
        )

        return f"Retrieved {read_counts.get('source_objects_retrieved', 0)} objects, " \
               f"proposed {total_changes} changes, {len(self._errors)} errors"

    def _get_dataset_endpoint(self, dataset: str) -> str:
        """Get UAC endpoint for dataset type."""
        endpoints = {
            "Agents": "/resources/agent/list",
            "Calendars": "/resources/calendar/list",
            "Scripts": "/resources/script/list",
            "SAP/ABAP Jobs": "/resources/task/list",
        }
        return endpoints.get(dataset, "/resources/agent/list")

    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:6]
        return f"run_{timestamp}_{unique_id}"

    def _format_timestamp(self) -> str:
        """Format current time as RFC3339 string."""
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
