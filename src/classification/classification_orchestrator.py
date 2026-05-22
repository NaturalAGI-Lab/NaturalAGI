import logging
import math
from typing import List, Dict, Optional

import networkx as nx
from opentelemetry import trace as otel_trace

from concept_minor_classifier import ConceptMinorClassifier
from repository.image_repository import ImageRepository
from models import ClassificationResult
from services.graph_complexity_service import GraphComplexityService
from graph_similarity.comparator_protocol import GraphComparator
from graph_similarity.ged_comparator import GEDComparator

# === Bayesian log-complexity specificity prior (Method 3 winner, +3.96pp at 25% QUICK) ===
# score = sim + COMPLEXITY_PRIOR_LAMBDA * log2(concept_complexity)
# Formalizes "при прочих равних, complex concept wins" as a Bayesian prior:
# P(concept | match) ∝ P(match | concept) * P(concept). Smaller concepts have higher
# P(match | random graph), so their observed similarity is less informative. The log2
# term is the number of bits needed to specify a graph of that complexity (MDL prior).
# Empirically, lambda=0.02 gives increments of ~0.046–0.092 over c=5..24, matching
# the observed tiebreaker margin of 0.01–0.05 from the top1-issue analysis.
# Reference: Grünwald (2007) MDL Ch 17; Cilibrasi-Vitányi (2005) NCD.
# Winner of exp_050..exp_053 bench — see researches/ged_size_bias_four_methods_findings.md.
COMPLEXITY_PRIOR_LAMBDA = 0.02

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
        driver,
        ged_timeout: float = 15,
        comparison_method: str = "ged",
        fgw_alpha: float = 0.5,
        tracer: Optional[otel_trace.Tracer] = None,
    ):
        self.driver = driver
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

        image_repository = ImageRepository(self.driver)
        image_graph = image_repository.get_image_graph(image_id)
        results = self._classify_sequentially(image_graph, concept_graphs)
        return self._process_and_sort_results(results, image_id)

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

        def _complexity_adjusted_score(r: ClassificationResult) -> float:
            base = r.similarity or 0.0
            c = max(r.concept_complexity or 1, 1)
            return base + COMPLEXITY_PRIOR_LAMBDA * math.log2(c)

        results.sort(
            key=lambda x: (x.is_minor, _complexity_adjusted_score(x)),
            reverse=True,
        )

        matching = sum(1 for r in results if r.is_minor)
        if results:
            top = results[0]
            logging.info(
                f"Top concept={top.concept_id}, sim={top.similarity}, "
                f"concept_complexity={top.concept_complexity}, "
                f"adjusted_score={_complexity_adjusted_score(top):.4f}"
            )
        logging.info(
            f"Found {matching} matching concepts out of {len(results)} processed"
        )
        return results
