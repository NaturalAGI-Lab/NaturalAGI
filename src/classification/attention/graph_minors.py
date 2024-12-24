import networkx as nx
from itertools import combinations
from typing import Set


def is_minor(graph: nx.Graph, concept: nx.Graph) -> bool:
    """
    Check if concept is a minor of graph, considering node labels and edge types.

    Parameters:
    graph (nx.Graph): The original geometric structure graph
    concept (nx.Graph): The concept graph to check as a minor

    Returns:
    bool: True if concept is a minor of graph, False otherwise
    """
    if concept.number_of_nodes() > graph.number_of_nodes():
        return False

    def node_match(n1: dict, n2: dict) -> bool:
        """Compare node labels for compatibility"""
        labels1 = set(n1.get("labels", set()))
        labels2 = set(n2.get("labels", set()))
        if not labels1 or not labels2:
            return True
        return bool(labels1 & labels2)

    for nodes_to_delete in combinations(
        graph.nodes, graph.number_of_nodes() - concept.number_of_nodes()
    ):
        G_sub = graph.copy()
        G_sub.remove_nodes_from(nodes_to_delete)

        if G_sub.number_of_edges() >= concept.number_of_edges():
            for edges_to_contract in combinations(
                G_sub.edges, G_sub.number_of_edges() - concept.number_of_edges()
            ):
                G_contracted = G_sub.copy()
                for u, v in edges_to_contract:
                    if G_contracted.has_edge(u, v):
                        # Merge node labels during contraction
                        u_labels = set(G_contracted.nodes[u].get("labels", set()))
                        v_labels = set(G_contracted.nodes[v].get("labels", set()))
                        merged_labels = u_labels | v_labels

                        G_contracted = nx.contracted_nodes(
                            G_contracted, u, v, self_loops=False, copy=False
                        )
                        # Update labels of the contracted node
                        G_contracted.nodes[u]["labels"] = merged_labels

                if nx.is_isomorphic(G_contracted, concept, node_match=node_match):
                    return True
    return False

if __name__ == "__main__":
    import time

    # Create a simple geometric structure (L-shape)
    graph_r = nx.Graph()
    # Points
    graph_r.add_node(1, labels={"EndPoint", "Point"})
    graph_r.add_node(2, labels={"CornerPoint", "Point"})
    graph_r.add_node(3, labels={"EndPoint", "Point"})
    graph_r.add_node(4, labels={"EndPoint", "Point"})
    # Vectors as nodes
    graph_r.add_node("v1", labels={"VerticalVector", "Vector"})
    graph_r.add_node("v2", labels={"VerticalVector", "Vector"})
    graph_r.add_node("v3", labels={"HorizontalVector", "Vector"})
    # Connect points through vectors
    graph_r.add_edge(1, "v1")
    graph_r.add_edge("v1", 2)
    graph_r.add_edge(2, "v2")
    graph_r.add_edge("v2", 3)
    graph_r.add_edge(2, "v3")
    graph_r.add_edge("v3", 4)

    # Create a concept (vertical line)
    graph_c = nx.Graph()
    # Points
    graph_c.add_node(1, labels={"EndPoint", "Point"})
    graph_c.add_node(2, labels={"EndPoint", "Point"})
    # Vector as node
    graph_c.add_node("v1", labels={"VerticalVector", "Vector"})
    # Connect points through vector
    graph_c.add_edge(1, "v1")
    graph_c.add_edge("v1", 2)

    start_time = time.time()
    result = is_minor(graph_r, graph_c)
    execution_time = time.time() - start_time

    print(f"Vertical line concept is a minor of L-shape: {result}")  # Should be True
    print(f"Execution time: {execution_time:.4f} seconds")
