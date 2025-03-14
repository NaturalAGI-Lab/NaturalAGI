import networkx as nx
import logging
from typing import Dict, List, Tuple, Any

from property_handlers import PropertyHandlerManager


class MaximumCommonSubgraph:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.property_manager = PropertyHandlerManager()

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

            # Merge properties from both nodes using PropertyHandlerManager
            g_props = G.nodes[g_node]
            h_props = H.nodes[h_node]

            # First handle labels specially
            initial_props = {}
            if "labels" in g_props and "labels" in h_props:
                labels1 = set(g_props["labels"])
                labels2 = set(h_props["labels"])
                initial_props["labels"] = list(labels1.intersection(labels2))

            # Use property manager to process all properties if available
            if hasattr(self, "property_manager"):
                processed_props = self.property_manager.process_node_properties(
                    initial_props, g_props, h_props
                )
                mcs.nodes[mcs_node].update(processed_props)
            else:
                # Fall back to simple property matching if property_manager not available
                mcs.nodes[mcs_node].update(initial_props)
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
                    # Add the edge
                    mcs.add_edge(G_to_mcs[g1], G_to_mcs[g2])

                    # Get edge properties
                    g_edge = G[g1][g2]
                    h_edge = H[h1][h2]

                    # Process edge properties using PropertyHandlerManager if available
                    if hasattr(self, "property_manager"):
                        edge_props = self.property_manager.process_node_properties(
                            {}, g_edge, h_edge
                        )
                        mcs[G_to_mcs[g1]][G_to_mcs[g2]].update(edge_props)
                    else:
                        # Fall back to simple property matching
                        for key in set(g_edge.keys()).intersection(set(h_edge.keys())):
                            if g_edge[key] == h_edge[key]:
                                mcs[G_to_mcs[g1]][G_to_mcs[g2]][key] = g_edge[key]

        return mcs, G_to_mcs, H_to_mcs


class MaximumCommonMinorGraph(MaximumCommonSubgraph):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.property_manager = PropertyHandlerManager()

    def find_max_common_minor(
        self,
        G: nx.Graph,
        H: nx.Graph,
    ) -> Tuple[nx.Graph, Dict, Dict, List]:
        """
        Find the maximum common minor graph between two input graphs.

        Args:
            G: First input graph
            H: Second input graph

        Returns:
            Tuple containing:
            - The maximum common minor graph
            - A mapping from G nodes to MCM nodes
            - A mapping from H nodes to MCM nodes
            - List of contractions applied (tuples of (g_node, g_neighbor, h_node, h_neighbor))
        """
        # First find maximum common subgraph
        mcs, G_to_mcs, H_to_mcs = self.find_max_common_subgraph(G, H)

        # Find potential contractions to expand the common graph
        potential_contractions = self._find_potential_contractions(
            G, H, G_to_mcs, H_to_mcs
        )

        # Apply contractions to create maximum common minor
        mcm, G_to_mcm, H_to_mcm, applied_contractions = self._apply_contractions(
            mcs, G, H, G_to_mcs, H_to_mcs, potential_contractions
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
        Uses the PropertyHandlerManager to process different property types:
        - For labels: uses intersection
        - For numeric properties: creates range representations (min/max)
        - For numeric arrays: creates element-wise ranges
        - For other properties: keeps only matching properties
        """
        # Get the properties for each node
        mcm_props = mcm.nodes[mcm_node]
        g_props = G.nodes[g_node]
        h_props = H.nodes[h_node]

        self.logger.debug(f"Updating node properties for MCM node {mcm_node}")
        self.logger.debug(f"  MCM props before: {mcm_props}")
        self.logger.debug(f"  G props: {g_props}")
        self.logger.debug(f"  H props: {h_props}")

        # Use the property manager to update properties
        updated_props = self.property_manager.process_node_properties(
            mcm_props, g_props, h_props
        )

        self.logger.debug(f"  Updated props after merging: {updated_props}")

        # Update the node properties in the graph
        mcm.nodes[mcm_node].clear()
        mcm.nodes[mcm_node].update(updated_props)

    def find_max_common_minor_with_start_points(
        self,
        G: nx.Graph,
        H: nx.Graph,
    ) -> Tuple[nx.Graph, Dict, Dict, List]:
        """
        Find the maximum common minor graph with special handling for StartPoint nodes.
        This method first anchors the matching on StartPoints, then grows the common minor.

        Args:
            G: First input graph
            H: Second input graph

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

            # Set properties to the intersection of g_props and h_props
            if "labels" in g_props and "labels" in h_props:
                labels1 = set(g_props["labels"])
                labels2 = set(h_props["labels"])
                initial_mcm.nodes[mcm_node]["labels"] = list(
                    labels1.intersection(labels2)
                )

            # Instead of only copying exact matching properties,
            # use the PropertyHandlerManager to properly process all properties
            # including numeric ones that should be converted to ranges
            initial_props = {}
            if "labels" in initial_mcm.nodes[mcm_node]:
                initial_props["labels"] = initial_mcm.nodes[mcm_node]["labels"]

            # Process properties using the property manager
            processed_props = self.property_manager.process_node_properties(
                initial_props, g_props, h_props
            )

            # Update the node properties
            initial_mcm.nodes[mcm_node].update(processed_props)

            self.logger.debug(
                f"StartPoint properties after processing: {initial_mcm.nodes[mcm_node]}"
            )

            G_to_mcm[g_start] = mcm_node
            H_to_mcm[h_start] = mcm_node

        # If we couldn't match any start points, fall back to the regular approach
        if not initial_mcm.nodes():
            return self.find_max_common_minor(G, H)

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

                # Instead of manually handling properties, use PropertyHandlerManager
                # First, handle labels specially
                initial_props = {}
                if "labels" in g_props and "labels" in h_props:
                    labels1 = set(g_props["labels"])
                    labels2 = set(h_props["labels"])
                    initial_props["labels"] = list(labels1.intersection(labels2))

                # Use the property manager to process all properties
                processed_props = self.property_manager.process_node_properties(
                    initial_props, g_props, h_props
                )

                # Update the node properties
                mcm.nodes[mcm_node].update(processed_props)

                self.logger.debug(
                    f"Regular node properties after processing: {mcm.nodes[mcm_node]}"
                )

                # Update mappings
                G_to_mcm[g_node] = mcm_node
                H_to_mcm[h_node] = mcm_node

                # Add edges to already matched nodes
                for g_neighbor in G.neighbors(g_node):
                    if g_neighbor in G_to_mcm:
                        mcm_neighbor = G_to_mcm[g_neighbor]

                        # Add the edge
                        mcm.add_edge(mcm_node, mcm_neighbor)

                        # Merge edge properties if they exist in both graphs
                        if G.has_edge(g_node, g_neighbor) and H.has_edge(
                            h_node, H_to_mcm.get(g_neighbor)
                        ):
                            g_edge = G[g_node][g_neighbor]
                            h_edge = H[h_node][H_to_mcm.get(g_neighbor)]

                            # Process edge properties
                            edge_props = self.property_manager.process_node_properties(
                                {}, g_edge, h_edge
                            )

                            # Update edge properties
                            mcm[mcm_node][mcm_neighbor].update(edge_props)

                            self.logger.debug(
                                f"Edge properties after processing: {mcm[mcm_node][mcm_neighbor]}"
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

        return mcm, G_to_mcm, H_to_mcm, applied_contractions
