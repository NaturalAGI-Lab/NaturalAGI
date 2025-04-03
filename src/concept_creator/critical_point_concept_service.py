import logging
import networkx as nx
from typing import Dict, List, Tuple, Any, Optional, Set
import uuid

from concept_creation_repository import ConceptCreationRepository
from property_handlers.property_handler_manager import PropertyHandlerManager
from node_similarity_calculator import NodeSimilarityCalculator
from graph_minor_finder import GraphMinorFinder


class CriticalPointConceptService:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.repository = ConceptCreationRepository(
            neo4j_uri, neo4j_user, neo4j_password
        )
        self.prop_manager = PropertyHandlerManager()
        self.similarity_calculator = NodeSimilarityCalculator()
        self.graph_minor_finder = GraphMinorFinder()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("CriticalPointConceptService initialized.")

    def create_concept_incrementally(
        self, session_id: str, concept_id: Optional[str] = None, steps: Optional[int] = None
    ) -> Tuple[str, nx.Graph]:
        """
        Create a concept incrementally by finding the intersection graph of all training samples.
        This follows the algorithm described in the concept formation documentation.

        Args:
            session_id: The session ID to create a concept for
            concept_id: Optional concept ID to use. If not provided, a new one will be generated.

        Returns:
            Tuple of (concept_id, concept_graph)
        """
        self.logger.info(
            f"Creating concept for session {session_id} using Critical Point approach."
        )

        if not concept_id:
            concept_id = str(uuid.uuid4())

        # Get all image IDs for the session
        image_ids = self.repository.get_image_ids_for_session(session_id)

        if not image_ids:
            raise ValueError(f"No images found for session {session_id}")

        # Start with the first image as the initial concept
        first_image_id = image_ids[0]
        concept_graph = self.repository.get_image_graph(first_image_id)

        # Initialize the concept with the first image
        self.logger.info(
            f"Initialized concept with graph from image {first_image_id}. Nodes: {len(concept_graph.nodes)}"
        )

        # Process each additional image
        for i, image_id in enumerate(image_ids[1:], 2):
            if steps and i > steps:
                break
            self.logger.info(f"Processing image {i}/{len(image_ids)}: {image_id}")
            image_graph = self.repository.get_image_graph(image_id)

            # Find the intersection graph between current concept and new image
            concept_graph = self.graph_minor_finder.find_max_common_minor(
                concept_graph, image_graph
            )

            self.logger.info(
                f"Updated concept after image {image_id}. Nodes: {len(concept_graph.nodes)}"
            )

        # # Save the final concept
        # self.repository.save_concept(concept_id, concept_graph)

        # for image_id in image_ids:
        #     self.repository.remove_image_data(image_id)

        return concept_id, concept_graph
