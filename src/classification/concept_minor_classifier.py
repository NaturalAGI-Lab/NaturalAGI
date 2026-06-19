from __future__ import annotations
import logging
import copy
import networkx as nx
from services.pre_processing.critical_point_preprocessor import (
    CriticalPointPreprocessor,
)
from models import ClassificationResult
from services.pre_processing.start_point_preprocessor import StartPointPreprocessor
from services.graph_complexity_service import GraphComplexityService
from reduction_strategy.endpoint_strategy import EndpointReductionStrategy
from reduction_strategy.intersection_strategy import IntersectionPointReductionStrategy
from reduction_strategy.corner_point_reduction_strategy import (
    CornerPointReductionStrategy,
)
from node_similarity_calculator import NodeSimilarityCalculator
from graph_similarity.comparator_protocol import GraphComparator
from graph_similarity.ged_comparator import GEDComparator
from common.decorator import timed
from services.graph_analyzer import GraphAnalyzer
from common.traversal.visitors import AngleVisitor, QuadrantVisitor, DirectionVisitor

logging.basicConfig(level=logging.DEBUG)


class ConceptMinorClassifier:

    def __init__(
        self,
        ged_timeout: float = 15,
        comparator: GraphComparator | None = None,
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
        self.comparator = comparator if comparator is not None else GEDComparator(timeout=ged_timeout)
        self.critical_point_preprocessor = critical_point_preprocessor
        self.graph_complexity_service = GraphComplexityService()
        self.start_point_preprocessor = start_point_preprocessor

    def preprocess_pair(self, image_graph: nx.Graph, concept_graph: nx.Graph):
        image_graph = copy.deepcopy(image_graph)
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
        return self.critical_point_preprocessor.preprocess_graphs(
            inference_graph=image_graph,
            concept_graph=concept_graph,
        )

    @timed(label="check_single_concept")
    def check_single_concept(
        self,
        image_graph: nx.Graph,
        concept_id: str,
        concept_graph: nx.Graph,
    ) -> ClassificationResult:
        image_graph = copy.deepcopy(image_graph)
        logging.info(f"Checking concept {concept_id} for minor of image")

        try:
            logging.info("Preprocessing image graph")
            preprocessed_image_graph, preprocessed_concept_graph = self.preprocess_pair(
                image_graph, concept_graph
            )
            similarity = self.comparator.compare(
                image_graph=preprocessed_image_graph,
                concept_graph=preprocessed_concept_graph,
                concept_name=concept_id,
            )

            concept_complexity = self.graph_complexity_service.get_default_graph_complexity(
                concept_graph
            )
            image_complexity = self.graph_complexity_service.get_default_graph_complexity(
                image_graph
            )

            coverage = min(concept_complexity / max(image_complexity, 1), 1.0)
            adjusted_similarity = round(similarity, 4)

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
