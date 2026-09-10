"""OutputFields dataclass for UAC Universal Extension.

Handles output field tracking and UI synchronization.
"""

from dataclasses import dataclass, fields as dataclass_fields
from typing import Optional

from universal_extension import ui
from fields.types import Text


@dataclass
class OutputFields:
    """Output fields for ServiceNow Table Sync extension."""

    status: Optional[Text] = None
    details: Optional[Text] = None
    error_summary: Optional[Text] = None

    def update(self, **fields):
        """Update fields and sync with UAC UI in real-time.

        Args:
            **fields: Field names and values to update
        """
        for field_name, field_value in fields.items():
            if hasattr(self, field_name):
                if isinstance(field_value, str):
                    field_value = Text(field_value)
                setattr(self, field_name, field_value)

        ui.update_output_fields(fields)

    def to_dict(self) -> dict:
        """Convert OutputFields to dictionary.

        Uses dataclass_fields + getattr to access live instances.
        Returns field values as plain strings, not wrapped Text objects.

        Returns:
            Dictionary with field names and values
        """
        result = {}
        for field in dataclass_fields(self):
            value = getattr(self, field.name)
            if value is not None:
                result[field.name] = value.value if isinstance(value, Text) else value
        return result

    def clear(self):
        """Reset all fields to None."""
        self.status = None
        self.details = None
        self.error_summary = None
