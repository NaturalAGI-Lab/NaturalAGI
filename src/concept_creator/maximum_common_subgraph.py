import networkx as nx
import logging
from typing import Dict, List, Set, Tuple, Optional, Any, Callable


class MaximumCommonSubgraph:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def find_max_common_subgraph(
        self, G: nx.Graph, H: nx.Graph
    ) -> Tuple[nx.Graph, Dict, Dict]:
        """
        Find the maximum common subgraph between G and H.

        Args:
            G: First graph
            H: Second graph

        Returns:
            Tuple containing:
            - The maximum common subgraph
            - Mapping from G nodes to common subgraph nodes
            - Mapping from H nodes to common subgraph nodes
        """
        # Create product graph
        product_graph = self._create_product_graph(G, H)

        # Find maximum clique
        clique = self._find_max_clique(product_graph)

        # Convert clique to subgraph
        mcs, G_to_mcs, H_to_mcs = self._clique_to_subgraph(clique, G, H)

        return mcs, G_to_mcs, H_to_mcs

    def _create_product_graph(self, G: nx.Graph, H: nx.Graph) -> nx.Graph:
        """Create product graph for MCS algorithm."""
        product = nx.Graph()

        # Add nodes to product graph
        for g_node in G.nodes():
            for h_node in H.nodes():
                if self._nodes_match(G.nodes[g_node], H.nodes[h_node]):
                    product.add_node((g_node, h_node), g_node=g_node, h_node=h_node)

        # Add edges
        for g1, h1 in product.nodes():
            for g2, h2 in product.nodes():
                if g1 != g2 and h1 != h2:
                    # Check if edge exists in both graphs
                    if G.has_edge(g1, g2) and H.has_edge(h1, h2):
                        if self._edges_match(G[g1][g2], H[h1][h2]):
                            product.add_edge((g1, h1), (g2, h2))

        return product

    def _nodes_match(self, node1: Dict, node2: Dict) -> bool:
        """
        Check if two nodes match based on their properties.

        Special handling for node labels - they must have at least one common label.
        Other properties must match exactly.
        """
        # Special handling for 'labels' property if it exists
        if "labels" in node1 and "labels" in node2:
            labels1 = set(node1["labels"])
            labels2 = set(node2["labels"])
            if not labels1.intersection(labels2):
                return False

        # Check if one is a StartPoint - if so, the other must be too
        if ("labels" in node1 and "StartPoint" in node1.get("labels", [])) != (
            "labels" in node2 and "StartPoint" in node2.get("labels", [])
        ):
            return False

        return True

    def _edges_match(self, edge1: Dict, edge2: Dict) -> bool:
        """
        Check if two edges match based on their presence only, not their properties.
        """
        # We only care about the presence of edges, not their properties
        return True

    def _find_max_clique(self, graph: nx.Graph) -> List:
        """
        Find approximate maximum clique in the given graph.
        Using NetworkX's approximation algorithm for efficiency.
        """
        try:
            # For large graphs, use approximation algorithm
            if len(graph.nodes()) > 100:
                clique = nx.approximation.max_clique(graph)
            else:
                # For smaller graphs, we can use the exact algorithm
                clique = nx.algorithms.clique.find_cliques(graph)
                clique = max(clique, key=len, default=[])
        except Exception as e:
            self.logger.warning(f"Error finding maximum clique: {e}")
            clique = []

        return clique

    def _clique_to_subgraph(
        self, clique: List, G: nx.Graph, H: nx.Graph
    ) -> Tuple[nx.Graph, Dict, Dict]:
        """
        Convert a clique in the product graph to the maximum common subgraph.

        Returns:
            - The maximum common subgraph
            - Mapping from G nodes to common subgraph nodes
            - Mapping from H nodes to common subgraph nodes
        """
        mcs = nx.Graph()
        G_to_mcs = {}
        H_to_mcs = {}

        # Create nodes in the MCS
        for i, (g_node, h_node) in enumerate(clique):
            mcs_node = i  # Use index as node ID in MCS
            mcs.add_node(mcs_node)

            # Merge properties from both nodes, keeping only matching properties
            g_props = G.nodes[g_node]
            h_props = H.nodes[h_node]

            # Special handling for labels - intersection
            if "labels" in g_props and "labels" in h_props:
                labels1 = set(g_props["labels"])
                labels2 = set(h_props["labels"])
                mcs.nodes[mcs_node]["labels"] = list(labels1.intersection(labels2))

            # Copy other matching properties
            for key in set(g_props.keys()).intersection(set(h_props.keys())):
                if key != "labels" and g_props[key] == h_props[key]:
                    mcs.nodes[mcs_node][key] = g_props[key]

            # Store mappings
            G_to_mcs[g_node] = mcs_node
            H_to_mcs[h_node] = mcs_node

        # Create edges in the MCS
        for i, (g1, h1) in enumerate(clique):
            for j, (g2, h2) in enumerate(clique):
                if i < j and G.has_edge(g1, g2) and H.has_edge(h1, h2):
                    mcs.add_edge(G_to_mcs[g1], G_to_mcs[g2])

                    # Merge edge properties, keeping only matching ones
                    g_edge = G[g1][g2]
                    h_edge = H[h1][h2]

                    for key in set(g_edge.keys()).intersection(set(h_edge.keys())):
                        if g_edge[key] == h_edge[key]:
                            mcs[G_to_mcs[g1]][G_to_mcs[g2]][key] = g_edge[key]

        return mcs, G_to_mcs, H_to_mcs


class MaximumCommonMinorGraph(MaximumCommonSubgraph):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def find_max_common_minor(
        self,
        G: nx.Graph,
        H: nx.Graph,
        visualization_callback: Optional[Callable] = None,
    ) -> Tuple[nx.Graph, Dict, Dict, List]:
        """
        Find the maximum common minor graph between two input graphs.

        Args:
            G: First input graph
            H: Second input graph
            visualization_callback: Optional callback for visualization during the process
                Expected signature: callback(step_name, G, H, mcm, G_to_mcm, H_to_mcm, contractions, property_changes)
                where property_changes is a list of dicts with node property changes

        Returns:
            Tuple containing:
            - The maximum common minor graph
            - A mapping from G nodes to MCM nodes
            - A mapping from H nodes to MCM nodes
            - List of contractions applied (tuples of (g_node, g_neighbor, h_node, h_neighbor))
        """
        # First find maximum common subgraph
        mcs, G_to_mcs, H_to_mcs = self.find_max_common_subgraph(G, H)

        if visualization_callback:
            # For initial MCS, there are no property changes yet
            visualization_callback(
                "Initial MCS", G, H, mcs, G_to_mcs, H_to_mcs, [], None
            )

        # Find potential contractions to expand the common graph
        potential_contractions = self._find_potential_contractions(
            G, H, G_to_mcs, H_to_mcs
        )

        # Apply contractions to create maximum common minor
        mcm, G_to_mcm, H_to_mcm, applied_contractions = self._apply_contractions(
            mcs, G, H, G_to_mcs, H_to_mcs, potential_contractions
        )

        # Generate property changes information for visualization
        property_changes = []
        if applied_contractions:
            # Compare properties before and after contractions
            for g_node, g_neighbor, h_node, h_neighbor in applied_contractions:
                # Check if these nodes are now represented in the MCM
                if g_node in G_to_mcm and h_node in H_to_mcm:
                    mcm_node = G_to_mcm[
                        g_node
                    ]  # or H_to_mcm[h_node], should be the same

                    # Get original properties
                    g_props = G.nodes[g_node]
                    h_props = H.nodes[h_node]
                    mcm_props = mcm.nodes[mcm_node]

                    for prop in set(g_props.keys()) | set(h_props.keys()):
                        if prop in g_props and prop in h_props and prop in mcm_props:
                            if (
                                g_props[prop] != mcm_props[prop]
                                or h_props[prop] != mcm_props[prop]
                            ):
                                property_changes.append(
                                    {
                                        "G Node": g_node,
                                        "H Node": h_node,
                                        "MCM Node": mcm_node,
                                        "Property": prop,
                                        "G Value": g_props.get(prop, "(not present)"),
                                        "H Value": h_props.get(prop, "(not present)"),
                                        "MCM Value": mcm_props.get(
                                            prop, "(not present)"
                                        ),
                                    }
                                )

        if visualization_callback and applied_contractions:
            visualization_callback(
                "After Contractions",
                G,
                H,
                mcm,
                G_to_mcm,
                H_to_mcm,
                applied_contractions,
                property_changes,
            )

        return mcm, G_to_mcm, H_to_mcm, applied_contractions

    def _find_potential_contractions(
        self, G: nx.Graph, H: nx.Graph, G_to_mcs: Dict, H_to_mcs: Dict
    ) -> List:
        """
        Find potential edge contractions that could extend the match.

        Returns a list of potential contractions in format:
        [(g_node1, g_node2, h_node1, h_node2), ...]
        """
        potential_contractions = []

        # Nodes in G not in the common subgraph
        G_unmatched = set(G.nodes()) - set(G_to_mcs.keys())

        # Nodes in H not in the common subgraph
        H_unmatched = set(H.nodes()) - set(H_to_mcs.keys())

        # For each unmatched node in G
        for g_node in G_unmatched:
            # Find its neighbors that are in the common subgraph
            g_matched_neighbors = [n for n in G.neighbors(g_node) if n in G_to_mcs]

            # For each unmatched node in H
            for h_node in H_unmatched:
                # Find its neighbors that are in the common subgraph
                h_matched_neighbors = [n for n in H.neighbors(h_node) if n in H_to_mcs]

                # Check if there's potential for contraction
                for g_neighbor in g_matched_neighbors:
                    for h_neighbor in h_matched_neighbors:
                        # If both neighbors map to the same node in the MCS
                        if G_to_mcs[g_neighbor] == H_to_mcs[h_neighbor]:
                            potential_contractions.append(
                                (g_node, g_neighbor, h_node, h_neighbor)
                            )

        # Sort by the number of common neighbors to prioritize better contractions
        potential_contractions.sort(
            key=lambda c: self._contraction_quality(G, H, c[0], c[1], c[2], c[3]),
            reverse=True,
        )

        return potential_contractions

    def _contraction_quality(
        self,
        G: nx.Graph,
        H: nx.Graph,
        g_node: Any,
        g_neighbor: Any,
        h_node: Any,
        h_neighbor: Any,
    ) -> int:
        """
        Calculate a quality score for a potential contraction.
        Higher is better.
        """
        # Count common neighbors - higher means better structural similarity
        g_neighbors = set(G.neighbors(g_node)) & set(G.neighbors(g_neighbor))
        h_neighbors = set(H.neighbors(h_node)) & set(H.neighbors(h_neighbor))

        # Node similarity score based on properties
        node_similarity = (
            1 if self._nodes_match(G.nodes[g_node], H.nodes[h_node]) else 0
        )

        return len(g_neighbors) + len(h_neighbors) + 10 * node_similarity

    def _apply_contractions(
        self,
        mcs: nx.Graph,
        G: nx.Graph,
        H: nx.Graph,
        G_to_mcs: Dict,
        H_to_mcs: Dict,
        contractions: List,
    ) -> Tuple[nx.Graph, Dict, Dict, List]:
        """
        Apply valid contractions to grow the common structure.

        Returns:
            - The maximum common minor graph
            - Updated mapping from G nodes to minor graph nodes
            - Updated mapping from H nodes to minor graph nodes
            - List of applied contractions
        """
        # Make a copy of the MCS as our starting point for the minor
        mcm = mcs.copy()
        G_to_mcm = G_to_mcs.copy()
        H_to_mcm = H_to_mcs.copy()
        applied_contractions = []

        # For each potential contraction
        for g_node, g_neighbor, h_node, h_neighbor in contractions:
            # Skip if already processed
            if g_node in G_to_mcm or h_node in H_to_mcm:
                continue

            # Get the common node in the minor that g_neighbor and h_neighbor map to
            common_node = G_to_mcm[g_neighbor]

            # Add g_node and h_node to the mapping
            G_to_mcm[g_node] = common_node
            H_to_mcm[h_node] = common_node

            # Update properties of the node in the minor graph
            # (only keeping properties that match both G and H)
            self._update_node_properties(mcm, common_node, G, g_node, H, h_node)

            # Track the contraction
            applied_contractions.append((g_node, g_neighbor, h_node, h_neighbor))

        return mcm, G_to_mcm, H_to_mcm, applied_contractions

    def _update_node_properties(
        self,
        mcm: nx.Graph,
        mcm_node: Any,
        G: nx.Graph,
        g_node: Any,
        H: nx.Graph,
        h_node: Any,
    ) -> None:
        """
        Update properties of a node in the minor graph after contraction.
        Only keep properties that match in both G and H and are consistent with existing properties.
        """
        g_props = G.nodes[g_node]
        h_props = H.nodes[h_node]

        # Special handling for labels - intersection
        if "labels" in g_props and "labels" in h_props:
            current_labels = set(mcm.nodes[mcm_node].get("labels", []))
            new_labels = current_labels.intersection(
                set(g_props["labels"]).intersection(set(h_props["labels"]))
            )
            mcm.nodes[mcm_node]["labels"] = list(new_labels)

        # Keep only properties that are in all nodes mapped to mcm_node
        for key in list(mcm.nodes[mcm_node].keys()):
            if key != "labels":
                # Remove property if it's not in both g_node and h_node or values don't match
                if not (
                    key in g_props
                    and key in h_props
                    and g_props[key] == h_props[key] == mcm.nodes[mcm_node][key]
                ):
                    del mcm.nodes[mcm_node][key]

        # Add new properties from g_node and h_node that match, if not already present
        for key in set(g_props.keys()).intersection(set(h_props.keys())):
            if key != "labels" and g_props[key] == h_props[key]:
                if key not in mcm.nodes[mcm_node]:
                    mcm.nodes[mcm_node][key] = g_props[key]

    def find_max_common_minor_with_start_points(
        self,
        G: nx.Graph,
        H: nx.Graph,
        visualization_callback: Optional[Callable] = None,
    ) -> Tuple[nx.Graph, Dict, Dict, List]:
        """
        Find the maximum common minor graph with special handling for StartPoint nodes.
        This method first anchors the matching on StartPoints, then grows the common minor.

        Args:
            G: First input graph
            H: Second input graph
            visualization_callback: Optional callback for visualization during the process
                Expected signature: callback(step_name, G, H, mcm, G_to_mcm, H_to_mcm, contractions, property_changes)

        Returns:
            Tuple containing:
            - The maximum common minor graph
            - A mapping from G nodes to MCM nodes
            - A mapping from H nodes to MCM nodes
            - List of contractions applied
        """
        # Initialize mappings and MCM
        G_to_mcm = {}
        H_to_mcm = {}
        initial_mcm = nx.Graph()

        # Get all StartPoint nodes from both graphs
        G_start_points = [
            node
            for node, attrs in G.nodes(data=True)
            if "labels" in attrs and "StartPoint" in attrs["labels"]
        ]
        H_start_points = [
            node
            for node, attrs in H.nodes(data=True)
            if "labels" in attrs and "StartPoint" in attrs["labels"]
        ]

        if visualization_callback:
            temp_G = G.copy()
            temp_H = H.copy()
            # Highlight start points for visualization
            for n in G_start_points:
                if "visualization" not in temp_G.nodes[n]:
                    temp_G.nodes[n]["visualization"] = {}
                temp_G.nodes[n]["visualization"]["highlight"] = True
            for n in H_start_points:
                if "visualization" not in temp_H.nodes[n]:
                    temp_H.nodes[n]["visualization"] = {}
                temp_H.nodes[n]["visualization"]["highlight"] = True
            visualization_callback(
                "Start Points", temp_G, temp_H, initial_mcm, {}, {}, [], None
            )

        # Property change tracking for visualization
        property_changes = []

        # If both graphs have start points, match them first
        if G_start_points and H_start_points:
            # Match start points (assuming all start points are compatible)
            for i, g_start in enumerate(G_start_points):
                # If we have more start points in G than H, only use the first len(H_start_points)
                if i >= len(H_start_points):
                    break

                h_start = H_start_points[i]

                # Create a new node in MCM for this matched pair
                mcm_node = i  # Use index as node ID
                initial_mcm.add_node(mcm_node)

                # Copy properties from G node
                g_props = G.nodes[g_start]
                h_props = H.nodes[h_start]

                # Track property differences
                for prop in set(g_props.keys()) | set(h_props.keys()):
                    if prop in g_props and prop in h_props:
                        if g_props[prop] != h_props[prop]:
                            # Remember we'll use G's value in the MCM node
                            property_changes.append(
                                {
                                    "G Node": g_start,
                                    "H Node": h_start,
                                    "MCM Node": mcm_node,
                                    "Property": prop,
                                    "G Value": g_props.get(prop, "(not present)"),
                                    "H Value": h_props.get(prop, "(not present)"),
                                    "MCM Value": g_props.get(
                                        prop, "(not present)"
                                    ),  # Using G's value
                                }
                            )

            # Set properties to the intersection of g_props and h_props
            if "labels" in g_props and "labels" in h_props:
                labels1 = set(g_props["labels"])
                labels2 = set(h_props["labels"])
                initial_mcm.nodes[mcm_node]["labels"] = list(labels1.intersection(labels2))

            for key in set(g_props.keys()).intersection(set(h_props.keys())):
                if key != "labels" and g_props[key] == h_props[key]:
                    initial_mcm.nodes[mcm_node][key] = g_props[key]

            G_to_mcm[g_start] = mcm_node
            H_to_mcm[h_start] = mcm_node

            if visualization_callback:
                visualization_callback(
                    "Initial Anchoring",
                    G,
                    H,
                    initial_mcm,
                    G_to_mcm,
                    H_to_mcm,
                    [],
                    property_changes,
                )

        # If we couldn't match any start points, fall back to the regular approach
        if not initial_mcm.nodes():
            return self.find_max_common_minor(G, H, visualization_callback)

        # Grow the common minor from the matched start points
        mcm, G_to_mcm, H_to_mcm, contractions = self._grow_common_minor(
            initial_mcm, G, H, G_to_mcm, H_to_mcm
        )

        # Update property changes for the final result
        final_property_changes = []
        for g_node, mcm_node in G_to_mcm.items():
            if g_node in G and mcm_node in mcm:
                # Find the corresponding H node if any
                h_nodes = [h for h, m in H_to_mcm.items() if m == mcm_node]
                h_node = h_nodes[0] if h_nodes else None

                if h_node and h_node in H:
                    g_props = G.nodes[g_node]
                    h_props = H.nodes[h_node]
                    mcm_props = mcm.nodes[mcm_node]

                    for prop in set(g_props.keys()) | set(h_props.keys()):
                        if prop in g_props and prop in h_props and prop in mcm_props:
                            if (
                                g_props[prop] != mcm_props[prop]
                                or h_props[prop] != mcm_props[prop]
                            ):
                                final_property_changes.append(
                                    {
                                        "G Node": g_node,
                                        "H Node": h_node,
                                        "MCM Node": mcm_node,
                                        "Property": prop,
                                        "G Value": g_props.get(prop, "(not present)"),
                                        "H Value": h_props.get(prop, "(not present)"),
                                        "MCM Value": mcm_props.get(
                                            prop, "(not present)"
                                        ),
                                    }
                                )

        if visualization_callback:
            visualization_callback(
                "Final MCM",
                G,
                H,
                mcm,
                G_to_mcm,
                H_to_mcm,
                contractions,
                final_property_changes,
            )

        return mcm, G_to_mcm, H_to_mcm, contractions

    def _grow_common_minor(
        self,
        initial_mcm: nx.Graph,
        G: nx.Graph,
        H: nx.Graph,
        G_to_mcm: Dict,
        H_to_mcm: Dict,
    ) -> Tuple[nx.Graph, Dict, Dict, List]:
        """
        Grow the common minor graph from the initial match.

        Args:
            initial_mcm: Initial common graph
            G: First graph
            H: Second graph
            G_to_mcm: Mapping from G nodes to common graph nodes
            H_to_mcm: Mapping from H nodes to common graph nodes

        Returns:
            Tuple containing:
            - The maximum common minor graph
            - Mapping from G nodes to minor graph nodes
            - Mapping from H nodes to minor graph nodes
            - List of edge contractions applied
        """
        mcm = initial_mcm.copy()
        G_to_mcm = G_to_mcm.copy()
        H_to_mcm = H_to_mcm.copy()
        applied_contractions = []

        # Keep track of frontier nodes to explore
        g_frontier = set(
            n for node in G_to_mcm for n in G.neighbors(node) if n not in G_to_mcm
        )
        h_frontier = set(
            n for node in H_to_mcm for n in H.neighbors(node) if n not in H_to_mcm
        )

        # Continue growing until no more matches can be found
        while g_frontier and h_frontier:
            # Find best match between frontier nodes
            best_match = None
            best_score = -1

            for g_node in g_frontier:
                for h_node in h_frontier:
                    # Check if the nodes can be matched
                    if self._nodes_match(G.nodes[g_node], H.nodes[h_node]):
                        # Find common neighbors that are already matched
                        g_matched_neighbors = {
                            G_to_mcm[n] for n in G.neighbors(g_node) if n in G_to_mcm
                        }
                        h_matched_neighbors = {
                            H_to_mcm[n] for n in H.neighbors(h_node) if n in H_to_mcm
                        }

                        common_neighbors = g_matched_neighbors.intersection(
                            h_matched_neighbors
                        )
                        score = len(common_neighbors)

                        if score > best_score:
                            best_score = score
                            best_match = (g_node, h_node)

            # If no good match found, try contractions
            if best_match is None:
                # Find potential contractions
                contractions = self._find_potential_contractions(
                    G, H, G_to_mcm, H_to_mcm
                )

                # Apply first valid contraction
                if contractions:
                    g_node, g_neighbor, h_node, h_neighbor = contractions[0]

                    # Get the common node in the minor
                    common_node = G_to_mcm[g_neighbor]

                    # Add to mapping
                    G_to_mcm[g_node] = common_node
                    H_to_mcm[h_node] = common_node

                    # Update properties
                    self._update_node_properties(mcm, common_node, G, g_node, H, h_node)

                    # Track contraction
                    applied_contractions.append(
                        (g_node, g_neighbor, h_node, h_neighbor)
                    )

                    # Update frontier
                    g_frontier = set(
                        n
                        for node in G_to_mcm
                        for n in G.neighbors(node)
                        if n not in G_to_mcm
                    )
                    h_frontier = set(
                        n
                        for node in H_to_mcm
                        for n in H.neighbors(node)
                        if n not in H_to_mcm
                    )
                else:
                    # No more matches or contractions possible
                    break
            else:
                # Add matched nodes to the common graph
                g_node, h_node = best_match
                mcm_node = len(mcm.nodes())
                mcm.add_node(mcm_node)

                # Merge properties
                g_props = G.nodes[g_node]
                h_props = H.nodes[h_node]

                # Special handling for labels
                if "labels" in g_props and "labels" in h_props:
                    labels1 = set(g_props["labels"])
                    labels2 = set(h_props["labels"])
                    mcm.nodes[mcm_node]["labels"] = list(labels1.intersection(labels2))

                # Copy other matching properties
                for key in set(g_props.keys()).intersection(set(h_props.keys())):
                    if key != "labels" and g_props[key] == h_props[key]:
                        mcm.nodes[mcm_node][key] = g_props[key]

                # Update mappings
                G_to_mcm[g_node] = mcm_node
                H_to_mcm[h_node] = mcm_node

                # Add edges to already matched nodes
                for g_neighbor in G.neighbors(g_node):
                    if g_neighbor in G_to_mcm:
                        mcm.add_edge(mcm_node, G_to_mcm[g_neighbor])

                # Update frontier
                g_frontier = set(
                    n
                    for node in G_to_mcm
                    for n in G.neighbors(node)
                    if n not in G_to_mcm
                )
                h_frontier = set(
                    n
                    for node in H_to_mcm
                    for n in H.neighbors(node)
                    if n not in H_to_mcm
                )

        return mcm, G_to_mcm, H_to_mcm, applied_contractions
