import logging
from typing import List, Dict, Optional

import networkx as nx
from opentelemetry import trace as otel_trace

from concept_minor_classifier import ConceptMinorClassifier
from repository.image_repository import ImageRepository
from models import ClassificationResult
from services.graph_complexity_service import GraphComplexityService
from graph_similarity.comparator_protocol import GraphComparator
from graph_similarity.ged_comparator import GEDComparator

logging.basicConfig(level=logging.DEBUG)


def _build_comparator(
    method: str, ged_timeout: float, fgw_alpha: float
) -> GraphComparator:
    if method == "fgw":
        from graph_similarity.fgw_comparator import FGWComparator
        return FGWComparator(alpha=fgw_alpha)
    return GEDComparator(timeout=ged_timeout)


class ClassificationOrchestrator:

    def __init__(
        self,
        neo4j_dsn: str,
        neo4j_user: str,
        neo4j_pass: str,
        ged_timeout: float = 15,
        comparison_method: str = "ged",
        fgw_alpha: float = 0.5,
        tracer: Optional[otel_trace.Tracer] = None,
    ):
        self.neo4j_dsn = neo4j_dsn
        self.neo4j_user = neo4j_user
        self.neo4j_pass = neo4j_pass
        self.ged_timeout = ged_timeout
        self.comparator = _build_comparator(comparison_method, ged_timeout, fgw_alpha)
        self.graph_complexity_service = GraphComplexityService()
        self._tracer = tracer

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

        classifier = ConceptMinorClassifier(comparator=self.comparator)
        results = []

        for concept_id, concept_graph in eligible.items():
            try:
                if self._tracer:
                    with self._tracer.start_as_current_span("ged.compare") as span:
                        span.set_attribute("concept_id", concept_id)
                        concept_complexity = self.graph_complexity_service.get_default_graph_complexity(
                            concept_graph
                        )
                        span.set_attribute("concept_complexity", concept_complexity)
                        result = classifier.check_single_concept(
                            image_graph, concept_id, concept_graph
                        )
                        span.set_attribute("similarity", result.similarity or 0)
                        span.set_attribute("is_minor", result.is_minor)
                        results.append(result)
                else:
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

        results.sort(
            key=lambda x: (x.is_minor, x.similarity or 0),
            reverse=True,
        )

        matching = sum(1 for r in results if r.is_minor)
        logging.info(
            f"Found {matching} matching concepts out of {len(results)} processed"
        )
        return results
