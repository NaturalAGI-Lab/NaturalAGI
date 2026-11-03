"""Matching-free ISL simulator (notes/scripts_isl/isl_sim.py): local learning rules and readout."""
import importlib.util
import itertools
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "notes" / "scripts_isl" / "isl_sim.py"
_spec = importlib.util.spec_from_file_location("isl_sim", _PATH)
sim = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sim)


def _neuron(families):
    n = sim.Neuron("x", "seed")
    for fam in families:
        n.learn(set(fam), {k: 1.0 for k in fam})
    return n


def test_family_presence_is_a_majority_vote():
    members = [{"a": 1.0, "b": 1.0}, {"a": 1.0}, {"a": 1.0, "b": 1.0, "c": 1.0}]
    keys, _ = sim.family_presence(members, augmented=True)
    assert keys == {"a", "b"}                     # c is present in 1 of 3 members only


def test_pruning_keeps_elements_with_frequency_at_least_tau():
    n = _neuron([{"a", "b"}, {"a", "c"}, {"a", "b"}])
    assert set(n.attractor(1.0)) == {"a"}
    assert set(n.attractor(0.6)) == {"a", "b"}   # b in 2 of 3 originals
    assert set(n.attractor(0.3)) == {"a", "b", "c"}


def test_attractor_does_not_depend_on_presentation_order():
    fams = [{"a", "b"}, {"a", "c"}, {"a", "b", "d"}]
    results = {frozenset(_neuron(p).attractor(0.6)) for p in itertools.permutations(fams)}
    assert len(results) == 1


def test_normalised_readout_is_one_for_the_seed_and_lower_for_a_superset():
    att = {"a": 2.0, "b": 1.0}
    assert sim.response(att, 3.0, {"a": 2.0, "b": 1.0}, "c") == pytest.approx(1.0)
    assert sim.response(att, 3.0, {"a": 2.0, "b": 1.0}, "a") == pytest.approx(1.0)
    bigger = {"a": 2.0, "b": 1.0, "z": 6.0}       # extra input drive lowers the divisively normalised response
    assert sim.response(att, 3.0, bigger, "c") < 1.0
    assert sim.response(att, 3.0, bigger, "a") == pytest.approx(1.0)


def test_response_of_a_neuron_ignores_other_neurons():
    act = {"a": 1.0, "b": 1.0}
    alone = sim.response({"a": 1.0}, 1.0, act, "c")
    _ = [sim.response({"b": 1.0, "q": 1.0}, 2.0, act, "c") for _ in range(3)]   # other neurons evaluated
    assert sim.response({"a": 1.0}, 1.0, act, "c") == alone


def test_extract_finds_endpoints_corner_and_two_strokes_on_an_L():
    data = {"nodes": [[30, 30], [30, 50], [30, 70], [50, 70], [70, 70]],
            "edges": [[0, 1], [1, 2], [2, 3], [3, 4]], "skel": [[30, 30], [30, 70], [70, 70]]}
    points, relations = sim.extract(data)
    kinds = sorted(p["type"] for p in points)
    assert kinds == ["C", "E", "E"]
    assert sorted(r["type"] for r in relations) == ["CE", "CE"]
    act = sim.activate(points, relations, {"levels": sim.LEVELS, "relations": True})
    assert any(k[0] == "R" for k in act) and any(k[0] == "C" for k in act)


def test_overlapping_field_adds_the_nearer_neighbour_only():
    assert sim._neighbours("pos", (0.30, 0.10), 2) == [1]          # x near the middle line -> right cell; y far from it
    assert sim._neighbours("pos", (0.10, 0.10), 2) == []           # deep inside the top-left cell, at the outer border
    assert sim._neighbours("dir", 40.0, 4) == [1]                  # 40° is in the 0° sector, nearer to 90°
    assert sim._neighbours("dir", 40.0, 2) == []                   # coarse halves do not overlap


def test_exact_fields_give_activation_equal_to_weight_and_overlap_adds_half_active_keys():
    data = {"nodes": [[30, 30], [30, 50], [30, 70], [50, 70], [70, 70]],
            "edges": [[0, 1], [1, 2], [2, 3], [3, 4]], "skel": [[30, 30], [30, 70], [70, 70]]}
    pts, rels = sim.extract(data)
    exact = sim.activate(pts, rels, {"levels": sim.LEVELS, "relations": True, "rf": "exact"})
    over = sim.activate(pts, rels, {"levels": sim.LEVELS, "relations": True, "rf": "overlap"})
    assert all(v == pytest.approx(sim.key_weight(k)) for k, v in exact.items())
    assert set(exact) <= set(over) and len(over) > len(exact)
    assert any(v == pytest.approx(0.5 * sim.key_weight(k)) for k, v in over.items() if k not in exact)


def test_channels_take_the_max_and_curvature_of_an_L_is_ninety_degrees():
    data = {"nodes": [[30, 30], [30, 50], [30, 70], [50, 70], [70, 70]],
            "edges": [[0, 1], [1, 2], [2, 3], [3, 4]], "skel": [[30, 30], [30, 70], [70, 70]]}
    pts, rels = sim.extract(data)
    cfg = {"levels": sim.LEVELS, "relations": True, "frame": "centroid", "curves": True}
    one = sim.activate(pts, rels, cfg)
    both = sim.activate_channels([data, {"error": "missing"}], cfg)
    assert both == one
    straight = {"nodes": [[30, 30], [30, 50], [30, 70]], "edges": [[0, 1], [1, 2]], "skel": [[30, 30], [30, 70]]}
    _, r = sim.extract(straight)
    assert r[0]["curv"] == pytest.approx(0.0, abs=1e-6)
    bent = {"nodes": [[30, 30], [30, 50], [50, 50]], "edges": [[0, 1], [1, 2]], "skel": [[30, 30], [50, 50]]}
    pts_b, r_b = sim.extract(bent)            # the middle node is a corner (90°): two straight strokes
    assert sorted(p["type"] for p in pts_b) == ["C", "E", "E"] and all(x["curv"] == pytest.approx(0.0, abs=1e-6) for x in r_b)


def test_arcs_along_a_stroke_are_straight_for_a_line_and_bend_inward_for_an_arc():
    import numpy as np
    line = np.array([[0.2, 0.5], [0.4, 0.5], [0.6, 0.5], [0.8, 0.5]])
    assert all(a["bend"] < 1e-6 and a["side"] == 0 for a in sim._arcs(line, np.array([0.5, 0.2])))
    t = np.linspace(np.pi, 2 * np.pi, 13)                      # lower half circle around the centre of mass
    arc = np.stack([0.5 + 0.3 * np.cos(t), 0.5 - 0.3 * np.sin(t)], 1)
    arcs = sim._arcs(arc, np.array([0.5, 0.5]))
    assert len(arcs) == 3 and all(40 < a["bend"] < 50 and a["side"] == 1 for a in arcs)


def test_chains_add_arc_and_junction_branch_synapses():
    data = {"nodes": [[50, 30], [50, 50], [50, 70], [30, 50], [70, 50]],
            "edges": [[0, 1], [1, 2], [1, 3], [1, 4]], "skel": [[50, 30], [50, 70], [30, 50], [70, 50]]}
    pts, rels = sim.extract(data)
    base = sim.activate(pts, rels, {"levels": sim.LEVELS, "relations": True})
    more = sim.activate(pts, rels, {"levels": sim.LEVELS, "relations": True, "chains": True})
    assert set(base) < set(more)
    assert any(k[0] == "JB" for k in more) and any(k[0] == "K" for k in more)


# ---- his point 3: vector reaction (structural, parametric) and a local competition rule identical for every neuron
def _att_neuron(cls, keys):
    n = sim.Neuron(cls, "seed")
    n.att = {k: 1.0 for k in keys}
    n.att_w = float(len(keys))
    return n


S1, S2, S3 = ("R", "EE", 1), ("R", "EC", 2), ("K", 3)          # relational synapses (hyperedges, arcs)
P1, P2, P3 = ("E", 1), ("C", 2), ("J", 3)                     # point synapses


def test_reaction_vector_splits_structural_and_parametric():
    n = _att_neuron("a", [S1, S2, P1, P2])
    act = {S1: 1.0, P1: 1.0, P2: 1.0}
    rs, rp = sim.reaction_vector(n, act, drive_s=1.0, drive_p=2.0)
    assert rs == pytest.approx(1 / (2 * 1.0) ** 0.5) and rp == pytest.approx(2 / (2 * 2.0) ** 0.5)


def test_pareto_dominated_neuron_is_inhibited_and_sum_breaks_the_rest():
    a = _att_neuron("a", [S1, P1])                 # matches one structural + one parametric synapse
    b = _att_neuron("b", [S1, S2, P1, P2])         # matches everything a matches and more of the stimulus
    act = {S1: 1.0, S2: 1.0, P1: 1.0, P2: 1.0}
    assert sim.compete([(0.9, 0), (0.8, 1)], [a, b], act, "pareto") == 1


def test_distinct_evidence_decides_between_co_active_neurons():
    a = _att_neuron("a", [S1, P1, S3])             # its own synapse S3 is present in the stimulus
    b = _att_neuron("b", [S1, P1, P3])             # its own synapse P3 is absent
    act = {S1: 1.0, P1: 1.0, S3: 1.0}
    # b has the (slightly) larger scalar response, both are co-active (>= 0.9 x max): a wins by its distinctive evidence
    assert sim.compete([(1.0, 1), (0.95, 0)], [a, b], act, "distinct") == 0
    # outside the co-active band nothing is compared: the argmax stays
    assert sim.compete([(1.0, 1), (0.5, 0)], [a, b], act, "distinct") == 1


def test_competition_rules_are_identical_for_every_neuron():
    a = _att_neuron("a", [S1, P1, S3])
    b = _att_neuron("b", [S1, P1, P3])
    act = {S1: 1.0, P1: 1.0, S3: 1.0}
    # swapping the neurons' positions (and responses) does not change who wins
    assert sim.compete([(1.0, 0), (0.95, 1)], [b, a], act, "distinct") == 1


# ---- P: two-level scheme inside H0, ComAN-like parameters, competition dynamics, fixations, own-positive mean
def test_new_parameter_segments():
    assert [sim._segment("tort", v, 4) for v in (1.0, 1.1, 1.3, 2.0)] == [0, 1, 2, 3]
    assert [sim._segment("ang", v, 2) for v in (30.0, 120.0)] == [0, 1]
    assert sim._segment("nlen", 1.0, 4) == 3 and sim._segment("nlen", 0.3, 2) == 0


def test_quantised_keys_include_the_coarse_level():
    keys = list(sim._quantised({("pos", 2): 1, ("pos", 4): 5}, ["pos"]))
    assert keys == [(("pos", 1, 0),), (("pos", 2, 1),), (("pos", 4, 5),)]


def test_comanfeat_and_runs_add_parametric_and_structural_synapses():
    data = {"nodes": [[50, 30], [50, 50], [50, 70], [30, 50], [70, 50]],
            "edges": [[0, 1], [1, 2], [1, 3], [1, 4]], "skel": [[50, 30], [50, 70], [30, 50], [70, 50]]}
    cfg = {"levels": sim.LEVELS, "relations": True, "frame": "centroid"}
    base = sim.activate_channels([data], cfg)
    feat = sim.activate_channels([data], {**cfg, "comanfeat": True})
    runs = sim.activate_channels([data], {**cfg, "runs": True})
    assert set(base) < set(feat) and any(k[0] == "JA" for k in feat) and any(k[0] == "RT" for k in feat)
    assert set(base) < set(runs) and any(k[0] == "RN" for k in runs)
    assert "RN" in sim.STRUCT and "RT" not in sim.STRUCT and "JA" not in sim.STRUCT


def test_fixations_restrict_the_fovea():
    data = {"nodes": [[50, 30], [50, 50], [50, 70], [30, 50], [70, 50]],
            "edges": [[0, 1], [1, 2], [1, 3], [1, 4]], "skel": [[50, 30], [50, 70], [30, 50], [70, 50]]}
    cfg = {"levels": sim.LEVELS, "relations": True, "frame": "centroid", "fovea": True}
    fine = lambda act: {k for k in act if any(n == "pos" and l == 8 for n, l, _ in sim._named(k))}
    every = fine(sim.activate_channels([data], cfg))
    one = fine(sim.activate_channels([data], {**cfg, "fixations": 1}))
    assert one and one < every                   # the fovea only at the first fixation


def test_iterated_distinct_with_the_response_condition_is_the_argmax():
    a = _att_neuron("a", [S1, P1, S3])
    b = _att_neuron("b", [S1, P1, P3])
    act = {S1: 1.0, P1: 1.0, S3: 1.0}
    assert sim.compete([(1.0, 1), (0.95, 0)], [a, b], act, "distinct_iter") == 1
    assert sim.compete([(1.0, 1), (0.95, 0)], [a, b], act, "distinct_iter_free") == 0
    # the pool rule compares only neurons above the pool mean: here both (mean 0.975 < 1.0, 0.95 is below) -> argmax
    assert sim.compete([(1.0, 1), (0.95, 0)], [a, b], act, "distinct_pool") == 1


def test_own_mean_is_the_response_to_its_own_family_stimuli():
    keys = {S1, P1}
    stimuli = {("a", "f1"): (keys, {k: 1.0 for k in keys}), ("a", "f2"): ({S1}, {S1: 1.0})}
    n = _att_neuron("a", [S1, P1])
    n.members = [("a", "f1"), ("a", "f2")]
    want = (sim.response(n.att, n.att_w, {S1: 1.0, P1: 1.0}, "c") + sim.response(n.att, n.att_w, {S1: 1.0}, "c")) / 2
    assert sim.own_mean(n, stimuli) == pytest.approx(want)


def test_shape_anchor_synapses_only_with_their_key():
    dense = {"points": [0.2, 0.2, 0.8, 0.8] * 16, "tangents": [1.0, 0.0, 0.0, 1.0] * 16}
    cfg = {"levels": sim.LEVELS, "relations": True, "frame": "centroid"}
    act = sim.shape_anchor_act(dense, cfg)
    assert act and all(k[0] == "SP" for k in act)
    assert not sim.activate_channels([], cfg, dense)                       # no key -> the base is unchanged
    assert sim.activate_channels([], {**cfg, "shape_anchors": True}, dense) == act


def test_param_score_band_and_bonus_in_the_competition():
    assert sim.band([0.0, 1.0, 2.0, 3.0, 100.0]) == (0.0, 3.0)
    assert sim.param_score([1.0, 5.0], [(0.0, 2.0), (2.0, 4.0)]) == pytest.approx((1.0 + 0.5) / 2)
    a = _att_neuron("a", [S1, P1, S3])
    b = _att_neuron("b", [S1, P1, P3])
    act = {S1: 1.0, P1: 1.0, S3: 1.0}
    assert sim.compete([(1.0, 1), (0.95, 0)], [a, b], act, "distinct_iter_free") == 0
    assert sim.compete([(1.0, 1), (0.95, 0)], [a, b], act, "distinct_iter_free", bonus={0: 0.0, 1: 2.0}) == 1


def test_sleep_consolidation_merges_overlapping_attractors_of_one_class():
    cfg = {"tau": 1.0}
    a = sim.Neuron("x", "f1")
    a.learn({S1, P1}, {S1: 1.0, P1: 1.0})
    a.members = [("x", "f1")]
    b = sim.Neuron("x", "f2")
    b.learn({S1, P1, S3}, {S1: 1.0, P1: 1.0, S3: 1.0})
    b.members = [("x", "f2")]
    c = sim.Neuron("y", "f3")
    c.learn({S1, P1}, {S1: 1.0, P1: 1.0})
    for n in (a, b, c):
        n.att = n.attractor(1.0)
    out = sim.consolidate([a, b, c], cfg, 0.5)
    merged = [n for n in out if n.cls == "x"]
    assert len(out) == 2 and len(merged) == 1
    assert set(merged[0].att) == {S1, P1} and len(merged[0].families) == 2   # f = 1 over the joined originals
    assert len(sim.consolidate([a, b, c], cfg, 0.9)) == 3                   # below θ nothing merges
