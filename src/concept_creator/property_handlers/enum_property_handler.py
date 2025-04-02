import logging
from typing import Any, Dict, List, Optional, Union, Tuple, Set, cast
from enum import Enum

from .property_handler import PropertyHandler


class EnumPropertyHandler(PropertyHandler):
    """
    Handler for properties that are based on Enum values.

    This handler specifically processes properties that store direction information
    (horizontal and vertical directions) from contour traversal.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def can_handle(self, value1: Any, value2: Any) -> bool:
        """
        Determine if this handler can process the given property values.

        Can handle:
        - String values representing enum names (e.g., "LEFT", "RIGHT", "TOP", "BOTTOM")
        - All values must be strings and represent a finite set of options

        Args:
            value1: First property value
            value2: Second property value

        Returns:
            True if both values are enum name strings, False otherwise
        """
        # Check if both are strings
        if not (isinstance(value1, str) and isinstance(value2, str)):
            return False

        # Check if they are direction-related enum values
        direction_values = {"LEFT", "RIGHT", "NONE", "TOP", "BOTTOM"}
        return value1 in direction_values or value2 in direction_values

    def merge_values(self, *values: Any) -> list[str]:
        """
        Merge multiple enum values into a set of possible values.

        For direction properties, we store all possible directions seen in the examples.
        This allows concepts to match any of the directions found in the samples.

        Args:
            *values: Variable number of enum name strings to merge

        Returns:
            A set of all unique enum name strings
        """
        # Filter out None values and non-strings
        filtered_values = [v for v in values if v is not None and isinstance(v, str)]

        if not filtered_values:
            return {"NONE"}

        # Create a set of all unique values
        result = list(filtered_values)

        self.logger.debug(f"Merged enum values: {filtered_values} → {result}")
        return result

    def is_match(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if an instance enum value matches a concept enum value set.

        Args:
            concept_value: The enum set from the concept
            instance_value: The enum value from the instance being classified

        Returns:
            True if the instance value is in the concept's set of values, False otherwise
        """
        # If concept value is a string, convert to set for consistent handling
        if isinstance(concept_value, str):
            concept_set = {concept_value}
        elif isinstance(concept_value, list):
            concept_set = set(concept_value)
        elif isinstance(concept_value, set):
            concept_set = concept_value
        else:
            return False

        if not isinstance(instance_value, str):
            return False

        # Return true if the instance value is in the concept's set
        return instance_value in concept_set
