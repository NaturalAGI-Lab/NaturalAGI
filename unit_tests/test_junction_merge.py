import networkx as nx
import pytest



@pytest.fixture(scope="module")
def jm():
    import importlib.util, sys
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "src" / "skeletonization" / "junction_merge.py"
    spec = importlib.util.spec_from_file_location("junction_merge", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _graph(points, edges):
    g = nx.Graph()
    for i, (x, y) in enumerate(points):
        g.add_node(i, x=float(x), y=float(y))
    for u, v in edges:
        g.add_edge(u, v, length=((points[u][0] - points[v][0]) ** 2 + (points[u][1] - points[v][1]) ** 2) ** 0.5)
    return g


def _h():      # two stems, a short crossbar between junctions 1 and 4
    return _graph([(0, 0), (0, 10), (0, 20), (6, 0), (6, 10), (6, 20)], [(0, 1), (1, 2), (3, 4), (4, 5), (1, 4)])


def _x():      # thinning split of a crossing: two 3-way junctions 4, 5 joined by a short link
    return _graph([(0, 0), (20, 0), (0, 20), (20, 20), (9, 10), (11, 10)], [(0, 4), (2, 4), (1, 5), (3, 5), (4, 5)])


def test_default_rule_collapses_both(jm):
    assert sum(1 for n in jm.merge_short_junction_bridges(_h(), 8.0) if True) == 5       # H loses a junction
    assert jm.merge_short_junction_bridges(_x(), 8.0).number_of_nodes() == 5             # X crossing restored


def test_protected_rule_keeps_the_crossbar_of_h_but_still_fixes_x(jm):
    h = jm.merge_short_junction_bridges(_h(), 8.0, protect_through_strokes=True)
    assert h.number_of_nodes() == 6 and sum(1 for n in h if h.degree(n) >= 3) == 2
    x = jm.merge_short_junction_bridges(_x(), 8.0, protect_through_strokes=True)
    assert x.number_of_nodes() == 5 and sum(1 for n in x if x.degree(n) >= 3) == 1
