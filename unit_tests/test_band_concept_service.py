import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent

FORBIDDEN = {"image_id", "session_id", "samples", "concept_id"}


@pytest.fixture(scope="module")
def service(direction_map):
    path = str(REPO / "src" / "concept_creator" / "src")
    if path not in sys.path:
        sys.path.insert(0, path)
    import band_concepts.band_concept_service as module
    return module, direction_map.dim_schema()


def _pool(rng, stems, centres, n_aug=10):
    out = {}
    for stem, centre in zip(stems, centres):
        out[stem] = centre
        for k in range(n_aug):
            out[f"{stem}_aug{k}"] = np.abs(centre + rng.normal(scale=0.01, size=141))
    return out


def _build(service, **kw):
    module, (names, blocks, grids) = service
    rng = np.random.default_rng(0)
    a, b = np.abs(rng.normal(1, 0.2, 141)), np.abs(rng.normal(3, 0.2, 141))
    features = {
        "fs-pool-uA": _pool(rng, ["uA_00", "uA_01"], [a, a + 1e-4]),         # same writing mode -> merge
        "fs-pool-la": _pool(rng, ["la_00", "la_01"], [a, b]),                # two different modes
    }
    forms = {
        "uA": {"letter": "A", "session_id": "fs-pool-uA", "originals": ["uA_00", "uA_01", "uA_99"]},
        "la": {"letter": "A", "session_id": "fs-pool-la", "originals": ["la_00", "la_01"]},
    }
    return module.assemble_band_model("m1", forms, features, names, blocks, grids, "dm2", **kw), features


def test_leaves_roots_ids_and_skipped(service):
    (model, concepts, skipped), _ = _build(service)
    ids = sorted(c["band_id"] for c in concepts)
    assert ids == ["A_la_00", "A_la_01", "A_la_root", "A_uA_00+01", "A_uA_root"]
    assert skipped == ["uA_99"]
    merged = next(c for c in concepts if c["band_id"] == "A_uA_00+01")
    assert merged["n"] == 22 and merged["originals"] == ["uA_00", "uA_01"]
    assert model["root_scope"] == "form" and len(model["weights"]) == len(model["scale"]) == 141


def test_no_property_that_cleanup_queries_delete_by(service):
    (model, concepts, _), _ = _build(service)
    assert not FORBIDDEN & set(model)
    for c in concepts:
        assert not FORBIDDEN & set(c)


def test_scale_is_the_std_of_all_leaf_members(service):
    (model, concepts, _), features = _build(service, merge_similar=False)
    members = np.vstack([features[s][f] for s in features for f in features[s]])
    np.testing.assert_allclose(model["scale"], np.maximum(members.std(0), 1e-6), atol=1e-10)
    assert sum(c["role"] == "leaf" for c in concepts) == 4


def test_letter_wide_root(service):
    (model, concepts, _), _ = _build(service, root_scope="letter")
    roots = [c for c in concepts if c["role"] == "root"]
    assert [(r["band_id"], r["form"], r["n"]) for r in roots] == [("A_root", "*", 44)]


def test_leaves_carry_a_shape_concept_and_no_examples(service):
    """Round 2 needs a shape concept per leaf; no individual training example may be stored."""
    (module, (names, blocks, grids)), np = service, __import__("numpy")
    rng = np.random.default_rng(5)
    stems = ["uA_00", "uA_00_aug1", "uA_00_aug2"]
    pool = {s: np.abs(rng.normal(1, 0.1, len(names))) for s in stems}
    base = rng.random((32, 2)).astype(np.float32)
    shapes = {"s": {s: ((base + rng.normal(0, 0.01, base.shape)).ravel().tolist(), np.tile([1.0, 0.0], 32).tolist()) for s in stems}}
    forms = {"uA": {"letter": "A", "session_id": "s", "originals": ["uA_00"]}}
    model, concepts, _ = module.assemble_band_model("m", forms, {"s": pool}, names, blocks, grids, "dm2",
                                                    merge_similar=False, shapes=shapes, stage2_lambda=1.0)
    leaf = next(c for c in concepts if c["role"] == "leaf"); root = next(c for c in concepts if c["role"] == "root")
    assert len(leaf["shape_mu"]) == 64 and len(leaf["shape_tol"]) == 32 and len(leaf["shape_tan"]) == 64
    assert len(leaf["shape_hist"]) == 32 * 60 and "shape_mu" not in root
    assert not any(k in c for c in concepts for k in ("member_dm", "member_sp", "member_st"))   # file names only, no vectors
    assert model["stage2_lambda"] == 1.0 and "tiebreak_tau" not in model
