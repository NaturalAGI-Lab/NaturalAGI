import logging
from typing import Any, Dict, List, Optional, Union, Tuple, cast

from .property_handler import PropertyHandler
from .range_property_handler import RangePropertyHandler


class ListPropertyHandler(PropertyHandler):
    """
    Handler for list properties that may contain numeric values.

    This handler processes lists by applying element-wise operations,
    potentially using other handlers for the individual elements.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.range_handler = RangePropertyHandler()

    def can_handle(self, value1: Any, value2: Any) -> bool:
        """
        Determine if this handler can process the given property values.

        Can handle:
        - Two lists of the same length
        - Lists containing numeric values or ranges

        Args:
            value1: First property value
            value2: Second property value

        Returns:
            True if both values are compatible lists, False otherwise
        """
        # Check if both are lists of the same length
        if not (isinstance(value1, list) and isinstance(value2, list)):
            return False

        if len(value1) != len(value2):
            return False

        if not value1 or not value2:  # Empty lists
            return True

        # Check if all elements can be handled by the range handler
        return all(
            self.range_handler.can_handle(v1, v2) for v1, v2 in zip(value1, value2)
        )

    def merge_values(self, *lists: Any) -> List[Any]:
        """
        Merge multiple lists element-wise.

        Args:
            *lists: Variable number of lists to merge

        Returns:
            A new list with merged elements
        """
        # Filter out None values and non-lists
        filtered_lists = [l for l in lists if l is not None and isinstance(l, list)]

        # Ensure all lists have the same length
        if not filtered_lists or len(set(len(l) for l in filtered_lists)) > 1:
            # Return the first list as fallback if we can't merge
            return cast(List[Any], filtered_lists[0] if filtered_lists else [])

        # Merge element-wise
        result = []
        for i in range(len(filtered_lists[0])):
            elements = [l[i] for l in filtered_lists]

            # If all elements are numeric or ranges, merge them using the range handler
            if all(self.range_handler.can_handle(elements[0], e) for e in elements[1:]):
                result.append(self.range_handler.merge_values(*elements))
            else:
                # If not all elements can be handled by range handler, use the first one
                result.append(elements[0])

        self.logger.debug(f"Merged lists: {filtered_lists} → {result}")
        return result

    def is_match(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Determine if an instance list matches a concept list.

        Args:
            concept_value: The list value from the concept
            instance_value: The list value from the instance being classified

        Returns:
            True if the instance list matches the concept list element-wise, False otherwise
        """
        if not (isinstance(concept_value, list) and isinstance(instance_value, list)):
            return False

        # Lists must have the same length
        if len(concept_value) != len(instance_value):
            return False

        # Empty lists match
        if not concept_value and not instance_value:
            return True

        # Check each element
        for concept_elem, instance_elem in zip(concept_value, instance_value):
            # If elements are numeric or ranges, use range handler
            if self.range_handler.can_handle(concept_elem, instance_elem):
                if not self.range_handler.is_match(concept_elem, instance_elem):
                    return False
            # Otherwise, require exact match
            elif concept_elem != instance_elem:
                return False

        return True
