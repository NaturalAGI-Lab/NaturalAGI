import logging
from typing import List, Dict

import networkx as nx

from concept_minor_classifier import ConceptMinorClassifier
from repository.image_repository import ImageRepository
from models import ClassificationResult
from services.graph_complexity_service import GraphComplexityService

logging.basicConfig(level=logging.DEBUG)


class ClassificationOrchestrator:

    def __init__(
        self,
        neo4j_dsn: str,
        neo4j_user: str,
        neo4j_pass: str,
        ged_timeout: float = 15,
    ):
        self.neo4j_dsn = neo4j_dsn
        self.neo4j_user = neo4j_user
        self.neo4j_pass = neo4j_pass
        self.ged_timeout = ged_timeout
        self.graph_complexity_service = GraphComplexityService()

    def classify_image(
        self,
        image_id: str,
        concept_graphs: Dict[str, nx.Graph],
    ) -> List[ClassificationResult]:
        logging.info(f"Starting classification for image {image_id}")

        image_repository = ImageRepository(
            self.neo4j_dsn, self.neo4j_user, self.neo4j_pass
        )

        try:
            image_graph = image_repository.get_image_graph(image_id)
            results = self._classify_sequentially(image_graph, concept_graphs)
            return self._process_and_sort_results(results, image_id)
        finally:
            image_repository.close()

    def _classify_sequentially(
        self,
        image_graph: nx.Graph,
        concept_graphs: Dict[str, nx.Graph],
    ) -> List[ClassificationResult]:
        image_complexity = self.graph_complexity_service.get_default_graph_complexity(
            image_graph
        )

        eligible = {
            cid: g
            for cid, g in concept_graphs.items()
            if self.graph_complexity_service.get_default_graph_complexity(g)
            <= image_complexity
        }

        logging.info(
            f"Complexity filter: {len(eligible)}/{len(concept_graphs)} concepts eligible "
            f"(image_complexity={image_complexity})"
        )

        classifier = ConceptMinorClassifier(ged_timeout=self.ged_timeout)
        results = []

        for concept_id, concept_graph in eligible.items():
            try:
                result = classifier.check_single_concept(
                    image_graph, concept_id, concept_graph
                )
                results.append(result)
            except Exception as e:
                logging.error(
                    f"Error processing concept {concept_id}: {str(e)}",
                    exc_info=True,
                )
                results.append(
                    ClassificationResult(
                        concept_id=concept_id,
                        is_minor=False,
                        message=f"Processing error: {str(e)}",
                    )
                )

        logging.info(f"Classification completed. Processed {len(results)} concepts")
        return results

    def _process_and_sort_results(
        self, results: List[ClassificationResult], image_id: str
    ) -> List[ClassificationResult]:
        if not results:
            logging.warning(f"No classification results for image {image_id}")
            return []

        filtered_results = [result for result in results if result.is_minor]
        if not filtered_results:
            return []

        filtered_results.sort(
            key=lambda x: (x.similarity or 0),
            reverse=True,
        )

        logging.info(
            f"Found {len(filtered_results)} matching concepts out of {len(results)} processed"
        )
        return filtered_results
