import logging
import networkx as nx
from typing import Dict, Optional
import uuid
import traceback
import copy

import numpy as np

from common.decorator import timed
from common.traversal.visitors import (
    AngleVisitor,
    QuadrantVisitor,
    DirectionVisitor,
)
from src.concept_creation_repository import ConceptCreationRepository
from src.logic.graph_analyzer import GraphAnalyzer
from src.critical_point_preprocessor import CriticalPointPreprocessor
from src.logic.start_point_modifier import StartPointModifier
from src.logic.start_point_picker import StartPointPicker
from src.model.concept_result import ConceptFormationStep, ConceptResult
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.property_handlers import PropertyProcessor
from src.synced_graph_algorithm import SyncedGraphMinorFinder


class CriticalPointConceptService:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.repository = ConceptCreationRepository(
            neo4j_uri, neo4j_user, neo4j_password
        )
        self.prop_manager = PropertyProcessor()
        self.similarity_calculator = NodeSimilarityCalculator()
        self.critical_point_preprocessor = CriticalPointPreprocessor()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.graph_minor_finder = SyncedGraphMinorFinder(
            prop_manager=self.prop_manager,
            similarity_calculator=self.similarity_calculator,
            critical_point_preprocessor=self.critical_point_preprocessor,
            logger=self.logger,
        )
        self.logger.info("CriticalPointConceptService initialized.")

    def create_concept_incrementally(
        self,
        session_id: str,
        concept_id: Optional[str] = None,
        steps: Optional[int] = None,
        debug_mode: bool = False,
    ) -> ConceptResult:
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
        image_graphs = {
            image_id: self.repository.get_image_graph(image_id)
            for image_id in image_ids
        }
        image_graphs = self._determine_start_point(image_graphs)
        image_graphs = {
            image_id: self._analyze_graph(graph)
            for image_id, graph in image_graphs.items()
        }
        steps_debug = []
        error_occurred = False
        error_message = None

        if not image_ids:
            raise ValueError(f"No images found for session {session_id}")

        # Start with the first image as the initial concept
        first_image_id = image_ids[0]
        concept_graph = image_graphs[first_image_id]
        image_graphs[first_image_id] = concept_graph
        steps_debug.append(
            ConceptFormationStep(
                current_concept=concept_graph,
                current_image=concept_graph,
                current_image_id=first_image_id,
                current_step=1,
                current_step_description="Initial concept",
                resulted_concept=concept_graph,
            )
        )
        # Initialize the concept with the first image
        self.logger.info(
            f"Initialized concept with graph from image {first_image_id}. Nodes: {len(concept_graph.nodes)}"
        )

        # Process each additional image
        for i, image_id in enumerate(image_ids[1:], 2):
            if steps and i > steps:
                break
            self.logger.info(f"Processing image {i}/{len(image_ids)}: {image_id}")
            image_graph = image_graphs[image_id]
            concept_old = copy.deepcopy(concept_graph)

            # Find the intersection graph between current concept and new image
            try:
                concept_graph = self.graph_minor_finder.find_max_common_minor(
                    copy.deepcopy(concept_old), copy.deepcopy(image_graph)
                )
            except Exception:
                # Log full stack trace for easier debugging
                error_occurred = True
                error_message = traceback.format_exc()
                self.logger.exception("Error finding max common minor", exc_info=True)
            finally:
                steps_debug.append(
                    ConceptFormationStep(
                        current_concept=concept_old,
                        current_image=image_graph,
                        current_image_id=image_id,
                        current_step=i,
                        current_step_description=f"Processing image {i}/{len(image_ids)}: {image_id}",
                        resulted_concept=None if error_occurred else concept_graph,
                    )
                )

            if error_occurred:
                break

            self.logger.info(
                f"Updated concept after image {image_id}. Nodes: {len(concept_graph.nodes)}"
            )

        # Save the final concept
        if not debug_mode and not error_occurred:
            self.repository.save_concept(concept_id, concept_graph)
            for image_id in image_ids:
                self.repository.remove_image_data(image_id)

        return ConceptResult(
            concept_id,
            concept_graph,
            image_graphs,
            steps_debug,
            is_error=error_occurred,
            error_message=error_message,
        )

    def _determine_start_point(
        self, image_graphs: Dict[str, nx.Graph]
    ) -> Dict[str, nx.Graph]:
        MAX_ITERATIONS = 15
        start_clustering_eps = 0.01
        eps_step = 0.05
        min_samples_coefficient = np.arange(0.4, 0.8)
        clustering_algorithm = "optics"
        start_point_characteristic = None

        start_point_picker = StartPointPicker(
            image_graphs.values(), clustering_algorithm=clustering_algorithm
        )
        for min_samples_coefficient in min_samples_coefficient:
            start_clustering_min_samples = int(
                len(image_graphs) * min_samples_coefficient
            )
            for _ in range(MAX_ITERATIONS):
                start_point_characteristic = (
                    start_point_picker.get_start_point_characteristic()
                )
                if start_point_characteristic is not None:
                    break
                start_point_picker.determine_start_point_characteristic(
                    clustering_eps=start_clustering_eps,
                    clustering_min_samples=start_clustering_min_samples,
                )
                start_clustering_eps += eps_step
                start_clustering_min_samples += 1
            if start_point_characteristic is not None:
                break

        if start_point_characteristic is None:
            self.logger.error("Could not determine start point characteristic")
            raise ValueError("Could not determine start point characteristic")

        start_point_modifier = StartPointModifier(start_point_characteristic)
        for image_id, image_graph in image_graphs.items():
            self.logger.info(f"Determining start point for image {image_id}")
            start_point = start_point_picker.get_start_point_for_graph(image_graph)
            if start_point is not None:
                self.logger.info(f"Start point for image {image_id}: {start_point}")
                image_graph = start_point_modifier.change_start_point(
                    image_graph, start_point
                )
                image_graphs[image_id] = image_graph
            else:
                self.logger.info(f"No start point found for image {image_id}")
                raise ValueError(f"No start point found for image {image_id}")
        return image_graphs

    @timed(label="analyze_graph")
    def _analyze_graph(self, graph: nx.Graph) -> nx.Graph:
        visitors = [
            AngleVisitor(graph),
            QuadrantVisitor(graph),
            DirectionVisitor(graph),
        ]
        analyzer = GraphAnalyzer(graph, visitors)
        analyzer.analyze()
        return graph
