import networkx as nx
import logging
from typing import List, Tuple

from maximum_common_subgraph import MaximumCommonMinorGraph
from concept_creation_repository import ConceptCreationRepository
from neo4j_to_networkx import Neo4jToNetworkx
from networkx_to_neo4j import NetworkxToNeo4j
from utils.uuid_generator import UUIDGenerator

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
    ) -> Tuple[str, nx.Graph]:
        """
        Create a concept graph incrementally using the Maximum Common Minor Graph approach.

        Args:
            session_id: The session ID containing the images to process
            concept_id: Optional concept ID to use (defaults to None, will be generated)

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
        concept_graph = self.repository.get_image_graph(first_image_id)

        # Track all applied contractions for the concept
        all_contractions = []

        # Process remaining images
        for i, image_id in enumerate(image_ids[1:], 2):
            self.logger.info(f"Processing image {i}/{len(image_ids)}")

            # Extract graph for current image
            image_graph = self.repository.get_image_graph(image_id)

            # Find maximum common minor with start points
            mcm_results = self.mcm_finder.find_max_common_minor_with_start_points(
                concept_graph, image_graph
            )

            mcm, concept_to_mcm, image_to_mcm, new_contractions = mcm_results

            # Create a mapping from original concept nodes to new concept nodes
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

        # Generate a concept ID based on the graph structure if not provided
        if concept_id is None:
            concept_id = UUIDGenerator.generate_concept_id(concept_graph)

        # Log the final concept graph nodes for debugging
        self.logger.info("Final concept graph nodes:")
        for node_id, node_attrs in concept_graph.nodes(data=True):
            self.logger.info(f"Node {node_id}: {node_attrs}")

        # Store the concept graph
        self.repository.save_concept(concept_id, concept_graph)

        # Clean up processing data
        # self._cleanup_processed_images(image_ids)

        self.logger.info(
            f"Created concept with ID {concept_id} using traversal-based MCMG approach. "
            f"Final concept has {len(concept_graph.nodes())} nodes, {len(concept_graph.edges())} edges, and "
            f"{len(all_contractions)} total contractions"
        )

        return concept_id, concept_graph

    def _cleanup_processed_images(self, image_ids: List[str]) -> None:
        """
        Remove processed image data to free up resources.
        """
        for image_id in image_ids:
            self.repository.remove_image_data(image_id)
            self.logger.info(f"Removed data for image {image_id}")
