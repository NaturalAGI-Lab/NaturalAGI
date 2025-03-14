import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .property_handler import PropertyHandler
from .range_property_handler import RangePropertyHandler
from .list_property_handler import ListPropertyHandler


class PropertyHandlerManager:
    """
    Manages a collection of property handlers and coordinates property processing.

    This class provides a unified interface for the concept creation process to
    handle properties without needing to know about specific handler implementations.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.handlers: List[PropertyHandler] = [
            RangePropertyHandler(),
            ListPropertyHandler(),
        ]

    def add_handler(self, handler: PropertyHandler) -> None:
        """Add a new property handler to the manager."""
        self.handlers.append(handler)

    def find_handler(self, value1: Any, value2: Any) -> Optional[PropertyHandler]:
        """
        Find the first handler that can process the given property values.

        Args:
            value1: First property value
            value2: Second property value

        Returns:
            The first handler that can process the values, or None if no handler is found
        """
        for handler in self.handlers:
            if handler.can_handle(value1, value2):
                return handler
        return None

    def can_handle_property(self, value1: Any, value2: Any) -> bool:
        """
        Check if any handler can process the given property values.

        Args:
            value1: First property value
            value2: Second property value

        Returns:
            True if a handler exists for these values, False otherwise
        """
        return self.find_handler(value1, value2) is not None

    def merge_property_values(self, *values: Any) -> Any:
        """
        Merge multiple property values using the appropriate handler.

        Args:
            *values: Variable number of property values to merge

        Returns:
            The merged property value, or the first value if no handler is found
        """
        if not values:
            return None

        # If only one value, return it directly
        if len(values) == 1:
            return values[0]

        # Find a handler for the first two values
        handler = self.find_handler(values[0], values[1])
        if handler:
            return handler.merge_values(*values)

        # If no handler is found, return the first value
        self.logger.debug(f"No handler found for values: {values}, using first value")
        return values[0]

    def is_property_match(self, concept_value: Any, instance_value: Any) -> bool:
        """
        Check if an instance property value matches a concept property value.

        Args:
            concept_value: The property value from the concept
            instance_value: The property value from the instance being classified

        Returns:
            True if the values match according to a handler, or by exact equality if no handler is found
        """
        # Try to find a handler
        handler = self.find_handler(concept_value, instance_value)
        if handler:
            return handler.is_match(concept_value, instance_value)

        # If no handler is found, use exact equality
        return concept_value == instance_value

    def process_node_properties(
        self,
        mcm_node_props: Dict[str, Any],
        g_node_props: Dict[str, Any],
        h_node_props: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process all properties of a node during concept creation.

        This method handles:
        1. Special handling for labels (intersection)
        2. Processing existing properties in the MCM node
        3. Adding new properties from G and H nodes

        Args:
            mcm_node_props: Properties of the MCM (concept) node
            g_node_props: Properties of the node from graph G
            h_node_props: Properties of the node from graph H

        Returns:
            Updated properties for the MCM node
        """
        result = mcm_node_props.copy()

        self.logger.debug(f"Processing node properties:")
        self.logger.debug(f"  MCM props: {mcm_node_props}")
        self.logger.debug(f"  G props: {g_node_props}")
        self.logger.debug(f"  H props: {h_node_props}")

        # Special handling for labels - intersection
        if "labels" in g_node_props and "labels" in h_node_props:
            current_labels = set(result.get("labels", []))
            new_labels = current_labels.intersection(
                set(g_node_props["labels"]).intersection(set(h_node_props["labels"]))
            )
            result["labels"] = list(new_labels)

        # Process existing properties
        for key in list(result.keys()):
            if key != "labels":
                # Check if property exists in both source nodes
                if key in g_node_props and key in h_node_props:
                    mcm_value = result[key]
                    g_value = g_node_props[key]
                    h_value = h_node_props[key]

                    # Case 1: Values match exactly - keep as is
                    if g_value == h_value == mcm_value:
                        self.logger.debug(
                            f"  Property {key}: Exact match {g_value}, keeping as is"
                        )
                        continue

                    # Case 2: Values can be handled by a property handler
                    if self.can_handle_property(
                        g_value, h_value
                    ) and self.can_handle_property(mcm_value, g_value):
                        # Merge values
                        self.logger.debug(
                            f"  Merging property {key}: mcm={mcm_value}, G={g_value}, H={h_value}"
                        )
                        result[key] = self.merge_property_values(
                            mcm_value, g_value, h_value
                        )
                        self.logger.debug(f"  Merged result for {key}: {result[key]}")
                    else:
                        # Case 3: Values don't match and can't be handled - remove property
                        self.logger.debug(
                            f"  Removing non-matching property {key}: mcm={mcm_value}, G={g_value}, H={h_value}"
                        )
                        self.logger.debug(
                            f"  Can handle G+H: {self.can_handle_property(g_value, h_value)}"
                        )
                        self.logger.debug(
                            f"  Can handle MCM+G: {self.can_handle_property(mcm_value, g_value)}"
                        )
                        del result[key]
                else:
                    # Property doesn't exist in both source nodes - remove it
                    self.logger.debug(
                        f"  Removing property {key} not present in both source nodes"
                    )
                    del result[key]

        # Add new properties from g_node and h_node if they match or can be merged
        for key in set(g_node_props.keys()).intersection(set(h_node_props.keys())):
            if key != "labels" and key not in result:
                g_value = g_node_props[key]
                h_value = h_node_props[key]

                # Case 1: Values match exactly - add as is
                if g_value == h_value:
                    self.logger.debug(f"  Adding matching property {key}: {g_value}")
                    result[key] = g_value
                # Case 2: Values can be handled by a property handler
                elif self.can_handle_property(g_value, h_value):
                    self.logger.debug(
                        f"  Adding merged property {key} from G={g_value}, H={h_value}"
                    )
                    merged_value = self.merge_property_values(g_value, h_value)
                    result[key] = merged_value
                    self.logger.debug(f"  Merged result for {key}: {merged_value}")
                # Otherwise, don't add the property
                else:
                    self.logger.debug(
                        f"  Skipping non-matching property {key}: G={g_value}, H={h_value}"
                    )
                    self.logger.debug(
                        f"  Can handle: {self.can_handle_property(g_value, h_value)}"
                    )

        self.logger.debug(f"Final processed properties: {result}")
        return result
