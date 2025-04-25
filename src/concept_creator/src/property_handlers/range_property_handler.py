import logging
from typing import Any, Dict, List, Optional, Union, TypeVar, cast

from .property_handler import PropertyHandler

# Type for numeric values
NumericType = TypeVar("NumericType", int, float, complex)

# Type for range representation
RangeDict = Dict[str, Union[float, str]]


class RangePropertyHandler(PropertyHandler):
    """
    Handler for numeric properties using range-based representation.

    This handler converts numeric properties into a range format (min/max/center)
    for more robust concept representation and matching.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def can_handle(self, value1: Any, value2: Any) -> bool:
        """
        Determine if this handler can process the given property values.

        Can handle:
        - Two numeric values
        - One numeric value and one range dictionary
        - Two range dictionaries

        Args:
            value1: First property value
            value2: Second property value

        Returns:
            True if values are numeric or range dictionaries, False otherwise
        """
        result = self._is_numeric_comparable(value1, value2)
        if not result:
            self.logger.debug(
                f"RangePropertyHandler cannot handle: {value1} ({type(value1)}) and {value2} ({type(value2)})"
            )
            self.logger.debug(f"  Is value1 numeric: {self._is_numeric(value1)}")
            self.logger.debug(f"  Is value2 numeric: {self._is_numeric(value2)}")
            self.logger.debug(f"  Is value1 range: {self._is_range(value1)}")
            self.logger.debug(f"  Is value2 range: {self._is_range(value2)}")
        return result

    def merge_values(self, *values: Any) -> RangeDict:
        """
        Merge multiple numeric values into a range representation.

        Args:
            *values: Variable number of numeric values or range dictionaries

        Returns:
            A dictionary with min, max, center, and type keys
        """
        # Filter out None values
        filtered_values = [v for v in values if v is not None]

        # Convert all numeric or range values to range format
        ranges = []
        for value in filtered_values:
            if self._is_numeric(value):
                ranges.append(self._to_range(value))
            elif self._is_range(value):
                ranges.append(value)

        if not ranges:
            # Fallback if no usable values
            return cast(RangeDict, filtered_values[0] if filtered_values else None)

        # Calculate the overall min, max and center
        min_val = min(r["min"] for r in ranges)
        max_val = max(r["max"] for r in ranges)

        # Calculate center as the weighted average of all centers
        if all("center" in r for r in ranges):
            centers = []
            weights = []
            for r in ranges:
                range_size = max(r["max"] - r["min"], 0.0001)  # Avoid division by zero
                centers.append(r["center"])
                weights.append(range_size)
            total_weight = sum(weights)
            center = (
                sum(c * w for c, w in zip(centers, weights)) / total_weight
                if total_weight > 0
                else (min_val + max_val) / 2
            )
        else:
            center = (min_val + max_val) / 2

        result = {"min": min_val, "max": max_val, "type": "range", "center": center}
        self.logger.debug(
            f"Created range representation: {result} from values: {filtered_values}"
        )
        return result

    def is_match(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if an instance value falls within the concept's range.

        Args:
            concept_value: The property value from the concept (should be a range dict)
            instance_value: The property value from the instance being classified

        Returns:
            True if the instance value is within the concept's range, False otherwise
        """
        # Convert concept to range if it's not already
        if not self._is_range(concept_value):
            if self._is_numeric(concept_value):
                concept_range = self._to_range(concept_value)
            else:
                return False  # Can't match non-numeric, non-range concept values
        else:
            concept_range = concept_value

        # Convert instance to numeric if possible
        if not self._is_numeric(instance_value):
            if self._is_range(instance_value):
                # For range-to-range matching, check if ranges overlap
                instance_range = instance_value
                return (
                    instance_range["min"] <= concept_range["max"]
                    and instance_range["max"] >= concept_range["min"]
                )
            else:
                return False  # Can't match non-numeric instance values

        # Check if instance value falls within concept range
        return concept_range["min"] <= instance_value <= concept_range["max"]

    def _is_numeric(self, value: Any) -> bool:
        """Check if a value is numeric (int, float, complex) or a string that can be converted to a number."""
        # Direct numeric type check
        if isinstance(value, (int, float, complex)):
            return True

        # Check if it's a string that can be converted to a number
        if isinstance(value, str):
            try:
                float(value)
                return True
            except ValueError:
                return False

        self.logger.debug(f"Value {value} of type {type(value)} is not numeric")
        return False

    def _is_range(self, value: Any) -> bool:
        """Check if a value is a range dictionary."""
        return (
            isinstance(value, dict)
            and "min" in value
            and "max" in value
            and value.get("type") == "range"
        )

    def _to_range(self, value: NumericType) -> RangeDict:
        """Convert a numeric value to a range dictionary."""
        return {"min": value, "max": value, "type": "range", "center": value}

    def _is_numeric_comparable(self, val1: Any, val2: Any) -> bool:
        """Check if two values can be compared numerically."""
        # Both values are numeric
        if self._is_numeric(val1) and self._is_numeric(val2):
            return True

        # One value is numeric and one is a range
        if self._is_numeric(val1) and self._is_range(val2):
            return True

        if self._is_range(val1) and self._is_numeric(val2):
            return True

        # Both values are ranges
        if self._is_range(val1) and self._is_range(val2):
            return True

        return False
