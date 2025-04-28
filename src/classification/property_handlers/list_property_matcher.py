import logging
from typing import Any, Dict, List, Optional, Union, Tuple, cast

from .property_matcher import PropertyMatcher
from .range_property_matcher import RangePropertyMatcher


class ListPropertyMatcher(PropertyMatcher):
    """
    Matcher for list properties that may contain numeric values or ranges.

    This matcher supports:
    - Lists of simple values
    - Lists containing range dictionaries
    - Element-wise matching using specialized matchers
    """

    def __init__(self, list_matching_mode: str = "subset"):
        """
        Initialize the ListPropertyMatcher.

        Args:
            list_matching_mode: The matching mode to use for lists:
                - "subset": The concept list must be a subset of the instance list
                - "element_wise": Elements must match position-by-position
                - "contains_all": The instance list must contain all elements from the concept list
        """
        self.logger = logging.getLogger(__name__)
        self.range_matcher = RangePropertyMatcher()
        self.list_matching_mode = list_matching_mode

    def can_handle(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if this matcher can handle the given property values.

        Can handle:
        - Two lists
        - Lists that may contain range dictionaries

        Args:
            concept_value: Value from the concept
            instance_value: Value from the instance being classified

        Returns:
            True if both values are lists, False otherwise
        """
        return isinstance(concept_value, list) and isinstance(instance_value, list)

    def is_match(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if an instance list matches a concept list.

        Matching depends on the list_matching_mode:
        - "subset": The concept list must be a subset of the instance list
        - "element_wise": Elements must match position-by-position
        - "contains_all": The instance list must contain all elements from the concept list

        Args:
            concept_value: List from the concept
            instance_value: List from the instance being classified

        Returns:
            True if lists match according to the mode, False otherwise
        """
        if not (isinstance(concept_value, list) and isinstance(instance_value, list)):
            return False

        # Empty lists match
        if not concept_value and not instance_value:
            return True

        # Element-wise matching mode
        if self.list_matching_mode == "element_wise":
            # Lists must have the same length
            if len(concept_value) != len(instance_value):
                return False

            # Check each element
            for concept_elem, instance_elem in zip(concept_value, instance_value):
                # Try range matcher first if applicable
                if self.range_matcher.can_handle(concept_elem, instance_elem):
                    if not self.range_matcher.is_match(concept_elem, instance_elem):
                        return False
                # Otherwise, require exact match
                elif concept_elem != instance_elem:
                    return False

            return True

        # Subset matching mode (default)
        elif self.list_matching_mode == "subset":
            # Each concept element must have a matching instance element
            for concept_elem in concept_value:
                matched = False

                for instance_elem in instance_value:
                    # Try range matcher first if applicable
                    if self.range_matcher.can_handle(concept_elem, instance_elem):
                        if self.range_matcher.is_match(concept_elem, instance_elem):
                            matched = True
                            break
                    # Otherwise, check for exact match
                    elif concept_elem == instance_elem:
                        matched = True
                        break

                if not matched:
                    return False

            return True

        # Contains all matching mode
        elif self.list_matching_mode == "contains_all":
            # Similar to subset, but with roles reversed
            for instance_elem in instance_value:
                matched = False

                for concept_elem in concept_value:
                    # Try range matcher first if applicable
                    if self.range_matcher.can_handle(concept_elem, instance_elem):
                        if self.range_matcher.is_match(concept_elem, instance_elem):
                            matched = True
                            break
                    # Otherwise, check for exact match
                    elif concept_elem == instance_elem:
                        matched = True
                        break

                if not matched:
                    return False

            return True

        # Unknown matching mode
        self.logger.warning(f"Unknown list matching mode: {self.list_matching_mode}")
        return False
