import networkx as nx
import logging
import sys
import os

# Adjust import path for the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from maximum_common_subgraph import MaximumCommonMinorGraph
from property_handlers import (
    PropertyHandlerManager,
    RangePropertyHandler,
    ListPropertyHandler,
)

# Configure logging to see the debug messages
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def create_test_graph(graph_id, props):
    """Create a test graph with numeric properties."""
    G = nx.Graph()

    # Add a node with specific properties
    G.add_node(f"{graph_id}_node1", labels=["Point", "StartPoint"], **props)

    # Add a second node
    G.add_node(f"{graph_id}_node2", labels=["Point"])

    # Connect the nodes
    G.add_edge(f"{graph_id}_node1", f"{graph_id}_node2")

    return G


def print_property_comparison(property_name, g_val, h_val, mcm_val):
    """Print a formatted comparison of property values for each graph."""
    print(f"\nProperty: {property_name}")
    print(f"  Graph G: {g_val}")
    print(f"  Graph H: {h_val}")
    print(f"  Result:  {mcm_val}")


def test_range_property_handler():
    """Test that the RangePropertyHandler correctly handles numeric properties."""
    print("\n=== Testing RangePropertyHandler ===")

    handler = RangePropertyHandler()

    # Test single values
    print("\nMerging simple numeric values:")
    result = handler.merge_values(10, 20, 30)
    print(f"  10, 20, 30 -> {result}")

    # Test existing range values
    print("\nMerging with existing range:")
    existing_range = {"min": 5, "max": 15, "type": "range", "center": 10}
    result = handler.merge_values(existing_range, 20)
    print(f"  Range {existing_range}, 20 -> {result}")

    # Test matching
    print("\nTesting range matching:")
    concept_range = {"min": 5, "max": 15, "type": "range", "center": 10}
    test_values = [4, 5, 10, 15, 16]
    for val in test_values:
        print(
            f"  Does {val} match range {concept_range}? {handler.is_match(concept_range, val)}"
        )


def test_list_property_handler():
    """Test that the ListPropertyHandler correctly handles lists of numeric values."""
    print("\n=== Testing ListPropertyHandler ===")

    handler = ListPropertyHandler()

    # Test lists of numbers
    print("\nMerging lists of numeric values:")
    list1 = [10, 20, 30]
    list2 = [15, 20, 35]
    result = handler.merge_values(list1, list2)
    print(f"  {list1}, {list2} -> {result}")

    # Test with existing ranges in the list
    print("\nMerging with lists containing ranges:")
    list_with_ranges = [
        {"min": 5, "max": 15, "type": "range", "center": 10},
        20,
        {"min": 25, "max": 35, "type": "range", "center": 30},
    ]
    new_list = [12, 20, 32]
    result = handler.merge_values(list_with_ranges, new_list)
    print(f"  List with ranges + {new_list} -> {result}")

    # Test matching
    print("\nTesting list matching:")
    concept_list = [
        {"min": 5, "max": 15, "type": "range", "center": 10},
        {"min": 18, "max": 22, "type": "range", "center": 20},
        {"min": 25, "max": 35, "type": "range", "center": 30},
    ]
    test_lists = [
        [10, 20, 30],  # Should match
        [5, 22, 35],  # Should match
        [4, 20, 30],  # Should not match
        [10, 20, 36],  # Should not match
    ]
    for i, test_list in enumerate(test_lists):
        print(
            f"  Does {test_list} match concept list? {handler.is_match(concept_list, test_list)}"
        )


def test_property_handler_manager():
    """Test that the PropertyHandlerManager correctly coordinates property handlers."""
    print("\n=== Testing PropertyHandlerManager ===")

    manager = PropertyHandlerManager()

    # Test processing node properties with mixed property types
    concept_props = {
        "labels": ["Point", "StartPoint"],
        "exact_match": "hello",
        "numeric": 10,
        "coords": [10, 20, 30],
    }

    g_props = {
        "labels": ["Point", "StartPoint", "Special"],
        "exact_match": "hello",
        "numeric": 15,
        "coords": [15, 20, 35],
        "unique_to_g": "only in g",
    }

    h_props = {
        "labels": ["Point", "StartPoint", "Extra"],
        "exact_match": "hello",
        "numeric": 20,
        "coords": [5, 20, 25],
        "unique_to_h": "only in h",
    }

    result = manager.process_node_properties(concept_props, g_props, h_props)

    print("\nInput properties:")
    print(f"  Concept: {concept_props}")
    print(f"  G:       {g_props}")
    print(f"  H:       {h_props}")
    print("\nResult properties:")
    print(f"  {result}")

    # Test property matching
    print("\nTesting property matching:")

    numeric_range = {"min": 5, "max": 15, "type": "range", "center": 10}
    test_values = [5, 10, 15, 20]

    for val in test_values:
        print(
            f"  Does {val} match {numeric_range}? {manager.is_property_match(numeric_range, val)}"
        )


def test_with_maximum_common_minor_graph():
    """Test the integration with MaximumCommonMinorGraph."""
    print("\n=== Testing with MaximumCommonMinorGraph ===")

    # Create two graphs with different numeric values
    G = create_test_graph(
        "G", {"x": 10, "y": 20, "z": 30, "coords": [5, 10, 15], "string": "hello"}
    )

    H = create_test_graph(
        "H", {"x": 15, "y": 20, "z": 40, "coords": [7, 10, 18], "string": "hello"}
    )

    # Find the maximum common minor graph
    mcm_finder = MaximumCommonMinorGraph()
    mcm, G_to_mcm, H_to_mcm, _ = mcm_finder.find_max_common_minor_with_start_points(
        G, H
    )

    # Get the node in the result
    g_node = "G_node1"
    h_node = "H_node1"
    mcm_node = G_to_mcm[g_node]

    print("\nProperties in result:")
    for prop, value in mcm.nodes[mcm_node].items():
        if prop != "labels":
            g_val = G.nodes[g_node].get(prop, "(not present)")
            h_val = H.nodes[h_node].get(prop, "(not present)")
            print_property_comparison(prop, g_val, h_val, value)


def test_numeric_property_merging():
    """Test the handling of numeric properties like relative_distance."""
    print("\n=== Testing Numeric Property Merging ===")

    # Configure more detailed logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create a property handler manager
    manager = PropertyHandlerManager()

    # Create test properties similar to those in the production issue
    g_props = {
        "labels": ["Point", "StartPoint"],
        "contour_type": "OPEN",
        "monotony": "NON_MONOTONIC",
        "relative_distance": 0.2,
        "cycle_count": 0,
    }

    h_props = {
        "labels": ["Point", "StartPoint"],
        "contour_type": "OPEN",
        "monotony": "NON_MONOTONIC",
        "relative_distance": 0.3,
        "cycle_count": 0,
    }

    # Test property processing
    result = manager.process_node_properties({}, g_props, h_props)

    print("\nInput properties:")
    print(f"  G: {g_props}")
    print(f"  H: {h_props}")
    print("\nResult properties:")
    print(f"  {result}")

    # Test specific handling of relative_distance
    print("\nTesting numeric property handling:")
    range_handler = RangePropertyHandler()
    can_handle = range_handler.can_handle(0.2, 0.3)
    merged = range_handler.merge_values(0.2, 0.3) if can_handle else "Cannot handle"

    print(f"  Can handle 0.2 and 0.3? {can_handle}")
    print(f"  Merged result: {merged}")


if __name__ == "__main__":
    test_range_property_handler()
    test_list_property_handler()
    test_property_handler_manager()
    test_with_maximum_common_minor_graph()
    test_numeric_property_merging()
