"""Compliant ComAN (lab log M): majority intervals in the concept creator, offline re-scoring, the ISL profile."""
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROFILE_DIR = REPO / "notes" / "scripts_isl" / "coman_cfg"


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ph():
    return _load("property_handlers_m", "src/concept_creator/src/property_handlers/property_handlers.py")


@pytest.fixture(scope="module")
def rerank():
    return _load("coman_rerank", "notes/scripts_isl/coman_rerank.py")


def test_default_merge_is_unchanged(ph, monkeypatch):
    monkeypatch.delenv("CONCEPT_INTERVAL_MODE", raising=False)
    assert ph.merge_values(1.0, 3.0) == {"min": 1.0, "max": 3.0, "center": 2.0, "type": "range"}
    r = ph.merge_values({"min": 1.0, "max": 3.0, "center": 2.0, "type": "range"}, 7.0)
    assert (r["min"], r["max"]) == (1.0, 7.0) and "samples" not in r


def test_majority_interval_drops_the_outlier(ph, monkeypatch):
    monkeypatch.setenv("CONCEPT_INTERVAL_MODE", "majority")
    monkeypatch.setenv("CONCEPT_INTERVAL_TAU", "0.8")
    r = ph.merge_values(0.0, 1.0)
    for v in (2.0, 3.0, 100.0):                 # the concept keeps its samples from merge to merge
        r = ph.merge_values(r, v)
    assert r["samples"] == [0.0, 1.0, 2.0, 3.0, 100.0]
    assert (r["min"], r["max"]) == (0.0, 3.0)    # 4 of 5 values (>= 0.8) in the shortest interval
    assert r["center"] == 2.0                    # median, not the mean pulled by the outlier
    assert ph.is_range(r)


def test_majority_tau_one_is_min_max(ph, monkeypatch):
    monkeypatch.setenv("CONCEPT_INTERVAL_MODE", "majority")
    monkeypatch.setenv("CONCEPT_INTERVAL_TAU", "1.0")
    r = ph.merge_values(ph.merge_values(5.0, -1.0), 2.0)
    assert (r["min"], r["max"], r["center"]) == (-1.0, 5.0, 2.0)


def _row(path, true, ranked):
    return {"path": path, "true": true, "ranked": [dict(c=c, cid=cid, sim=s, cc=cc, minor=True) for c, cid, s, cc in ranked]}


def test_max_over_filters_and_lambda(rerank):
    a = {"x": _row("x", "7", [("1", "1_1", 0.80, 3), ("7", "7_1", 0.70, 9)])}
    b = {"x": _row("x", "7", [("7", "7_1", 0.78, 9), ("1", "1_1", 0.60, 3)])}
    assert rerank.predictions([a], 0.0)["x"][1][0] == "1"
    assert rerank.predictions([a, b], 0.0)["x"][1][0] == "1"        # MAX per concept: 0.80 vs 0.78
    assert rerank.predictions([a, b], 0.1)["x"][1][0] == "7"        # 0.78 + 0.1·log2 9 > 0.80 + 0.1·log2 3


def test_paired_delta_and_mcnemar(rerank):
    base = {str(i): ("a", ["a"] if i < 5 else ["b"]) for i in range(10)}
    new = {str(i): ("a", ["a"] if i < 8 else ["b"]) for i in range(10)}
    s = rerank.paired(base, new)
    assert s["delta"] == pytest.approx(30.0) and (s["only_base"], s["only_new"]) == (0, 3)
    assert s["p"] == pytest.approx(0.25)


@pytest.mark.skipif(not (PROFILE_DIR / "profile.json").exists(), reason="profile not present")
def test_isl_profile_has_no_observer_knobs():
    for f in PROFILE_DIR.glob("*.json"):
        if f.name == "nikita.json":                # his original run config, kept for reference only
            continue
        cfg = json.loads(f.read_text())
        # absent keys fall back to the deployed defaults (λ 0.10, gate 0.33) — so they must be set explicitly
        assert cfg["complexity_prior_lambda"] == 0.0, f.name          # λ of §15 is applied offline, chosen on dev
        assert cfg["range_gate_rel_width"] in (0.0, 1.0), f.name      # never the cross-class gate
        assert cfg.get("calibration") == "off", f.name                # no other-class statistics
        assert "band_mode" not in cfg, f.name


GRAPHS_4_1 = REPO / "tests" / "_isl" / "coman_graphs" / "t110" / "4_1"


@pytest.mark.skipif(not GRAPHS_4_1.exists(), reason="exported training graphs not present (run coman_concepts.py export)")
def test_fold_skips_non_absorbable_examples_instead_of_aborting():
    cc = _load("coman_concepts", "notes/scripts_isl/coman_concepts.py")
    graphs = cc.load_graphs("t110", "4_1")
    order = sorted(graphs)[:24]
    concept, st = cc.fold_chain({k: graphs[k] for k in order}, order)
    assert st["absorbed"] + st["skipped"] + st["no_start"] == len(order)
    assert st["absorbed"] >= 2 and concept.number_of_nodes() > 0        # an attractor over a set, never one sample
    again, st2 = cc.fold_chain({k: graphs[k] for k in order}, order)
    assert st2 == st and cc._same(concept, again)                        # deterministic for a fixed order


def test_concept_node_insert_cost_flag():
    import sys
    for p in (REPO / "common", REPO / "src" / "classification"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    cf = _load("cost_functions_p2", "src/classification/graph_similarity/cost_functions.py")
    assert cf.node_ins_cost({}) == cf.NodeCost.IMPOSSIBLE            # default: the whole attractor must embed
    cf.CONCEPT_NODE_INSERT_COST = 1.0
    try:
        assert cf.node_ins_cost({}) == 1.0                           # P2: incomplete input, Def. 1 f >= tau
    finally:
        cf.CONCEPT_NODE_INSERT_COST = None


GRAPHS_4_1_PS = REPO / "tests" / "_isl" / "coman_graphs" / "t110ps" / "4_1"


@pytest.mark.skipif(not GRAPHS_4_1_PS.exists(), reason="exported training graphs not present (run coman_concepts.py export)")
def test_accumulate_fold_is_order_free_and_connected():
    import networkx as nx
    cc = _load("coman_concepts_acc", "notes/scripts_isl/coman_concepts.py")
    graphs = cc.load_graphs("t110ps", "4_1")
    sub = {k: graphs[k] for k in sorted(graphs)[:16]}
    seed_id, seed_g, aligned, skipped, dropped = cc.align_to_seed(sub)
    assert "_aug" not in seed_id                                           # the seed is an original
    assert len(aligned) + len(skipped) + len(dropped) + 1 == len(sub)
    for tau in (1.0, 0.8):
        a = cc.accumulate(seed_id, seed_g, aligned, tau)
        b = cc.accumulate(seed_id, seed_g, aligned, tau, order=list(reversed(range(len(aligned)))))
        assert set(a.nodes) == set(b.nodes) and set(map(frozenset, a.edges)) == set(map(frozenset, b.edges))
        assert a.number_of_nodes() > 0 and nx.is_connected(a)
        assert any("StartPoint" in d["labels"] for _, d in a.nodes(data=True))
        assert set(a.nodes) <= set(seed_g.nodes)                           # reductive: elements of the seed only


def test_param_layer_band_and_score():
    import sys
    sys.path.insert(0, str(REPO / "notes" / "scripts_isl"))
    q = _load("coman_param_layer_t", "notes/scripts_isl/coman_param_layer.py")
    assert q.band([0.0, 0.1, 0.2, 0.3, 5.0], 0.8) == (0.0, 0.3)              # shortest interval with >= 80 % of the values
    bands = [(0.0, 0.2), (0.5, 0.5)]
    assert q.param_score([0.1, 0.5], bands) == 1.0                            # inside both bands
    assert q.param_score([0.3, 0.5], bands) == 0.75                           # half a band-width past the edge -> 0.5
    assert q.param_score([1.0, 0.9], bands) == 0.0                            # far outside; zero width floored
