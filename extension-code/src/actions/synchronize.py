"""Synchronize action - execute writes to ServiceNow with retry logic."""

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
    ConcurrentEditException,
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


class Synchronize:
    """Executes writes to ServiceNow with retry logic and conflict detection."""

    _MAX_RETRIES = 3

    def __init__(self, input_data: InputFields) -> None:
        """Initialize synchronize action."""
        self._input = input_data
        self._output_fields = OutputFields()
        self._uac_conn = None
        self._sn_conn = None
        self._run_id = self._generate_run_id()
        self._errors: List[Dict[str, Any]] = []
        self._write_results = {
            "customer_table_created": 0,
            "customer_table_updated": 0,
            "customer_table_unchanged": 0,
            "customer_table_failed": 0,
            "decision_table_rows_created": 0,
            "decision_table_rows_updated": 0,
            "decision_table_rows_failed": 0,
        }

    def execute(self) -> ActionOutput:
        """Execute synchronization and return results."""
        logger.info("Starting Synchronize action with run_id=%s", self._run_id)

        timestamp_start = self._format_timestamp()
        self._output_fields.update(status="Revalidating configuration")

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

            self._output_fields.update(status="Collecting source data")
            source_data = self._collect_source_data()
            read_counts = self._build_read_counts(source_data)

            self._output_fields.update(status="Executing writes")
            self._execute_writes(source_data)

            timestamp_end = self._format_timestamp()
            self._output_fields.update(status="Complete")

            formatter = OutputFormatter(self._input.output_verbosity.value if self._input.output_verbosity else OutputVerbosity.SUMMARY_AND_ERRORS)
            filtered_errors = formatter.filter_errors_by_verbosity(self._errors)

            return ActionOutput(
                status="success" if not self._has_write_failures() else "partial_success",
                action="synchronize",
                run_id=self._run_id,
                source_dataset=self._input.source_dataset.value,
                target_mode=self._input.target_mode.value,
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                read_counts=read_counts,
                write_results=self._write_results,
                errors=filtered_errors if filtered_errors else None,
                details=self._build_details(read_counts),
            )

        except ExecutionError as e:
            logger.error("Synchronize failed: %s", str(e))
            timestamp_end = self._format_timestamp()
            self._output_fields.update(status="Failed")

            return ActionOutput(
                status="failed",
                action="synchronize",
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

    def _execute_writes(self, source_data: List[Dict[str, Any]]) -> None:
        """Execute write operations for all source objects."""
        logger.info("Executing write operations for %d source objects", len(source_data))

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

        for i, source_obj in enumerate(source_data):
            if extension_manager.is_cancelled():
                logger.warning("Synchronize cancelled by user")
                break

            try:
                progress = int((i + 1) / len(source_data) * 100)
                self._output_fields.update(status=f"Processing {i + 1}/{len(source_data)}")

                if target_mode in ["Customer Tables", "Both Customer Tables and Decision Tables"]:
                    self._write_customer_table_record(source_obj, mapper, account_handler)

                if target_mode in ["Decision Tables", "Both Customer Tables and Decision Tables"]:
                    self._write_decision_table_row(source_obj, mapper or {}, decision_handler)

            except Exception as e:
                logger.error("Failed to write source object: %s", str(e))
                self._errors.append({
                    "source_id": str(source_obj.get("id", "unknown")),
                    "source_name": str(source_obj.get("name", "unknown")),
                    "error_category": "write_error",
                    "error_message": str(e),
                    "recovery_action": "Review and retry synchronization",
                })

    def _write_customer_table_record(
        self,
        source_obj: Dict[str, Any],
        mapper: FieldMapper,
        account_handler: AccountResolutionHandler,
    ) -> None:
        """Write a customer table record."""
        try:
            mapped_data = mapper.apply_mapping(source_obj, str(source_obj.get("id", "unknown")))

            bs_id = source_obj.get("business_service_id", "default")
            account_sys_id = account_handler.resolve_account(
                bs_id, source_obj, self._input.customer_record.value if self._input.customer_record else None
            )

            table_name = self._input.customer_table.value

            for attempt in range(self._MAX_RETRIES):
                try:
                    response = self._sn_conn.patch(table_name, account_sys_id, mapped_data)
                    self._write_results["customer_table_updated"] += 1
                    logger.info("Updated customer table record: %s", account_sys_id)
                    return

                except ConcurrentEditException as e:
                    logger.warning("Concurrent edit detected, attempt %d of %d", attempt + 1, self._MAX_RETRIES)
                    if attempt == self._MAX_RETRIES - 1:
                        self._write_results["customer_table_failed"] += 1
                        raise
                    continue

                except (NetworkException, Exception) as e:
                    if attempt == self._MAX_RETRIES - 1:
                        self._write_results["customer_table_failed"] += 1
                        raise
                    logger.warning("Write failed, attempt %d of %d: %s", attempt + 1, self._MAX_RETRIES, str(e))
                    continue

        except MappingException as e:
            logger.warning("Mapping failed for source object: %s", str(e))
            self._write_results["customer_table_failed"] += 1
            raise

    def _write_decision_table_row(
        self,
        source_obj: Dict[str, Any],
        mapped_data: Dict[str, Any],
        decision_handler: DecisionTableOperationsHandler,
    ) -> None:
        """Write a decision table row."""
        try:
            bs_id = source_obj.get("business_service_id", "default")
            source_id = str(source_obj.get("id", "unknown"))

            composite_key = decision_handler.create_composite_key(bs_id, source_id)

            existing_row = decision_handler.find_existing_row(composite_key)

            row_data = decision_handler.build_decision_row(mapped_data, source_obj, composite_key)

            if existing_row:
                decision_handler.update_row(existing_row.get("sys_id"), row_data)
                self._write_results["decision_table_rows_updated"] += 1
                logger.info("Updated decision table row: %s", composite_key)
            else:
                decision_handler.create_row(row_data)
                self._write_results["decision_table_rows_created"] += 1
                logger.info("Created decision table row: %s", composite_key)

        except Exception as e:
            logger.warning("Decision table write failed for source object: %s", str(e))
            self._write_results["decision_table_rows_failed"] += 1
            raise

    def _build_read_counts(self, source_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Build read count statistics."""
        return {
            "source_objects_retrieved": len(source_data),
            "source_objects_processed": len(source_data) - len(self._errors),
            "source_objects_skipped": len(self._errors),
        }

    def _build_details(self, read_counts: Dict[str, int]) -> str:
        """Build details summary."""
        total_written = (
            self._write_results.get("customer_table_created", 0) +
            self._write_results.get("customer_table_updated", 0) +
            self._write_results.get("decision_table_rows_created", 0) +
            self._write_results.get("decision_table_rows_updated", 0)
        )

        total_failed = (
            self._write_results.get("customer_table_failed", 0) +
            self._write_results.get("decision_table_rows_failed", 0)
        )

        return f"Retrieved {read_counts.get('source_objects_retrieved', 0)} objects, " \
               f"wrote {total_written} records, {total_failed} failed"

    def _has_write_failures(self) -> bool:
        """Check if any writes failed."""
        return (
            self._write_results.get("customer_table_failed", 0) > 0 or
            self._write_results.get("decision_table_rows_failed", 0) > 0
        )

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
