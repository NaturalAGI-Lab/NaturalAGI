import logging
import networkx as nx
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from property_handlers import PropertyMatcherManager
from services.pre_processing.critical_point_preprocessor import (
    CriticalPointPreprocessor,
)
from repository.concept_repository import ConceptRepository
from repository.image_repository import ImageRepository
from models import ClassificationResult
from services.pre_processing.complexity_preprocessor import ComplexityPreprocessor
from services.pre_processing.start_point_preprocessor import StartPointPreprocessor
from reduction_strategy.endpoint_strategy import EndpointReductionStrategy
from reduction_strategy.intersection_strategy import IntersectionPointReductionStrategy
from reduction_strategy.corner_point_reduction_strategy import (
    CornerPointReductionStrategy,
)
from node_similarity_calculator import NodeSimilarityCalculator

logging.basicConfig(level=logging.DEBUG)


class ConceptMinorClassifier:
    """
    Specialized classifier that checks if a concept is a minor of an image graph
    without removing properties from concept nodes during matching.

    This classifier starts from StartPoint nodes and tries to find the graph minor
    for the image. If the image can be presented as a concept graph without removing
    properties from the nodes of the concept, it's considered a minor and a match.
    """

    def __init__(
        self,
        concept_repository: ConceptRepository,
        image_repository: ImageRepository,
        max_workers: int = 4,
        use_multithreading: bool = False,
        complexity_preprocessor: ComplexityPreprocessor = ComplexityPreprocessor(),
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
        property_matcher: PropertyMatcherManager = PropertyMatcherManager(),
        start_point_preprocessor: StartPointPreprocessor = StartPointPreprocessor(),    
    ):
        self.max_workers = max_workers
        self.use_multithreading = use_multithreading
        self.property_matcher = property_matcher
        self.critical_point_preprocessor = critical_point_preprocessor
        self.complexity_preprocessor = complexity_preprocessor
        self.concept_repository = concept_repository
        self.image_repository = image_repository
        self.start_point_preprocessor = start_point_preprocessor
    def classify(
        self,
        image_id: str,
    ) -> List[ClassificationResult]:
        logging.info(f"Classifying image {image_id} using concept minor approach")
        concept_ids = self.concept_repository.get_all_concept_ids()
        image_graph = self.image_repository.get_image_graph(image_id)

        results = []

        if self.use_multithreading:
            results = self._classify_with_multithreading(image_graph, concept_ids)
        else:
            results = self._classify_sequentially(image_graph, concept_ids)

        # Process and sort results
        return self._process_and_sort_results(results, image_id)

    def _classify_with_multithreading(
        self,
        image_graph: nx.Graph,
        concepts: List[str],
    ) -> List[Dict[str, Any]]:
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._check_single_concept,
                    image_graph,
                    concept_id,
                ): concept_id
                for concept_id in concepts
            }

            for future in futures:
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    logging.error(f"Error checking concept minor: {str(e)}")

        return results

    def _classify_sequentially(
        self,
        image_graph: nx.Graph,
        concepts: List[str],
    ) -> List[Dict[str, Any]]:
        results = []
        for concept in concepts:
            try:
                result = self._check_single_concept(
                    image_graph,
                    concept,
                )
                results.append(result)
            except Exception as e:
                logging.error(f"Error checking concept minor: {str(e)}")

        return results

    def _check_single_concept(
        self,
        image_graph: nx.Graph,
        concept_id: str,
    ) -> ClassificationResult:
        logging.info(f"Checking concept {concept_id} for minor of image")
        # Get concept graph
        concept_graph = self.concept_repository.get_concept_graph(concept_id)

        if self.complexity_preprocessor.is_concept_more_complex(
            concept_graph, image_graph
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
                image_graph, concept_graph
            )
            self.critical_point_preprocessor.preprocess_graphs(
                image_graph, concept_graph
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

        return ClassificationResult(
            concept_id=concept_id,
            is_minor=True,
            message="Concept is a minor of the image",
        )

    def _process_and_sort_results(
        self, results: List[ClassificationResult], image_id: str
    ) -> List[ClassificationResult]:
        if not results:
            return []

        filtered_results = []
        for result in results:
            if result.is_minor:
                filtered_results.append(result)

        return filtered_results
