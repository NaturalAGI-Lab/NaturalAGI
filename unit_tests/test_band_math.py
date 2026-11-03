import numpy as np
import pytest


def test_dim_weights_share_a_block_between_its_dims_and_grid_levels(band_math, direction_map):
    _, blocks, grids = direction_map.dim_schema()
    w = band_math.dim_weights(blocks, grids)
    assert w.shape == (141,)
    assert w[:16].sum() == pytest.approx(8.8 / 2) and w[24:60].sum() == pytest.approx(8.8 / 2)
    assert w[16:20].sum() == pytest.approx(0.58 / 2) and w[69:78].sum() == pytest.approx(0.5 / 2)
    assert w[78:83].sum() == pytest.approx(1.0)
    assert w[83:91].sum() == pytest.approx(1.0 / 2) and w[91:109].sum() == pytest.approx(1.0 / 2)   # curv on both grids
    assert w[109:].sum() == pytest.approx(2.0 / 2)                                                  # epdir, one grid level


def test_percentile_band(band_math):
    members = np.arange(11, dtype=float).reshape(-1, 1)
    lo, hi, centre = band_math.percentile_band(members)
    assert lo[0] == pytest.approx(1.0) and hi[0] == pytest.approx(9.0) and centre[0] == pytest.approx(5.0)


def test_pooled_scale_equals_std_of_all_members(band_math):
    rng = np.random.default_rng(0)
    leaves = [rng.normal(size=(n, 4)) for n in (11, 22, 7)]
    got = band_math.pooled_scale([len(a) for a in leaves], [a.sum(0) for a in leaves], [(a**2).sum(0) for a in leaves])
    np.testing.assert_allclose(got, np.vstack(leaves).std(0), atol=1e-12)


def _cloud(rng, centre, spread, n=11):
    pts = np.abs(centre + rng.normal(scale=spread, size=(n, 3)))
    pts[0] = centre
    return pts


def test_merge_similar_joins_only_overlapping_modes(band_math):
    rng = np.random.default_rng(1)
    w = np.ones(3)
    a = _cloud(rng, np.array([1.0, 1.0, 1.0]), 0.2)
    b = _cloud(rng, np.array([1.02, 1.0, 0.99]), 0.2)       # same mode as a
    c = _cloud(rng, np.array([5.0, 0.1, 3.0]), 0.2)         # a different mode
    groups = band_math.merge_similar(np.array([a[0], b[0], c[0]]), [a, b, c], w)
    assert sorted(map(sorted, groups)) == [[0, 1], [2]]


def test_merge_similar_without_augmentations_never_merges(band_math):
    originals = np.array([[1.0, 1.0], [1.0, 1.0001]])
    groups = band_math.merge_similar(originals, [originals[[0]], originals[[1]]], np.ones(2))
    assert sorted(map(sorted, groups)) == [[0], [1]]
