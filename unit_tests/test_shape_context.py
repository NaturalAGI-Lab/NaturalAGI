import numpy as np
import pytest


@pytest.fixture(scope="module")
def sc():
    import sys
    from pathlib import Path
    path = str(Path(__file__).resolve().parent.parent / "src" / "classification")
    if path not in sys.path:
        sys.path.insert(0, path)
    import band.shape_context as module
    import band.band_model as bm
    import band.band_scorer as scorer
    return module, bm, scorer


def _line(n=32, vertical=True):
    t = np.linspace(0, 1, n, dtype=np.float32)
    pts = np.stack([np.full(n, 0.5, np.float32), t], 1) if vertical else np.stack([t, np.full(n, 0.5, np.float32)], 1)
    tan = np.tile(np.array([[-1.0, 0.0]] if vertical else [[1.0, 0.0]], np.float32), (n, 1))     # doubled angle
    return pts, tan


def test_histograms_are_normalised_and_identical_shapes_cost_nothing(sc):
    module, _, _ = sc
    p, t = _line()
    h = module.shape_context(p)
    assert h.shape == (32, 60) and np.allclose(h.sum(1), 1.0, atol=1e-5)
    d = module.distances(h, p, t, h[None], p[None], t[None], beta=0.3)
    assert d.shape == (1,) and d[0] == pytest.approx(0.0, abs=1e-6)


def test_rerank_prefers_the_letter_whose_shape_concept_matches(sc):
    module, bm, scorer = sc
    pv, tv = _line(vertical=True); ph, th = _line(vertical=False)
    D = 4
    lo = np.array([[0.4] * D, [0.4] * D, [0.5] * D, [0.5] * D]); hi = lo + 0.2
    model = bm.BandModel("m", "dm3", [f"d{i}" for i in range(D)], np.ones(D), np.ones(D),
                         ["A_leaf", "A_root", "B_leaf", "B_root"], ["A", "A", "B", "B"], ["*"] * 4,
                         ["leaf", "root", "leaf", "root"], lo, hi, lo + 0.1, alpha=1.0, leaf_weight=0.5, root_weight=0.5,
                         shape_points=[ph[None], None, pv[None], None], shape_tangents=[th[None], None, tv[None], None],
                         stage2_lambda=5.0, stage2_topk=2, stage2_beta=0.3)
    model.shape_contexts = [None if sp is None else np.stack([module.shape_context(x) for x in sp]) for sp in model.shape_points]
    ranked = scorer.score_letters(np.full(D, 0.5), model)
    assert ranked[0].letter == "A"                                  # bands slightly prefer A
    assert module.rerank(model, ranked, pv, tv)[0].letter == "B"    # the image is a vertical stroke, like B's shape concept
    model.stage2_lambda = 0.0
    assert module.rerank(model, ranked, pv, tv)[0].letter == "A"    # off => untouched
    assert module.rerank(model, ranked, None, None)[0].letter == "A"


def test_builder_and_classifier_agree_on_the_shape_context(sc):
    """concept_creator carries its own copy of shape_context (separate Nuclio function); the copies must not drift."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "src" / "concept_creator" / "src" / "band_concepts" / "shape_concept.py"
    spec = importlib.util.spec_from_file_location("shape_concept", path)
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    module, _, _ = sc
    pts = np.random.default_rng(0).random((32, 2)).astype(np.float32)
    np.testing.assert_allclose(builder.shape_context(pts), module.shape_context(pts), atol=1e-6)


def test_leaf_prototype_averages_matched_points(sc):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "src" / "concept_creator" / "src" / "band_concepts" / "shape_concept.py"
    spec = importlib.util.spec_from_file_location("shape_concept", path)
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    rng = np.random.default_rng(1)
    p0, t0 = _line(vertical=True)
    augs = [np.clip(p0 + rng.normal(0, 0.01, p0.shape), 0, 1).astype(np.float32)[rng.permutation(32)] for _ in range(5)]
    mu, tol, hist, tan = builder.leaf_prototype([p0] + augs, [t0] * 6)
    assert mu.shape == (32, 2) and tol.shape == (32,) and hist.shape == (32, 60) and tan.shape == (32, 2)
    assert np.abs(mu - p0).max() < 0.06 and tol.max() < 0.08          # shuffled, jittered copies land on (or next to) their anchors
    assert np.allclose(hist.sum(1), 1.0, atol=1e-4)
