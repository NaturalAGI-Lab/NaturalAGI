import logging
import json
from typing import Any, Dict, Union, TypeVar, cast

from .property_matcher import PropertyMatcher

# Type for numeric values
NumericType = TypeVar("NumericType", int, float, complex)

# Type for range representation
RangeDict = Dict[str, Union[float, str]]


class RangePropertyMatcher(PropertyMatcher):
    """
    Matcher for numeric properties using range-based representation.

    This matcher supports:
    - Simple numeric values with tolerance
    - Range dictionary comparisons from the concept creator
    - Flexible matching based on value magnitude
    - String-serialized range dictionaries from Neo4j
    """

    def __init__(self, numeric_tolerance: float = 0.2):
        """
        Initialize the RangePropertyMatcher.

        Args:
            numeric_tolerance: The tolerance to use for numeric comparisons (default: 0.2 or 20%)
        """
        self.logger = logging.getLogger(__name__)
        self.ABSOLUTE_TOLERANCE = numeric_tolerance
        self.RELATIVE_TOLERANCE = numeric_tolerance

    def can_handle(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if this matcher can handle the given property values.

        Can handle:
        - Numeric values (int, float)
        - Range dictionaries
        - String-serialized range dictionaries

        Args:
            concept_value: Value from the concept
            instance_value: Value from the instance being classified

        Returns:
            True if values are numeric or range dictionaries, False otherwise
        """

        self.logger.debug(
            f"Testing if can handle - Concept: {concept_value}, Instance: {instance_value}"
        )

        # Both values are numeric
        if self._is_numeric(concept_value) and self._is_numeric(instance_value):
            self.logger.debug("Both values are numeric - can handle")
            return True

        # One value is a range dictionary
        if self._is_range(concept_value) or self._is_range(instance_value):
            # If one is range and the other is numeric, can handle
            if self._is_range(concept_value) and self._is_numeric(instance_value):
                self.logger.debug("Concept is range, instance is numeric - can handle")
                return True
            if self._is_numeric(concept_value) and self._is_range(instance_value):
                self.logger.debug("Concept is numeric, instance is range - can handle")
                return True

            # If both are ranges, can handle
            if self._is_range(concept_value) and self._is_range(instance_value):
                self.logger.debug("Both values are ranges - can handle")
                return True

        self.logger.debug("Cannot handle these values")
        return False

    def is_match(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if an instance value matches a concept value.

        Args:
            concept_value: Value from the concept (numeric or range)
            instance_value: Value from the instance being classified (numeric or range)

        Returns:
            True if values match within tolerance, False otherwise
        """

        self.logger.debug(
            f"Checking if matches - Concept: {concept_value}, Instance: {instance_value}"
        )

        # If both values are dictionaries representing ranges
        if (
            isinstance(concept_value, dict)
            and self._is_range(concept_value)
            and isinstance(instance_value, dict)
            and self._is_range(instance_value)
        ):
            self.logger.debug(f"Value {concept_value} identified as range dictionary")
            self.logger.debug(f"Value {instance_value} identified as range dictionary")
            self.logger.debug(
                f"Ranges {concept_value} and {instance_value} overlap? {self._ranges_overlap(concept_value, instance_value)}"
            )
            return self._ranges_overlap(concept_value, instance_value)

        # If concept is a range and instance is a number
        if (
            isinstance(concept_value, dict)
            and self._is_range(concept_value)
            and isinstance(instance_value, (int, float))
        ):
            self.logger.debug(f"Value {concept_value} identified as range dictionary")
            self.logger.debug(
                f"Range {concept_value} contains number {instance_value}? {self._range_contains_number(concept_value, instance_value)}"
            )
            return self._range_contains_number(concept_value, instance_value)

        # If both are numeric values
        if isinstance(concept_value, (int, float)) and isinstance(
            instance_value, (int, float)
        ):
            # For small values, use absolute tolerance
            if abs(concept_value) < 1.0 or abs(instance_value) < 1.0:
                result = round(abs(concept_value - instance_value), 1) <= self.ABSOLUTE_TOLERANCE
                self.logger.debug(
                    f"Absolute tolerance match: {concept_value} vs {instance_value}, result: {result}"
                )
                return result

            # For larger values, use relative tolerance
            max_val = max(abs(concept_value), abs(instance_value))
            diff = abs(concept_value - instance_value) / max_val
            result = diff <= self.RELATIVE_TOLERANCE
            self.logger.debug(
                f"Numeric tolerance match: {concept_value} vs {instance_value}, diff: {diff}, result: {result}"
            )
            return result

        self.logger.debug(
            f"No matching rules applied for {concept_value} and {instance_value}"
        )
        return False

    def _is_numeric(self, value: Any) -> bool:
        """Check if a value is numeric (int, float, complex)."""
        return isinstance(value, (int, float, complex))

    def _is_range(self, value: Any) -> bool:
        """
        Check if a value is a range dictionary.

        Args:
            value: The value to check

        Returns:
            True if the value is a range dictionary, False otherwise
        """
        # Handle dictionary case
        if isinstance(value, dict):
            if "min" in value and "max" in value and value.get("type") == "range":
                self.logger.debug(f"Value {value} identified as range dictionary")
                return True

        return False

    def _ranges_overlap(self, range1: dict, range2: dict) -> bool:
        """Check if two range dictionaries overlap."""
        return not (range1["max"] < range2["min"] or range2["max"] < range1["min"])

    def _range_contains_number(self, range_dict: dict, number: (int, float)) -> bool:
        """Check if a range dictionary contains a given number."""
        return range_dict["min"] <= number <= range_dict["max"]
