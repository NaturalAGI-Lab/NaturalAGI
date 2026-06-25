import math

import classification_orchestrator as orch
from models import ClassificationResult


def _r(cid, sim, cx, is_minor=True, image_cx=9):
    return ClassificationResult(concept_id=cid, is_minor=is_minor, message="",
                                similarity=sim, concept_complexity=cx,
                                image_complexity=image_cx)


def test_complexity_adjusted_score_formula():
    # base + lambda * log2(complexity); coverage off by default (alpha=0)
    r = _r("1_3", 0.50, 4)
    expected = 0.50 + orch.COMPLEXITY_PRIOR_LAMBDA * math.log2(4)
    assert orch.complexity_adjusted_score(r) == expected


def test_prior_flips_raw_similarity_winner():
    # Reproduces mnist_test_1_00225: 1_3 wins RAW similarity but the complexity
    # prior lifts the larger 7_1 above it, so the predicted label is 7.
    one = _r("1_3", 0.4617, 5)
    seven = _r("7_1", 0.3882, 9)
    assert one.similarity > seven.similarity                       # raw: 1_3 ahead
    ranked = orch.ClassificationOrchestrator._process_and_sort_results(
        orch.ClassificationOrchestrator.__new__(orch.ClassificationOrchestrator),
        [one, seven], "img-00225")
    assert ranked[0].concept_id == "7_1"                           # adjusted: 7_1 wins
