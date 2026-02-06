import logging
import copy
import math
import networkx as nx
from services.pre_processing.critical_point_preprocessor import (
    CriticalPointPreprocessor,
)
from repository.concept_repository import ConceptRepository
from repository.image_repository import ImageRepository
from models import ClassificationResult
from services.pre_processing.complexity_preprocessor import ComplexityPreprocessor
from services.pre_processing.start_point_preprocessor import StartPointPreprocessor
from services.graph_complexity_service import GraphComplexityService
from reduction_strategy.endpoint_strategy import EndpointReductionStrategy
from reduction_strategy.intersection_strategy import IntersectionPointReductionStrategy
from reduction_strategy.corner_point_reduction_strategy import (
    CornerPointReductionStrategy,
)
from node_similarity_calculator import NodeSimilarityCalculator
from graph_similarity.graph_edit_distance_comparator import (
    GraphEditDistanceComparator,
)
from common.decorator import timed
from services.graph_analyzer import GraphAnalyzer
from common.traversal.visitors import AngleVisitor, QuadrantVisitor, DirectionVisitor

logging.basicConfig(level=logging.DEBUG)


class ConceptMinorClassifier:
    """
    Specialized classifier that checks if a concept is a minor of an image graph
    without removing properties from concept nodes during matching.

    This classifier focuses on the core classification logic while the orchestrator
    handles multiprocessing concerns.
    """

    def __init__(
        self,
        concept_repository: ConceptRepository,
        image_repository: ImageRepository,
        ged_timeout: float = 15,
        graph_complexity_service: GraphComplexityService = None,
        complexity_preprocessor: ComplexityPreprocessor = None,
        critical_point_preprocessor: CriticalPointPreprocessor = CriticalPointPreprocessor(
            endpoint_reduction_strategy=EndpointReductionStrategy(
                node_similarity_calculator=NodeSimilarityCalculator()
            ),
            intersection_reduction_strategy=IntersectionPointReductionStrategy(
                node_similarity_calculator=NodeSimilarityCalculator()
            ),
            corner_point_reduction_strategy=CornerPointReductionStrategy(
                node_similarity_calculator=NodeSimilarityCalculator()
            ),
        ),
        start_point_preprocessor: StartPointPreprocessor = StartPointPreprocessor(),
    ):
        self.critical_point_preprocessor = critical_point_preprocessor

        if graph_complexity_service is None:
            self.graph_complexity_service = GraphComplexityService()

        if complexity_preprocessor is None:
            self.complexity_preprocessor = ComplexityPreprocessor(
                graph_complexity_service=self.graph_complexity_service,
            )

        self.concept_repository = concept_repository
        self.image_repository = image_repository
        self.start_point_preprocessor = start_point_preprocessor
        self.ged_timeout = ged_timeout

    @timed(label="check_single_concept")
    def check_single_concept(
        self,
        image_graph: nx.Graph,
        concept_id: str,
    ) -> ClassificationResult:
        """
        Check if a single concept is a minor of the given image graph.

        Args:
            image_graph: The image graph to check against
            concept_id: ID of the concept to check

        Returns:
            Classification result for this concept
        """
        image_graph = copy.deepcopy(image_graph)
        logging.info(f"Checking concept {concept_id} for minor of image")
        concept_graph = self.concept_repository.get_concept_graph(concept_id)

        if self.complexity_preprocessor.is_concept_more_complex(
            concept_graph=concept_graph,
            image_graph=image_graph,
        ):
            logging.info(
                f"Concept {concept_id} is too complex to be a minor of the image"
            )
            return ClassificationResult(
                concept_id=concept_id,
                is_minor=False,
                message=f"Concept {concept_id} is too complex to be a minor of the image",
            )

        try:
            logging.info("Preprocessing image graph")
            image_graph = self.start_point_preprocessor.preprocess(
                inference_graph=image_graph,
                concept_graph=concept_graph,
            )
            GraphAnalyzer(
                graph=image_graph,
                visitors=[
                    AngleVisitor(image_graph),
                    QuadrantVisitor(image_graph),
                    DirectionVisitor(image_graph),
                ],
            ).analyze()
            preprocessed_image_graph, preprocessed_concept_graph = (
                self.critical_point_preprocessor.preprocess_graphs(
                    inference_graph=image_graph,
                    concept_graph=concept_graph,
                )
            )
            similarity = GraphEditDistanceComparator.compare_graphs_ged(
                image_graph=preprocessed_image_graph,
                concept_graph=preprocessed_concept_graph,
                concept_name=concept_id,
                ged_timeout=self.ged_timeout,
            )

            concept_complexity = self.graph_complexity_service.get_default_graph_complexity(
                concept_graph
            )
            image_complexity = self.graph_complexity_service.get_default_graph_complexity(
                image_graph
            )

            # Weight similarity by concept coverage: how much of the image's
            # structure the concept explains. Simpler concepts that match a small
            # substructure of a complex image get penalized.
            coverage = min(concept_complexity / max(image_complexity, 1), 1.0)
            adjusted_similarity = round(similarity * math.sqrt(coverage), 2)

            logging.info(
                f"Similarity between image and concept {concept_id}: {adjusted_similarity} "
                f"(raw_ged_similarity={similarity}, coverage={coverage:.2f})"
            )
            return ClassificationResult(
                concept_id=concept_id,
                is_minor=True,
                message=f"Similarity between image and concept {concept_id}: {adjusted_similarity}",
                similarity=adjusted_similarity,
                concept_complexity=concept_complexity,
                image_complexity=image_complexity,
            )
        except Exception as e:
            logging.warning(
                f"Preprocessing failed for concept {concept_id}: {str(e)}",
                exc_info=True,
            )
            return ClassificationResult(
                concept_id=concept_id,
                is_minor=False,
                message=f"Preprocessing failed: {str(e)}",
            )
