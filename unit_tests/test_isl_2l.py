"""N-2L: the professor's two-level hypergraph scheme (notes/scripts_isl/isl_2l.py) — anchors, alignment, counters."""
import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "notes" / "scripts_isl" / "isl_2l.py"
_spec = importlib.util.spec_from_file_location("isl_2l", _PATH)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


def _graph(points):
    """A polyline through `points` (image coordinates, y down)."""
    return {"nodes": [list(p) for p in points], "edges": [[i, i + 1] for i in range(len(points) - 1)]}


L_SHAPE = _graph([(40, 20), (40, 60), (70, 60)])                    # down, then a sharp turn to the right
Z_SHAPE = _graph([(30, 20), (60, 20), (30, 60), (60, 60)])           # turn one way, then the other (inflection)
LINE = _graph([(40, 20), (40, 60)])
DIAG = _graph([(40, 20), (55, 40), (70, 60)])                      # the same two ends, no corner


def test_sign_reduction_keeps_a_monotone_turn_in_one_hyperedge():
    hg = m.build(L_SHAPE, "sign")
    assert sorted(a["type"] for a in hg["anchors"]) == ["E", "E"]
    assert len(hg["hyper"]) == 1


def test_inflection_and_direction_change_become_anchors():
    z = m.build(Z_SHAPE, "sign")
    assert sorted(a["type"] for a in z["anchors"]) == ["B", "B", "E", "E"] or \
        sorted(a["type"] for a in z["anchors"]) == ["B", "E", "E"]
    d = m.build(L_SHAPE, "dir")
    assert sorted(a["type"] for a in d["anchors"]) == ["B", "E", "E"] and len(d["hyper"]) == 2


def test_capture_point_is_the_top_most_end():
    hg = m.build(L_SHAPE, "sign")
    first = min(hg["anchors"], key=lambda a: a["rank"])
    assert first["type"] == "E" and first["pos"][1] < 0.5          # (40, 20) is the upper end


def test_alignment_is_permutation_invariant_and_matches_everything_to_itself():
    a = m.build(L_SHAPE, "dir")
    perm = [2, 0, 1]
    b = {"anchors": [a["anchors"][perm.index(i)] for i in range(3)],
         "hyper": [{**h, "a": perm[h["a"]], "b": perm[h["b"]]} for h in a["hyper"]]}
    mp = m.align(a, b)
    assert mp == {i: perm[i] for i in range(3)}
    assert m.correspond(a, b, mp) == set(m.elements(a))


def test_counters_keep_only_elements_present_in_every_example_at_tau_one():
    x, y = m.build(L_SHAPE, "dir"), m.build(DIAG, "dir")
    strict = m.learn([x, x, y], tau=1.0)
    loose = m.learn([x, x, y], tau=0.6)
    assert "B" not in [a["type"] for a in strict["anchors"]]          # the corner is missing from the diagonal
    assert "B" in [a["type"] for a in loose["anchors"]]               # f = 2/3 >= 0.6 (Def. 1)
    assert len(strict["anchors"]) == 2


def test_reaction_two_sided_penalises_a_small_attractor_on_a_big_example():
    small = m.learn([m.build(LINE, "sign")] * 2, 1.0)
    big = m.build(Z_SHAPE, "sign")
    two, one, _ = m.reaction(small, m.weight_of(small), big, m.weight_of(big))
    assert two[0] < one[0]
