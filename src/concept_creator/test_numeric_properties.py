import networkx as nx
import logging
from maximum_common_subgraph import MaximumCommonSubgraph, MaximumCommonMinorGraph

# Configure logging
logging.basicConfig(level=logging.DEBUG)


def test_numeric_properties_in_nodes():
    # Create two simple graphs with numeric properties
    G = nx.Graph()
    H = nx.Graph()

    # Add nodes to G with numeric properties
    G.add_node(0, labels=["StartPoint"], relative_distance=0.2, count=10)
    G.add_node(1, labels=["Point"], relative_distance=0.3, count=5)

    # Add nodes to H with slightly different numeric properties
    H.add_node(0, labels=["StartPoint"], relative_distance=0.25, count=8)
    H.add_node(1, labels=["Point"], relative_distance=0.35, count=7)

    # Add edges
    G.add_edge(0, 1, weight=1.5)
    H.add_edge(0, 1, weight=1.7)

    # Create a MaximumCommonSubgraph instance
    mcs = MaximumCommonSubgraph()

    # Find the maximum common subgraph
    common_graph, G_to_common, H_to_common = mcs.find_max_common_subgraph(G, H)

    print("Maximum Common Subgraph:")
    print(f"Nodes: {common_graph.nodes(data=True)}")
    print(f"Edges: {common_graph.edges(data=True)}")

    # Check if numeric properties are processed correctly
    for node, data in common_graph.nodes(data=True):
        print(f"Node {node} properties: {data}")
        # Check if relative_distance is a range dictionary
        if "relative_distance" in data:
            if isinstance(data["relative_distance"], dict):
                print(
                    f"  relative_distance is correctly a range: {data['relative_distance']}"
                )
            else:
                print(
                    f"  ERROR: relative_distance is not a range: {data['relative_distance']}"
                )

    # Now test with MaximumCommonMinorGraph
    print("\nTesting MaximumCommonMinorGraph:")
    mcm = MaximumCommonMinorGraph()

    # Find the maximum common minor graph
    minor_graph, G_to_minor, H_to_minor, _ = (
        mcm.find_max_common_minor_with_start_points(G, H)
    )

    print("Maximum Common Minor Graph:")
    print(f"Nodes: {minor_graph.nodes(data=True)}")
    print(f"Edges: {minor_graph.edges(data=True)}")

    # Check if numeric properties are processed correctly
    for node, data in minor_graph.nodes(data=True):
        print(f"Node {node} properties: {data}")
        # Check if relative_distance is a range dictionary
        if "relative_distance" in data:
            if isinstance(data["relative_distance"], dict):
                print(
                    f"  relative_distance is correctly a range: {data['relative_distance']}"
                )
            else:
                print(
                    f"  ERROR: relative_distance is not a range: {data['relative_distance']}"
                )


if __name__ == "__main__":
    test_numeric_properties_in_nodes()
