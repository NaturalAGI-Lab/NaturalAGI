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
# Reference: Grünwald (2007) MDL Ch 17; Cilibrasi-Vitányi (2005) NCD.
# Winner of exp_050..exp_053 bench — see researches/ged_size_bias_four_methods_findings.md.
# lambda=0.10 (raised from 0.02) is the validated full-set optimum: exact offline sweep nets
# +31 at 25%, live full run 86.21%→86.70% (lifts class-2 recall, suppresses small-concept
# over-fire); plateau 0.10–0.12. See researches/complexity_preference_rule_findings.md (Phase 2/3).
COMPLEXITY_PRIOR_LAMBDA = 0.10

# Image-relative coverage penalty (per-message tunable). adjusted_sim = sim * coverage^alpha,
# coverage = min(concept_complexity / image_complexity, 1.0). alpha=0 disables (baseline).
# Penalizes a small concept matching a large image (the small-concept over-fire) without
# penalizing the same concept on a same-size image.
COVERAGE_ALPHA = 0.0

# A concept is compared only if it is not more complex than the image (a minor cannot be larger than its host).
# ELIGIBILITY_SLACK > 0 admits attractors up to (1 + slack) x the image complexity — with a finite insertion cost an
# incomplete input can still match most of a larger attractor (ISL Def. 1: 1 / tau). 0 = the original filter.
ELIGIBILITY_SLACK = 0.0

logging.basicConfig(level=logging.DEBUG)


def _concept_calibration(concept_graph: nx.Graph):
    """(mu, sd) of a concept's background score distribution, or None."""
    for _, attrs in concept_graph.nodes(data=True):
        if "calib_mu" in attrs:
            try:
                return (
                    float(attrs["calib_mu"]),
                    max(float(attrs.get("calib_sd", 1.0)), 1e-3),
                )
            except (TypeError, ValueError):
                return None
    return None


def complexity_adjusted_score(result: ClassificationResult) -> float:
    """Ranking score = similarity (× optional coverage penalty) + log-complexity prior.

    Reads the module-level COMPLEXITY_PRIOR_LAMBDA / COVERAGE_ALPHA at call time, so
    `_cost_config_override` and debug tools see the same value production ranks with.
    """
    base = result.similarity or 0.0
    c = max(result.concept_complexity or 1, 1)
    if COVERAGE_ALPHA > 0.0 and (result.image_complexity or 0) > 0:
        coverage = min(c / result.image_complexity, 1.0)
        base = base * (coverage ** COVERAGE_ALPHA)
    return base + COMPLEXITY_PRIOR_LAMBDA * math.log2(c)


def _build_comparator(
    method: str, ged_timeout: float, fgw_alpha: float
) -> GraphComparator:
    if method == "fgw":
        from graph_similarity.fgw_comparator import FGWComparator
        return FGWComparator(alpha=fgw_alpha)
    if method == "mcs":
        from graph_similarity.mcs_comparator import MCSComparator
        return MCSComparator()
    if method == "mcs_loose":
        from graph_similarity.mcs_comparator import MCSComparator
        return MCSComparator(compat_cost=3.0)
    if method == "mcs_concept":
        from graph_similarity.mcs_comparator import MCSComparator
        return MCSComparator(norm="concept")
    if method == "hungarian":
        from graph_similarity.hungarian_comparator import HungarianComparator
        return HungarianComparator(timeout=ged_timeout)
    if method in ("direct_bridge", "db"):
        from graph_similarity.direct_bridge_comparator import DirectBridgeComparator
        return DirectBridgeComparator(timeout=ged_timeout)
    return GEDComparator(timeout=ged_timeout)


class ClassificationOrchestrator:

    def __init__(
        self,
        driver,
        ged_timeout: float = 15,
        comparison_method: str = "ged",
        fgw_alpha: float = 0.5,
        preprocess_fallback: bool = False,
        tracer: Optional[otel_trace.Tracer] = None,
        calibration: str = "off",
        band_mode: str = "off",
        band_model=None,
        band_model_name: Optional[str] = None,
        band_topk: int = 3,
        explainer_graphs: Optional[Dict[str, nx.Graph]] = None,
    ):
        self.driver = driver
        # Band mode: band concepts make the decision ('decide') or shortlist the letters the
        # structural comparator then ranks ('shortlist'). 'off' (default) leaves the structural
        # path below exactly as it was.
        self.band_mode = band_mode
        self.band_model = band_model
        self.band_model_name = band_model_name
        self.band_topk = band_topk
        self.explainer_graphs = explainer_graphs or {}
        self.ged_timeout = ged_timeout
        # Per-concept score calibration of the structural path. Concepts of different size /
        # shape produce similarities on different scales, so "max over concepts" is dominated by
        # the most permissive ones — harmless with one concept per class, fatal with several.
        # 'zbg' re-ranks by (score - mu) / sd, mu / sd = that concept's score distribution over
        # OTHER classes' images, stored on the concept's nodes as calib_mu / calib_sd
        # (notes/scripts_pipeline/pl_calib.py).
        self.calibration = calibration
        self._calib: Dict[str, tuple] = {}
        self.comparator = _build_comparator(comparison_method, ged_timeout, fgw_alpha)
        self.graph_complexity_service = GraphComplexityService()
        self.preprocess_fallback = preprocess_fallback
        self._tracer = tracer

    def classify_image(
        self,
        image_id: str,
        concept_graphs: Dict[str, nx.Graph],
    ) -> List[ClassificationResult]:
        logging.info(f"Starting classification for image {image_id}")

        if self.band_mode != "off":
            ranked = self._rank_letters_by_bands(image_id)
            if self.band_mode == "decide":
                return self._band_results(ranked, image_id)
            keep = {ls.letter for ls in ranked[: max(self.band_topk, 1)]}
            concept_graphs = {
                cid: g for cid, g in concept_graphs.items() if cid.split("_")[0] in keep
            }

        image_repository = ImageRepository(self.driver)
        image_graph = image_repository.get_image_graph(image_id)
        results = self._classify_sequentially(image_graph, concept_graphs)
        return self._process_and_sort_results(results, image_id)

    def _rank_letters_by_bands(self, image_id: str):
        from band.band_repository import get_image_feature_set, get_image_shape
        from band.band_scorer import score_letters_committee
        from band.shape_context import rerank

        if self.band_model is None:
            raise ValueError(
                f"band_mode={self.band_mode}: band model '{self.band_model_name}' is not loaded"
            )
        xs = get_image_feature_set(self.driver, image_id, self.band_model.dm_version)
        if not xs:
            raise ValueError(
                f"No direction map ({self.band_model.dm_version}) for image {image_id}: "
                "the request must carry band_mode (or direction_map) so contour analysis writes it"
            )
        self._band_vector = xs[0]
        # round 1: band concepts (leaf + root) of all letters, averaged over the skeleton committee
        ranked = score_letters_committee(xs, self.band_model)
        # round 2: the best letters re-ranked against the leaves' shape concepts
        if self.band_model.stage2_lambda > 0:
            points, tangents = get_image_shape(self.driver, image_id)
            ranked = rerank(self.band_model, ranked, points, tangents)
        return ranked

    def _band_results(self, ranked, image_id: str) -> List[ClassificationResult]:
        """One result per letter, best first. `similarity` stays in (0, 1] and decreases with the
        rank, so the (is_minor, similarity) order that the evaluation code relies on is the band order. The top `band_topk` letters carry an
        explanation; the structural comparator is used for that only, never for the decision."""
        explanations = {}
        if self.band_topk > 0:
            from band.band_explainer import explain
            from graph_similarity.mcs_comparator import MCSComparator

            image_graph, classifier = None, None
            if self.explainer_graphs:
                try:
                    image_graph = ImageRepository(self.driver).get_image_graph(image_id)
                    classifier = ConceptMinorClassifier(
                        comparator=MCSComparator(compat_cost=3.0), preprocess_fallback=True
                    )
                except Exception as e:  # noqa: BLE001
                    logging.info(f"Band explainer: image graph unavailable: {e}")
            for ls in ranked[: self.band_topk]:
                explanations[ls.leaf_id] = explain(
                    self._band_vector, self.band_model, ls.leaf_id, image_graph,
                    self.explainer_graphs, classifier,
                )
        sims, prev = [], 1.0
        for ls in ranked:                       # a re-ranking stage may reorder letters: keep it monotone
            prev = min(prev - 1e-6, 1.0 / (1.0 + ls.score)); sims.append(max(prev, 1e-9))
        results = [
            ClassificationResult(
                concept_id=ls.leaf_id,
                is_minor=True,
                message=f"band:{ls.form}",
                similarity=round(sims[rank], 6),
                band_score=round(float(ls.score), 6),
                band_rank=rank,
                explanation=explanations.get(ls.leaf_id),
            )
            for rank, ls in enumerate(ranked)
        ]
        return results

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
            <= image_complexity * (1.0 + ELIGIBILITY_SLACK)
        }

        logging.info(
            f"Complexity filter: {len(eligible)}/{len(concept_graphs)} concepts eligible "
            f"(image_complexity={image_complexity})"
        )

        if self.calibration != "off":
            self._calib = {}
            for cid, g in eligible.items():
                stats = _concept_calibration(g)
                if stats:
                    self._calib[cid] = stats
            logging.info(
                f"Calibration '{self.calibration}': stats for "
                f"{len(self._calib)}/{len(eligible)} concepts"
            )

        classifier = ConceptMinorClassifier(
            comparator=self.comparator,
            preprocess_fallback=self.preprocess_fallback,
        )
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

        if self.calibration != "off" and self._calib:
            def _calibrated(x):
                base = complexity_adjusted_score(x)
                stats = self._calib.get(x.concept_id)
                return (base - stats[0]) / stats[1] if stats else base

            results.sort(key=lambda x: (x.is_minor, _calibrated(x)), reverse=True)
        else:
            results.sort(
                key=lambda x: (x.is_minor, complexity_adjusted_score(x)),
                reverse=True,
            )

        matching = sum(1 for r in results if r.is_minor)
        if results:
            top = results[0]
            logging.info(
                f"Top concept={top.concept_id}, sim={top.similarity}, "
                f"concept_complexity={top.concept_complexity}, "
                f"adjusted_score={complexity_adjusted_score(top):.4f}"
            )
        logging.info(
            f"Found {matching} matching concepts out of {len(results)} processed"
        )
        return results
