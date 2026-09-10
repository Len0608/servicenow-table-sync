"""Field Mapper - applies source-to-destination field transformations."""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from exceptions import MappingException

logger = logging.getLogger("UNV")


class FieldMapper:
    """Applies field transformations and mappings from source to destination data."""

    def __init__(self, mapping_config: Dict[str, Any]) -> None:
        """
        Initialize field mapper.

        Args:
            mapping_config: Field mapping configuration from field_mappings_customer
        """
        self._config = mapping_config
        logger.debug("Initialized FieldMapper with config: %s", mapping_config)

    def apply_mapping(
        self, source_data: Dict[str, Any], source_object_id: str
    ) -> Dict[str, Any]:
        """
        Apply field mappings to source data.

        Args:
            source_data: Source object data
            source_object_id: Stable ID of source object for error reporting

        Returns:
            Mapped destination fields

        Raises:
            MappingException: If mapping fails
        """
        mapped = {}

        try:
            mappings = self._config.get("mappings", [])

            for mapping in mappings:
                dest_field = mapping.get("destination_field")
                transform_type = mapping.get("transformation_type", "field_copy")

                try:
                    if transform_type == "field_copy":
                        value = self._transform_field_copy(
                            mapping, source_data, source_object_id
                        )
                    elif transform_type == "count":
                        value = self._transform_count(
                            mapping, source_data, source_object_id
                        )
                    elif transform_type == "timestamp":
                        value = self._transform_timestamp(
                            mapping, source_data, source_object_id
                        )
                    else:
                        raise MappingException(
                            f"Unknown transformation type: {transform_type}"
                        )

                    if value is not None:
                        mapped[dest_field] = value
                        logger.debug(
                            "Mapped %s to %s = %s",
                            mapping.get("source_field"),
                            dest_field,
                            value,
                        )

                except MappingException:
                    raise
                except Exception as e:
                    raise MappingException(
                        f"Transformation failed for {dest_field}: {str(e)}"
                    )

            logger.debug("Successfully mapped %d fields for %s", len(mapped), source_object_id)
            return mapped

        except MappingException:
            raise
        except Exception as e:
            logger.error("Mapping failed for %s: %s", source_object_id, str(e))
            raise MappingException(f"Field mapping failed: {str(e)}")

    def _transform_field_copy(
        self, mapping: Dict[str, Any], source_data: Dict[str, Any], source_id: str
    ) -> Optional[Any]:
        """
        Copy source field to destination (direct copy).

        Args:
            mapping: Mapping configuration
            source_data: Source object data
            source_id: Source object ID for error reporting

        Returns:
            Field value or None if not found

        Raises:
            MappingException: If source field missing and required
        """
        source_field = mapping.get("source_field")

        if source_field not in source_data:
            if mapping.get("required", False):
                raise MappingException(f"Required field missing: {source_field}")
            return None

        value = source_data[source_field]
        logger.debug("Field copy: %s -> %s", source_field, value)
        return value

    def _transform_count(
        self, mapping: Dict[str, Any], source_data: Dict[str, Any], source_id: str
    ) -> Optional[int]:
        """
        Count aggregation (e.g., count related records).

        Args:
            mapping: Mapping configuration
            source_data: Source object data
            source_id: Source object ID for error reporting

        Returns:
            Count value or None

        Raises:
            MappingException: If aggregation fails
        """
        source_field = mapping.get("source_field")
        strategy = mapping.get("aggregation_strategy", "count")

        if source_field not in source_data:
            if mapping.get("required", False):
                raise MappingException(f"Required field missing: {source_field}")
            return None

        value = source_data[source_field]

        if isinstance(value, list):
            if strategy == "count":
                result = len(value)
            elif strategy == "sum":
                result = sum(
                    int(v) if isinstance(v, (int, str)) else 0 for v in value
                )
            elif strategy == "first_match":
                result = 1 if value else 0
            else:
                raise MappingException(f"Unknown aggregation strategy: {strategy}")
        elif isinstance(value, (int, float)):
            result = int(value)
        else:
            raise MappingException(
                f"Cannot aggregate non-numeric value: {type(value).__name__}"
            )

        logger.debug("Count aggregation: %s -> %d (strategy=%s)", source_field, result, strategy)
        return result

    def _transform_timestamp(
        self, mapping: Dict[str, Any], source_data: Dict[str, Any], source_id: str
    ) -> Optional[str]:
        """
        Timestamp conversion to RFC3339 format.

        Args:
            mapping: Mapping configuration
            source_data: Source object data
            source_id: Source object ID for error reporting

        Returns:
            RFC3339 formatted timestamp or None

        Raises:
            MappingException: If conversion fails
        """
        source_field = mapping.get("source_field")

        if source_field not in source_data:
            if mapping.get("required", False):
                raise MappingException(f"Required field missing: {source_field}")
            return None

        value = source_data[source_field]

        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                raise MappingException(
                    f"Invalid timestamp format for {source_field}: {value}"
                )
        elif isinstance(value, datetime):
            dt = value
        else:
            raise MappingException(
                f"Cannot convert {type(value).__name__} to timestamp"
            )

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        result = dt.isoformat().replace("+00:00", "Z")
        logger.debug("Timestamp conversion: %s -> %s", source_field, result)
        return result

    def validate_type_compatibility(
        self, source_type: str, destination_type: str, source_id: str
    ) -> bool:
        """
        Check if source and destination field types are compatible.

        Args:
            source_type: Source field type
            destination_type: Destination field type
            source_id: Object ID for error reporting

        Returns:
            True if compatible, False otherwise
        """
        compatible_pairs = {
            ("string", "string"): True,
            ("integer", "integer"): True,
            ("number", "number"): True,
            ("boolean", "boolean"): True,
            ("datetime", "datetime"): True,
            ("integer", "string"): True,
            ("number", "string"): True,
            ("boolean", "string"): True,
            ("datetime", "string"): True,
        }

        is_compatible = compatible_pairs.get((source_type, destination_type), False)
        logger.debug(
            "Type compatibility check: %s -> %s = %s",
            source_type,
            destination_type,
            is_compatible,
        )
        return is_compatible
