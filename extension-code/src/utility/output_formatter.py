"""Output Formatter - formats validation/preview/sync reports for STDOUT and JSON."""

import logging
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        """StrEnum for Python < 3.11."""

        pass


logger = logging.getLogger("UNV")


class OutputVerbosity(StrEnum):
    """Output verbosity levels."""

    SUMMARY_ONLY = "Summary Only"
    SUMMARY_AND_ERRORS = "Summary and Errors"
    FULL_DETAILS = "Full Details"


class OutputFormatter:
    """Formats validation results, preview plans, and synchronization reports."""

    _MAX_OUTPUT_RECORDS = int(os.environ.get("UE_MAX_OUTPUT_RECORDS", 100))

    def __init__(self, verbosity: str = OutputVerbosity.SUMMARY_AND_ERRORS) -> None:
        """
        Initialize output formatter.

        Args:
            verbosity: Output verbosity level
        """
        self._verbosity = verbosity
        logger.debug("Initialized OutputFormatter with verbosity: %s", verbosity)

    def format_validation_result(
        self, validation_checks: List[Dict[str, Any]]
    ) -> str:
        """
        Format validation check results as ASCII table.

        Args:
            validation_checks: List of validation check results

        Returns:
            Formatted ASCII table string
        """
        try:
            from tabulate import tabulate

            headers = ["Check", "Result", "Details"]
            rows = []

            for check in validation_checks:
                rows.append(
                    [
                        check.get("check", ""),
                        check.get("result", ""),
                        check.get("details", ""),
                    ]
                )

            table = tabulate(rows, headers=headers, tablefmt="rounded_outline")
            logger.debug("Formatted validation result table")
            return table

        except Exception as e:
            logger.error("Failed to format validation results: %s", str(e))
            return json.dumps(validation_checks, indent=2)

    def format_validation_report(
        self, checks: List[Dict[str, Any]], status: str, timestamp_start: str, timestamp_end: str
    ) -> str:
        """
        Format full validation report for STDOUT.

        Args:
            checks: Validation check results
            status: Overall status
            timestamp_start: Start timestamp
            timestamp_end: End timestamp

        Returns:
            Formatted report string
        """
        report = f"""VALIDATION REPORT
═════════════════════════════════════════
Start:     {timestamp_start}
End:       {timestamp_end}
Status:    {status}

Checks Performed
─────────────────────────────────────────
"""
        for check in checks:
            result = "✓" if check.get("result") == "passed" else "✗"
            report += f"{result} {check.get('check')}\n"

        report += f"\nResult: Ready to proceed." if status == "SUCCESS" else f"\nResult: Validation failed."
        return report

    def format_preview_summary(
        self,
        read_counts: Dict[str, int],
        proposed_changes: Dict[str, int],
        error_count: int,
    ) -> str:
        """
        Format preview summary for STDOUT.

        Args:
            read_counts: Source read counts
            proposed_changes: Proposed change counts
            error_count: Number of errors

        Returns:
            Formatted summary string
        """
        summary = f"""PREVIEW REPORT
═════════════════════════════════════════

Source Statistics
─────────────────────────────────────────
Retrieved:        {read_counts.get("retrieved", 0)}
In scope:         {read_counts.get("in_scope", 0)}
With mapping:     {read_counts.get("with_mapping", 0)}
Mapping errors:   {read_counts.get("mapping_errors", 0)}

Proposed Changes
─────────────────────────────────────────
Customer Table Creates:     {proposed_changes.get("customer_creates", 0)}
Customer Table Updates:     {proposed_changes.get("customer_updates", 0)}
Decision Table Updates:     {proposed_changes.get("decision_updates", 0)}
Errors:                     {error_count}

No writes performed (Preview mode).
"""
        return summary

    def format_sync_summary(
        self,
        read_counts: Dict[str, int],
        write_results: Dict[str, int],
        error_summary: Dict[str, Any],
    ) -> str:
        """
        Format synchronization summary for STDOUT.

        Args:
            read_counts: Source read counts
            write_results: Write operation counts
            error_summary: Error summary and categories

        Returns:
            Formatted summary string
        """
        summary = f"""SYNCHRONIZATION REPORT
═════════════════════════════════════════

Source Statistics
─────────────────────────────────────────
Retrieved:        {read_counts.get("retrieved", 0)}
Processed:        {read_counts.get("processed", 0)}
Skipped:          {read_counts.get("skipped", 0)}

Write Results
─────────────────────────────────────────
Customer Table:
  Created:        {write_results.get("customer_created", 0)}
  Updated:        {write_results.get("customer_updated", 0)}
  Failed:         {write_results.get("customer_failed", 0)}

Decision Table Rows:
  Created:        {write_results.get("decision_created", 0)}
  Updated:        {write_results.get("decision_updated", 0)}
  Failed:         {write_results.get("decision_failed", 0)}

Total Errors:     {error_summary.get("total_errors", 0)}
"""
        return summary

    def filter_errors_by_verbosity(
        self, errors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter errors based on verbosity setting.

        Args:
            errors: All errors

        Returns:
            Filtered errors list
        """
        if self._verbosity == OutputVerbosity.SUMMARY_ONLY:
            return []

        if self._verbosity == OutputVerbosity.SUMMARY_AND_ERRORS:
            limited = errors[: self._MAX_OUTPUT_RECORDS]
            if len(errors) > self._MAX_OUTPUT_RECORDS:
                logger.warning(
                    "Error list truncated: showing %d of %d errors",
                    self._MAX_OUTPUT_RECORDS,
                    len(errors),
                )
            return limited

        return errors[: self._MAX_OUTPUT_RECORDS]

    def build_extension_output(
        self,
        status: str,
        action: str,
        data: Dict[str, Any],
        timestamp_start: str,
        timestamp_end: str,
    ) -> Dict[str, Any]:
        """
        Build Extension Output JSON result object.

        Args:
            status: Overall status (success/failure/partial)
            action: Action name
            data: Action-specific data
            timestamp_start: Start timestamp
            timestamp_end: End timestamp

        Returns:
            Extension output dict
        """
        output = {
            "result": {
                "status": status,
                "action": action,
                "timestamp_start": timestamp_start,
                "timestamp_end": timestamp_end,
            }
        }

        output["result"].update(data)

        logger.debug("Built Extension Output: %s", json.dumps(output, indent=2))
        return output

    def sanitize_for_output(self, data: Any) -> Any:
        """
        Sanitize sensitive data for output (remove passwords, tokens, etc.).

        Args:
            data: Data to sanitize

        Returns:
            Sanitized data
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(
                    sensitive in key.lower()
                    for sensitive in ["password", "token", "credential", "secret", "key"]
                ):
                    sanitized[key] = "***"
                else:
                    sanitized[key] = self.sanitize_for_output(value)
            return sanitized

        if isinstance(data, list):
            return [self.sanitize_for_output(item) for item in data]

        return data

    def format_timestamp(self, dt: Optional[datetime] = None) -> str:
        """
        Format datetime as RFC3339 string.

        Args:
            dt: Datetime object (defaults to now)

        Returns:
            RFC3339 formatted timestamp
        """
        if dt is None:
            dt = datetime.utcnow()

        return dt.isoformat() + "Z"
