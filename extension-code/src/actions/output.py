"""ActionOutput dataclass for ServiceNow Table Sync extension."""

from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
import json


@dataclass
class ActionOutput:
    """Output payload for extension actions."""

    status: Optional[str] = None
    details: Optional[str] = None
    error_summary: Optional[str] = None
    validation_checks: Optional[List[Dict[str, Any]]] = None
    read_counts: Optional[Dict[str, int]] = None
    proposed_changes: Optional[Dict[str, int]] = None
    write_results: Optional[Dict[str, int]] = None
    errors: Optional[List[Dict[str, Any]]] = None
    sample_proposed_record: Optional[Dict[str, Any]] = None
    run_id: Optional[str] = None
    source_dataset: Optional[str] = None
    target_mode: Optional[str] = None
    timestamp_start: Optional[str] = None
    timestamp_end: Optional[str] = None
    action: Optional[str] = None

    def print_output(self) -> None:
        """Print action output to STDOUT."""
        if self.status:
            print(f"Status: {self.status}")
        if self.details:
            print(f"Details: {self.details}")
        if self.error_summary:
            print(f"Errors: {self.error_summary}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Extension Output."""
        output = {}

        if self.status:
            output["status"] = self.status
        if self.action:
            output["action"] = self.action
        if self.run_id:
            output["run_id"] = self.run_id
        if self.source_dataset:
            output["source_dataset"] = self.source_dataset
        if self.target_mode:
            output["target_mode"] = self.target_mode
        if self.timestamp_start:
            output["timestamp_start"] = self.timestamp_start
        if self.timestamp_end:
            output["timestamp_end"] = self.timestamp_end
        if self.validation_checks:
            output["validation_checks"] = self.validation_checks
        if self.read_counts:
            output["read_counts"] = self.read_counts
        if self.proposed_changes:
            output["proposed_changes"] = self.proposed_changes
        if self.write_results:
            output["write_results"] = self.write_results
        if self.sample_proposed_record:
            output["sample_proposed_record"] = self.sample_proposed_record
        if self.errors:
            output["errors"] = self.errors

        return output
