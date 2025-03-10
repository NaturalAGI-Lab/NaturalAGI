import networkx as nx
import logging
import hashlib
import json
from typing import Dict, List, Tuple, Set, Any, Optional, Callable

from maximum_common_subgraph import MaximumCommonMinorGraph
from concept_creation_repository import ConceptCreationRepository
from neo4j_to_networkx import Neo4jToNetworkx
from networkx_to_neo4j import NetworkxToNeo4j


class EnergyMinimizationConceptService:
    def __init__(self, uri: str, user: str, password: str):
        self.repository = ConceptCreationRepository(uri, user, password)
        self.neo4j_to_networkx = Neo4jToNetworkx()
        self.networkx_to_neo4j = NetworkxToNeo4j()
        self.mcm_finder = MaximumCommonMinorGraph()
        self.logger = logging.getLogger(__name__)

    def create_concept_incrementally(
        self,
        session_id: str,
        concept_id: str = None,
        visualization_callback: Optional[Callable] = None,
    ) -> Tuple[str, nx.Graph]:
        """
        Create a concept graph incrementally using the Maximum Common Minor Graph approach.

        Args:
            session_id: The session ID containing the images to process
            concept_id: Optional concept ID to use (defaults to None, will be generated)
            visualization_callback: Optional callback function for visualization of each step
                Expected signature: callback(step_number, pre_concept, image_graph, post_concept, mcm_results, concept_to_new)
                where:
                    - mcm_results is a tuple of (mcm, concept_to_mcm, image_to_mcm, new_contractions)
                    - concept_to_new is a mapping from pre_concept nodes to post_concept nodes

        Returns:
            The ID of the created concept and the final concept graph
        """
        self.logger.info(
            f"Creating concept incrementally for session {session_id} using traversal-based MCMG approach"
        )

        # Get all image IDs for the session
        image_ids = self.repository.get_image_ids_for_session(session_id)
        self.logger.info(f"Found {len(image_ids)} images for session {session_id}")

        if not image_ids:
            raise ValueError(f"No images found for session {session_id}")

        # Initialize with the first image's graph
        first_image_id = image_ids[0]
        concept_graph = self._extract_graph_for_image(first_image_id)

        # Call visualization callback for the first image if provided
        if visualization_callback:
            # For the first step, there is no pre-concept or mapping
            visualization_callback(1, None, concept_graph, concept_graph, None, None)

        # Track all applied contractions for the concept
        all_contractions = []

        # Process remaining images
        for i, image_id in enumerate(image_ids[1:], 2):
            self.logger.info(f"Processing image {i}/{len(image_ids)}")

            # Extract graph for current image
            image_graph = self._extract_graph_for_image(image_id)

            # Save pre-update concept graph for visualization
            pre_concept = concept_graph.copy() if visualization_callback else None

            # Find maximum common minor with start points
            mcm_results = self.mcm_finder.find_max_common_minor_with_start_points(
                concept_graph, image_graph
            )

            mcm, concept_to_mcm, image_to_mcm, new_contractions = mcm_results

            # Create a mapping from original concept nodes to new concept nodes
            # This is important for tracking property changes
            concept_to_new = {}
            for orig_node, mcm_node in concept_to_mcm.items():
                concept_to_new[orig_node] = mcm_node

            # Update concept graph to be the maximum common minor
            concept_graph = mcm

            # Track contractions
            all_contractions.extend(new_contractions)

            self.logger.info(
                f"After processing image {i}, concept has {len(concept_graph.nodes())} nodes, "
                f"{len(concept_graph.edges())} edges, and {len(new_contractions)} new contractions"
            )

            # Call visualization callback if provided
            if visualization_callback:
                visualization_callback(
                    i,
                    pre_concept,
                    image_graph,
                    concept_graph,
                    mcm_results,
                    concept_to_new,
                )

        # Generate a concept ID based on the graph structure if not provided
        if concept_id is None:
            concept_id = self._generate_concept_id(concept_graph)

        # Store the concept graph
        # self._save_concept_graph(concept_id, concept_graph)

        # # Clean up processing data
        # self._cleanup_processed_images(image_ids)

        self.logger.info(
            f"Created concept with ID {concept_id} using traversal-based MCMG approach. "
            f"Final concept has {len(concept_graph.nodes())} nodes, {len(concept_graph.edges())} edges, and "
            f"{len(all_contractions)} total contractions"
        )

        return concept_id, concept_graph

    def _extract_graph_for_image(self, image_id: str) -> nx.Graph:
        """
        Extract a NetworkX graph for the given image ID from Neo4j.
        """
        nodes_and_edges = self.repository.get_nodes_and_edges_for_image(image_id)
        graph = self.neo4j_to_networkx.convert(nodes_and_edges)

        self.logger.info(
            f"Extracted graph for image {image_id} with {len(graph.nodes())} nodes and {len(graph.edges())} edges"
        )

        return graph

    def _generate_concept_id(self, graph: nx.Graph) -> str:
        """
        Generate a deterministic ID for the concept based on its graph structure.
        """
        # Create a dictionary representation of the graph
        graph_dict = {"nodes": [], "edges": []}

        # Sort nodes by their degree and properties for deterministic ordering
        sorted_nodes = sorted(
            graph.nodes(data=True),
            key=lambda n: (graph.degree(n[0]), self._sort_dict(n[1])),
        )

        for i, (node, attrs) in enumerate(sorted_nodes):
            node_dict = {"id": i}
            node_dict.update(attrs)
            graph_dict["nodes"].append(node_dict)

        # Create a mapping from original node IDs to sorted IDs
        node_mapping = {node: i for i, (node, _) in enumerate(sorted_nodes)}

        # Sort edges for deterministic ordering
        sorted_edges = []
        for u, v, attrs in graph.edges(data=True):
            sorted_edges.append(
                (
                    min(node_mapping[u], node_mapping[v]),
                    max(node_mapping[u], node_mapping[v]),
                    attrs,
                )
            )

        sorted_edges.sort(key=lambda e: (e[0], e[1], self._sort_dict(e[2])))

        for u, v, attrs in sorted_edges:
            edge_dict = {"source": u, "target": v}
            edge_dict.update(attrs)
            graph_dict["edges"].append(edge_dict)

        # Create a deterministic JSON string and hash it
        graph_json = json.dumps(graph_dict, sort_keys=True)
        concept_id = hashlib.sha256(graph_json.encode()).hexdigest()

        return concept_id

    def _sort_dict(self, d: Dict) -> str:
        """Helper method to convert a dictionary to a deterministic string representation."""
        return json.dumps(d, sort_keys=True)

    def _save_concept_graph(self, concept_id: str, graph: nx.Graph) -> None:
        """
        Save the concept graph to Neo4j.
        """
        # Add concept ID to all nodes and edges
        for node in graph.nodes():
            graph.nodes[node]["concept_id"] = concept_id

        for u, v in graph.edges():
            graph[u][v]["concept_id"] = concept_id

        # Convert to Neo4j format and save
        neo4j_data = self.networkx_to_neo4j.convert(graph)
        self.repository.save_concept(concept_id, neo4j_data)

    def _cleanup_processed_images(self, image_ids: List[str]) -> None:
        """
        Remove processed image data to free up resources.
        """
        for image_id in image_ids:
            self.repository.remove_image_data(image_id)
            self.logger.info(f"Removed data for image {image_id}")
