import logging
from typing import Any, Dict, List, Optional

from .property_matcher import PropertyMatcher
from .range_property_matcher import RangePropertyMatcher
from .list_property_matcher import ListPropertyMatcher
from .enum_property_matcher import EnumPropertyMatcher


class PropertyMatcherManager:
    """
    Manages a collection of property matchers and coordinates property matching.

    This class provides a unified interface for the classification process
    without needing to know about specific matcher implementations.
    """

    # List of keys that should not be matched because they are not relevant to the classification
    LIST_IGNORE_KEYS = [
        "labels",
        "visualization",
        "session_id",
        "concept_id",
        "uuid",
        "x",
        "y",
        "x1",
        "y1",
        "x2",
        "y2",
        "quadrant_change_count",  # TODO check if this is relevant
        "length",
        "direction_sequence_index",
        "corner_points_count",
        "normalized_x",
        "normalized_y",
        "relative_distance",
        "angle_with_ox",
        "angle"
    ]

    def __init__(self):
        """
        Initialize the PropertyMatcherManager with default matchers.
        """
        self.logger = logging.getLogger(__name__)
        self.matchers: List[PropertyMatcher] = [
            RangePropertyMatcher(),
            ListPropertyMatcher(list_matching_mode="subset"),
            EnumPropertyMatcher(),
        ]

    def add_matcher(self, matcher: PropertyMatcher) -> None:
        """Add a custom property matcher to the manager."""
        self.matchers.append(matcher)

    def find_matcher(
        self, concept_value: Any, instance_value: Any
    ) -> Optional[PropertyMatcher]:
        """
        Find the first matcher that can handle the given property values.

        Args:
            concept_value: Value from the concept
            instance_value: Value from the instance being classified

        Returns:
            The first matcher that can handle the values, or None if no matcher is found
        """
        for matcher in self.matchers:
            if matcher.can_handle(concept_value, instance_value):
                return matcher
        return None

    def is_property_match(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Check if an instance property value matches a concept property value.

        Args:
            concept_value: The property value from the concept
            instance_value: The property value from the instance being classified

        Returns:
            True if the values match according to a matcher, or by exact equality if no matcher is found
        """
        # Special case for None values
        if concept_value is None and instance_value is None:
            return True

        # If one is None but the other isn't, no match
        if concept_value is None or instance_value is None:
            return False

        # Try to find a matcher
        matcher = self.find_matcher(concept_value, instance_value)
        if matcher:
            return matcher.is_match(concept_value, instance_value)

        # Special case for strings - more flexible matching
        if isinstance(concept_value, str) and isinstance(instance_value, str):
            # Exact match for short strings
            if len(concept_value) <= 3 or len(instance_value) <= 3:
                return concept_value == instance_value

            # Case-insensitive contains for longer strings
            return (
                concept_value.lower() in instance_value.lower()
                or instance_value.lower() in concept_value.lower()
            )

        # If no matcher is found, use exact equality
        return concept_value == instance_value

    def check_node_properties_match(
        self, concept_node_data: Dict[str, Any], instance_node_data: Dict[str, Any]
    ) -> bool:
        """
        Check if all properties of a concept node match an instance node.

        Args:
            concept_node_data: Properties of the concept node
            instance_node_data: Properties of the instance node

        Returns:
            True if all concept properties match the instance, False otherwise
        """
        concept_id = concept_node_data.get("concept_id")
        # Check labels first
        if "labels" in concept_node_data:
            concept_labels = set(concept_node_data["labels"])
            instance_labels = set(instance_node_data.get("labels", []))

            if not concept_labels.issubset(instance_labels):
                self.logger.info(
                    f"Concept labels {concept_labels} are not a subset of instance labels {instance_labels} for concept {concept_id}"
                )
                return False

        # Check other properties
        for key, concept_value in concept_node_data.items():
            if key not in PropertyMatcherManager.LIST_IGNORE_KEYS:
                if key not in instance_node_data:
                    self.logger.info(
                        f"No key {key} in classified image node {instance_node_data} for concept {concept_id}"
                    )
                    return False

                instance_value = instance_node_data[key]

                # Apply flexible matching based on data type
                if not self.is_property_match(concept_value, instance_value):
                    self.logger.info(
                        f"Property {key} does not match: {concept_value} != {instance_value} for concept {concept_id}"
                    )
                    return False

        return True
