import logging
from typing import Any, Dict, List, Optional, Union, Tuple, Set, cast

from .property_matcher import PropertyMatcher


class EnumPropertyMatcher(PropertyMatcher):
    """
    Matcher for enum-based properties like direction values.

    This matcher handles direction information (horizontal and vertical)
    from contour traversal during classification.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def can_handle(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if this matcher can handle the given property values.

        Can handle:
        - String direction values
        - Sets of direction values from the concept creator

        Args:
            concept_value: Value from the concept
            instance_value: Value from the instance being classified

        Returns:
            True if these values are direction-related, False otherwise
        """
        # Handle set from concept creation and string from instance
        if isinstance(concept_value, set) and isinstance(instance_value, str):
            # Check if they are direction-related enum values
            direction_values = {"LEFT", "RIGHT", "NONE", "TOP", "BOTTOM"}
            return (
                any(val in direction_values for val in concept_value)
                or instance_value in direction_values
            )

        # Handle two strings
        if isinstance(concept_value, str) and isinstance(instance_value, str):
            direction_values = {"LEFT", "RIGHT", "NONE", "TOP", "BOTTOM"}
            return (
                concept_value in direction_values or instance_value in direction_values
            )

        return False

    def is_match(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if an instance direction value matches a concept direction value.

        Args:
            concept_value: Direction value or set from the concept
            instance_value: Direction value from the instance being classified

        Returns:
            True if the instance value matches the concept value, False otherwise
        """
        # If concept has a set of possible directions
        if isinstance(concept_value, set):
            if not isinstance(instance_value, str):
                return False

            # Match if instance direction is in the concept's direction set
            return instance_value in concept_value

        # If concept has a single direction value
        if isinstance(concept_value, str) and isinstance(instance_value, str):
            # For simple case, exact match
            return concept_value == instance_value

        return False
