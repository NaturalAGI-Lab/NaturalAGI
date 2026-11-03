import json

import networkx as nx
import numpy as np
import pytest


def _load(path):
    return nx.node_link_graph(json.load(open(path)))


def test_matches_reference_implementation(direction_map, fixtures_dir):
    """dm1 (first 83 values) against the offline reference that produced every dm1 number,
    the dm2 blocks against the offline experiment that measured them (+2.0 pp at B=4)."""
    golden = json.load(open(fixtures_dir / "golden_dm.json"))
    golden2 = json.load(open(fixtures_dir / "golden_dm2_extra.json"))
    assert len(golden) == len(golden2) == 30
    for name, expected in golden.items():
        got = direction_map.compute_direction_map(_load(fixtures_dir / "skeletons" / f"{name}.json"))
        assert got.shape == (141,)
        np.testing.assert_allclose(got[:83], expected, rtol=0, atol=1e-12, err_msg=name)
        np.testing.assert_allclose(got[83:], golden2[name], rtol=0, atol=1e-12, err_msg=name)


def test_schema_describes_every_dimension(direction_map):
    names, blocks, grids = direction_map.dim_schema()
    assert len(names) == len(blocks) == len(grids) == direction_map.dimension_count() == 141
    assert len(set(names)) == 141
    assert blocks[:16] == ["orient"] * 16 and blocks[16:20] == ["ep"] * 4 and blocks[20:24] == ["jp"] * 4
    assert blocks[78:83] == ["glob"] * 5 and grids[78:83] == [0] * 5
    assert blocks[83:109] == ["curv"] * 26 and grids[83:91] == [2] * 8 and grids[91:109] == [3] * 18
    assert blocks[109:] == ["epdir"] * 32 and grids[109:] == [2] * 32


def _arc_u():
    """A U: every bend faces the centroid, both ends point up (negative y)."""
    g = nx.Graph()
    for i, (x, y) in enumerate([(0, 0), (0, 20), (10, 30), (20, 20), (20, 0)]):
        g.add_node(i, x=float(x), y=float(y))
    g.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4)])
    return g


def test_curvature_side_and_endpoint_direction(direction_map):
    dm = direction_map.compute_direction_map(_arc_u())
    names, _, _ = direction_map.dim_schema()
    curv_in = dm[[i for i, n in enumerate(names) if ".curv.in." in n]]
    curv_out = dm[[i for i, n in enumerate(names) if ".curv.out." in n]]
    assert curv_in.sum() > 0 and curv_out.sum() == 0
    assert curv_in[:4].sum() == pytest.approx(curv_in[4:].sum())      # same turning mass on both grids
    epdir = dm[109:].reshape(4, 8)
    assert epdir.sum() == pytest.approx(2.0)                          # two endpoints
    assert epdir[:, 6].sum() == pytest.approx(2.0)                    # both point straight "up" (-y = 270 deg)


def _letter_l():
    g = nx.Graph()
    for i, (x, y) in enumerate([(10, 10), (10, 60), (40, 60)]):
        g.add_node(i, x=float(x), y=float(y))
    g.add_edges_from([(0, 1), (1, 2)])
    return g


def test_invariant_to_translation_and_axis_scaling(direction_map):
    base = direction_map.compute_direction_map(_letter_l())
    moved = _letter_l()
    for n in moved.nodes:
        moved.nodes[n]["x"] = moved.nodes[n]["x"] * 1.0 + 25
        moved.nodes[n]["y"] = moved.nodes[n]["y"] * 1.0 - 7
    got = direction_map.compute_direction_map(moved)
    np.testing.assert_allclose(np.delete(got, [81, 82]), np.delete(base, [81, 82]), atol=1e-12)
    scaled = _letter_l()
    for n in scaled.nodes:
        scaled.nodes[n]["x"] *= 3
        scaled.nodes[n]["y"] *= 3
    np.testing.assert_allclose(direction_map.compute_direction_map(scaled), base, atol=1e-12)


def test_orientation_mass_sums_to_one_per_grid(direction_map):
    dm = direction_map.compute_direction_map(_letter_l())
    assert dm[0:16].sum() == pytest.approx(1.0)
    assert dm[24:60].sum() == pytest.approx(1.0)
    assert dm[78] == 2 and dm[79] == 0 and dm[80] == 0          # two endpoints, no junction, no cycle


def test_counts_cycles_and_junctions(direction_map):
    g = nx.cycle_graph(4)
    for n, (x, y) in zip(g.nodes, [(0, 0), (10, 0), (10, 10), (0, 10)]):
        g.nodes[n]["x"], g.nodes[n]["y"] = float(x), float(y)
    g.add_node(9, x=20.0, y=0.0)
    g.add_edge(1, 9)
    dm = direction_map.compute_direction_map(g)
    assert dm[78] == 1 and dm[79] == 1 and dm[80] == 1


@pytest.mark.parametrize("builder", ["empty", "single", "no_edges", "vertical"])
def test_degenerate_graphs_do_not_raise(direction_map, builder):
    g = nx.Graph()
    if builder == "single":
        g.add_node(0, x=5.0, y=5.0)
    elif builder == "no_edges":
        g.add_node(0, x=1.0, y=1.0)
        g.add_node(1, x=4.0, y=9.0)
    elif builder == "vertical":
        g.add_node(0, x=3.0, y=0.0)
        g.add_node(1, x=3.0, y=10.0)
        g.add_edge(0, 1)
    dm = direction_map.compute_direction_map(g)
    assert dm.shape == (141,) and np.isfinite(dm).all()


def test_deslant_makes_a_sheared_letter_equal_to_the_upright_one(direction_map):
    def letter(shear):
        g = nx.Graph()
        for i, (x, y) in enumerate([(0, 0), (0, 40), (20, 40), (20, 0), (0, 20), (20, 20)]):    # an H-like shape
            g.add_node(i, x=float(x + shear * y), y=float(y))
        g.add_edges_from([(0, 4), (4, 1), (3, 5), (5, 2), (4, 5)])
        return g
    upright = direction_map.compute_direction_map(letter(0.0), deslant=True)
    slanted = direction_map.compute_direction_map(letter(0.4), deslant=True)
    np.testing.assert_allclose(slanted, upright, atol=1e-9)
    assert np.abs(direction_map.compute_direction_map(letter(0.4)) - direction_map.compute_direction_map(letter(0.0))).max() > 0.01
