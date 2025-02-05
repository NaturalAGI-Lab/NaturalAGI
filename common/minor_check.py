import networkx as nx
from itertools import combinations
from typing import Optional


def is_minor(graph: nx.Graph, concept: nx.Graph) -> bool:
    """
    Checks if 'concept' is a minor of 'graph' by enumerating possible node deletions
    and then recursively contracting edges until the subgraph has the same number
    of edges as 'concept'.

    - Retains all node data in the subgraph/contracted graph.
    - Only uses 'labels' field to compare nodes for isomorphism.
    """

    # Quick size checks
    if concept.number_of_nodes() > graph.number_of_nodes():
        return False
    if concept.number_of_edges() > graph.number_of_edges():
        return False

    # Prune early if the graph doesn't have enough labels to match concept
    if not _check_label_feasibility(graph, concept):
        return False

    # We'll define a node_match function that ONLY checks labels overlap.
    # We ignore everything else in node data for the match.
    def node_match(n1_data: dict, n2_data: dict) -> bool:
        labels1 = n1_data.get("labels", set())
        labels2 = n2_data.get("labels", set())
        # Two nodes match if they share at least one label
        return bool(labels1 & labels2)

    # How many nodes must we remove from 'graph'?
    to_remove = graph.number_of_nodes() - concept.number_of_nodes()

    # For each subset of nodes to delete
    for nodes_subset in combinations(list(graph.nodes()), to_remove):
        # Check if removing these nodes kills feasibility of labels
        if not _delete_feasibility_check(graph, nodes_subset, concept):
            continue

        # Build a subgraph with those nodes removed
        G_sub = graph.copy()
        G_sub.remove_nodes_from(nodes_subset)

        # We now need to contract edges so that G_sub has the same # of edges as concept
        needed_contractions = G_sub.number_of_edges() - concept.number_of_edges()

        if needed_contractions < 0:
            # Not enough edges to match concept's connectivity
            continue
        if needed_contractions == 0:
            # Just check isomorphism right away
            if nx.is_isomorphic(G_sub, concept, node_match=node_match):
                return True
            continue

        # Otherwise, recursively contract the necessary number of edges
        if _contract_recursive(G_sub, needed_contractions, concept, node_match):
            return True

    return False


def _contract_recursive(
    G_sub: nx.Graph, needed_contractions: int, concept: nx.Graph, node_match
) -> bool:
    """
    Recursively contract 'needed_contractions' edges in G_sub.
    Maintains a list of original node UUIDs that were merged into each node.
    """
    # If we have contracted enough edges, check isomorphism
    if needed_contractions == 0:
        return nx.is_isomorphic(G_sub, concept, node_match=node_match)

    edges = list(G_sub.edges())
    if len(edges) < needed_contractions:
        return False

    # Try each edge in turn
    for u, v in edges:
        G_copy = G_sub.copy()

        # Merge the original_nodes lists
        u_nodes = G_copy.nodes[u].get("original_nodes", [u])
        v_nodes = G_copy.nodes[v].get("original_nodes", [v])
        merged_nodes = u_nodes + v_nodes

        # Do the contraction
        G_copy = nx.contracted_nodes(G_copy, u, v, self_loops=False)

        # Store the list of original nodes that were merged into this node
        G_copy.nodes[u]["original_nodes"] = merged_nodes

        # Keep only labels for isomorphism checking
        G_copy.nodes[u]["labels"] = set(G_sub.nodes[u].get("labels", set())) | set(
            G_sub.nodes[v].get("labels", set())
        )

        # Recurse with one fewer contraction needed
        if _contract_recursive(G_copy, needed_contractions - 1, concept, node_match):
            return True

    return False


def _merge_node_data(data_u: dict, data_v: dict) -> dict:
    """
    Merge the data dictionaries from two nodes u and v.
    - 'labels' fields are unioned
    - All other fields are merged according to specific rules
    """
    merged = {}

    # Special handling for labels - always union them
    labels_u = data_u.get("labels", set())
    labels_v = data_v.get("labels", set())
    merged["labels"] = labels_u.union(labels_v)

    # Merge all other fields
    all_keys = set(data_u.keys()) | set(data_v.keys())
    for key in all_keys:
        if key == "labels":
            continue  # already handled

        # For numeric values, take average
        if key in data_u and key in data_v:
            val_u = data_u[key]
            val_v = data_v[key]
            if isinstance(val_u, (int, float)) and isinstance(val_v, (int, float)):
                merged[key] = (val_u + val_v) / 2
            else:
                # For non-numeric values, prefer data_u's value
                merged[key] = data_u[key]
        elif key in data_u:
            merged[key] = data_u[key]
        else:
            merged[key] = data_v[key]

    return merged


def _check_label_feasibility(graph: nx.Graph, concept: nx.Graph) -> bool:
    """
    Quick check: If concept requires more occurrences of any label
    than graph can provide, skip immediately.
    """
    from collections import Counter

    graph_labels = Counter()
    concept_labels = Counter()

    # Count labels in the graph
    for _, data in graph.nodes(data=True):
        lbls = data.get("labels", set())
        graph_labels.update(lbls)

    # Count labels in the concept
    for _, data in concept.nodes(data=True):
        lbls = data.get("labels", set())
        concept_labels.update(lbls)

    # If concept needs more of any label than the graph has, return False
    for label, needed_count in concept_labels.items():
        if graph_labels[label] < needed_count:
            return False

    return True


def _delete_feasibility_check(graph: nx.Graph, nodes_subset, concept: nx.Graph) -> bool:
    """
    If removing 'nodes_subset' from 'graph' eliminates critical labels
    needed to match 'concept', return False immediately.
    """
    from collections import Counter

    to_delete_set = set(nodes_subset)
    remaining_labels = Counter()

    for node in graph.nodes():
        if node not in to_delete_set:
            node_labels = graph.nodes[node].get("labels", set())
            remaining_labels.update(node_labels)

    concept_labels = Counter()
    for _, data in concept.nodes(data=True):
        concept_labels.update(data.get("labels", set()))

    for label, cnt_needed in concept_labels.items():
        if remaining_labels[label] < cnt_needed:
            return False

    return True


#######################################
# 2) Enumerate All Minors of a Graph  #
#######################################
def enumerate_minors(
    base_graph: nx.Graph, max_nodes: int = 5, max_enumerations: int = 1000
):
    """
    Generates minor graphs by enumerating all sub-node sets (up to max_nodes)
    and recursively contracting edges to produce unique minors.

    Args:
        base_graph: The graph from which to enumerate minors
        max_nodes: Maximum number of nodes in the enumerated minors
        max_enumerations: How many minors to generate before stopping
                          (just to avoid infinite blow-ups)

    Returns:
        A set of minors (each minor is returned as a "canonical" form).
    """
    all_minors = set()
    enumerations_count = 0

    graph_nodes = list(base_graph.nodes())
    n = len(graph_nodes)

    for subset_size in range(1, min(max_nodes, n) + 1):
        for subset in combinations(graph_nodes, subset_size):
            induced_sub = base_graph.subgraph(subset).copy()

            # Now consider possible edge contractions
            for minor_graph in _enumerate_contractions(induced_sub):
                enumerations_count += 1
                if enumerations_count > max_enumerations:
                    return all_minors  # early exit
                cstring = _canonical_label(minor_graph)
                all_minors.add(cstring)

    return all_minors


def _enumerate_contractions(graph: nx.Graph):
    """
    Yields all possible contractions from the given graph.
    We do a DFS: each edge can be contracted or not.
    """
    # Yield the original graph
    yield graph

    edges = list(graph.edges())
    for i, (u, v) in enumerate(edges):
        G_copy = graph.copy()
        merged_labels = set(G_copy.nodes[u].get("labels", set())) | set(
            G_copy.nodes[v].get("labels", set())
        )
        nx.contracted_nodes(G_copy, u, v, self_loops=False, copy=False)
        G_copy.nodes[u]["labels"] = merged_labels

        # Recurse
        yield from _enumerate_contractions(G_copy)


def _canonical_label(g: nx.Graph) -> str:
    """
    Create a string that uniquely identifies a graph's structure and node labels.
    (Naive approach—real solutions might use NAUTY/Bliss for a perfect canonical form.)
    """
    labels_map = {}
    for node in sorted(g.nodes()):
        lbls = sorted(g.nodes[node].get("labels", []))
        labels_map[node] = ",".join(lbls)

    edges_sorted = []
    for a, b in g.edges():
        edges_sorted.append(tuple(sorted([a, b])))
    edges_sorted.sort()

    node_part = ";".join([f"{node}:{labels_map[node]}" for node in sorted(labels_map)])
    edge_part = ",".join([f"({u}=>{v})" for (u, v) in edges_sorted])
    return f"N[{node_part}] E[{edge_part}]"


############################################
# 3) Rebuild Graph from Canonical String   #
############################################
def parse_cstring_to_graph(cstr: str) -> nx.Graph:
    """
    Parse the canonical string back into a networkx.Graph with 'labels' attributes.
    Format: N[node_entries]E[edge_entries] where:
    - node_entries are semicolon-separated: node_info:labels
    - edge_entries are comma-separated: (node1=>node2)

    Example:
    N[4:Point,EndPoint;5:Point,Vector]E[(4=>5),(5=>6)]
    """
    import re

    g = nx.Graph()

    match_nodes = re.search(r"N\[(.*?)\]", cstr)
    match_edges = re.search(r"E\[(.*?)\]", cstr)
    if not match_nodes:
        return g

    # Parse nodes
    nodes_part = match_nodes.group(1)
    node_entries = nodes_part.split(";") if nodes_part else []

    for node_entry in node_entries:
        if not node_entry:
            continue

        # Split by the last colon to separate labels from node info
        parts = node_entry.rsplit(":", 1)
        if len(parts) != 2:
            continue

        node_info, lbl_str = parts
        labels = set(lbl_str.split(",")) if lbl_str else set()
        g.add_node(node_info, labels=labels)

    # Parse edges
    if match_edges:
        edges_part = match_edges.group(1)
        # Split on closing parenthesis and remove empty strings
        edge_entries = [e.strip() for e in edges_part.split(")") if e.strip()]

        for e in edge_entries:
            # Clean up the edge entry
            e = e.replace("(", "").strip()
            if "=>" not in e:
                continue

            u, v = e.split("=>")
            u, v = u.strip(), v.strip()  # Remove any whitespace
            if u in g.nodes and v in g.nodes:
                g.add_edge(u, v)

    return g


############################################
# 4) find_common_minors_in_dataset (Revised)
############################################
def find_common_minors_in_dataset_return_biggest(
    graphs: list[nx.Graph], max_nodes: int = 5
) -> Optional[nx.Graph]:
    """
    Modified to restore properties after finding the common minor.
    """
    # 1) Pick the smallest graph
    smallest_graph = min(graphs, key=lambda g: g.number_of_nodes())

    # 2) Enumerate minors (as canonical strings)
    print("Enumerating minors from the smallest graph...")
    candidate_minors_cstrings = enumerate_minors(
        smallest_graph, max_nodes=max_nodes, max_enumerations=2000
    )
    print(
        f"Found {len(candidate_minors_cstrings)} candidate minors (some might be duplicates)."
    )

    # 3) For each candidate, parse into a graph, and check if it's a minor of all other graphs
    all_other_graphs = [g for g in graphs if g is not smallest_graph]
    common_minors_as_graphs = []
    visited_cstrings = set()

    print("Checking each candidate minor against all other graphs...")
    for cstr in candidate_minors_cstrings:
        if cstr in visited_cstrings:
            continue
        visited_cstrings.add(cstr)

        minor_graph = parse_cstring_to_graph(cstr)

        # Check if it's a minor of all other graphs
        is_common = True
        for g in all_other_graphs:
            if not is_minor(g, minor_graph):
                is_common = False
                break

        if is_common:
            common_minors_as_graphs.append(minor_graph)

    # 4) Return the 'largest' common minor if any exist
    if common_minors_as_graphs:
        # Sort descending by (#nodes, #edges)
        common_minors_as_graphs.sort(
            key=lambda mg: (mg.number_of_nodes(), mg.number_of_edges()), reverse=True
        )
        biggest_minor = common_minors_as_graphs[0]
        # Restore properties from original graphs
        return restore_node_properties(biggest_minor, graphs)
    else:
        return None


def restore_node_properties(
    minor_graph: nx.Graph, source_graphs: list[nx.Graph]
) -> nx.Graph:
    """
    Restores original node properties from source graphs based on stored original_nodes.
    For merged nodes, properties are averaged or combined according to type.
    """
    result = minor_graph.copy()

    for node in result.nodes():
        original_nodes = result.nodes[node].get("original_nodes", [node])
        merged_data = {}

        # Collect all properties from original nodes across all source graphs
        for source_graph in source_graphs:
            for orig_node in original_nodes:
                if orig_node in source_graph:
                    node_data = source_graph.nodes[orig_node]
                    for key, value in node_data.items():
                        if key == "original_nodes":
                            continue
                        if key not in merged_data:
                            merged_data[key] = []
                        merged_data[key].append(value)

        # Merge collected properties
        final_data = {}
        for key, values in merged_data.items():
            if not values:
                continue

            if key == "labels":
                # Union all label sets
                final_data[key] = set().union(
                    *[v if isinstance(v, set) else {v} for v in values]
                )
            elif all(isinstance(v, (int, float)) for v in values):
                # Average numeric values
                final_data[key] = sum(values) / len(values)
            else:
                # For other types, take the most common value
                final_data[key] = max(set(values), key=values.count)

        # Update node data
        result.nodes[node].update(final_data)

    return result


#######################################
# 5) Example Usage / Demo
#######################################
if __name__ == "__main__":
    import time

    # Graph 1: L-shape with additional properties
    G1 = nx.Graph()
    G1.add_node("p1", labels={"EndPoint", "Point"}, x=0, y=0, weight=1.0)
    G1.add_node("p2", labels={"CornerPoint", "Point"}, x=0, y=1, weight=2.0)
    G1.add_node("p3", labels={"EndPoint", "Point"}, x=0, y=2, weight=3.0)
    G1.add_node("p4", labels={"EndPoint", "Point"}, x=1, y=1, weight=4.0)
    G1.add_node("v1", labels={"VerticalVector", "Vector"}, length=1.0)
    G1.add_node("v2", labels={"VerticalVector", "Vector"}, length=1.0)
    G1.add_node("v3", labels={"HorizontalVector", "Vector"}, length=1.0)
    G1.add_edge("p1", "v1")
    G1.add_edge("v1", "p2")
    G1.add_edge("p2", "v2")
    G1.add_edge("v2", "p3")
    G1.add_edge("p2", "v3")
    G1.add_edge("v3", "p4")

    # Graph 2: a smaller shape with properties
    G2 = nx.Graph()
    G2.add_node("p1", labels={"EndPoint", "Point"}, x=5, y=5, weight=10.0)
    G2.add_node("p2", labels={"EndPoint", "Point"}, x=5, y=6, weight=20.0)
    G2.add_node("v1", labels={"VerticalVector", "Vector"}, length=1.0)
    G2.add_edge("p1", "v1")
    G2.add_edge("v1", "p2")

    # Graph 3: Just a single line segment with a corner and properties
    G3 = nx.Graph()
    G3.add_node("p1", labels={"CornerPoint", "Point"}, x=10, y=10, weight=100.0)
    G3.add_node("p2", labels={"EndPoint", "Point"}, x=10, y=11, weight=200.0)
    G3.add_node("v1", labels={"VerticalVector", "Vector"}, length=1.0)
    G3.add_edge("p1", "v1")
    G3.add_edge("v1", "p2")

    dataset = [G1, G2, G3]

    start = time.time()
    common_minors_graph = find_common_minors_in_dataset_return_biggest(
        dataset, max_nodes=3
    )
    elapsed = time.time() - start

    print("\n=== Testing Property Retention ===")
    print("\nCommon Minor Found:")
    print("Nodes with all properties:")
    for node, data in common_minors_graph.nodes(data=True):
        print(f"\nNode {node}:")
        for key, value in data.items():
            print(f"  {key}: {value}")

    print("\nEdges:", common_minors_graph.edges())
    print(f"\nExecution time: {elapsed:.4f} seconds")

    # Verify that properties were merged correctly
    print("\nVerifying property merging:")
    for node, data in common_minors_graph.nodes(data=True):
        if "weight" in data:
            print(f"Node {node} has weight: {data['weight']}")
        if "x" in data and "y" in data:
            print(f"Node {node} has coordinates: ({data['x']}, {data['y']})")
        if "length" in data:
            print(f"Node {node} has length: {data['length']}")
