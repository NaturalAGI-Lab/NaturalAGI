"""Neo4j access for band models and per-image direction maps (classification side)."""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from .band_model import BandModel


def load_band_models(driver) -> Dict[str, BandModel]:
    """All :BandModel nodes with their :BandConcept children. Empty dict when none exist."""
    models: Dict[str, BandModel] = {}
    with driver.session() as session:
        heads = session.run("MATCH (m:BandModel) RETURN properties(m) AS m").data()
        for head in heads:
            m = head["m"]
            rows = session.run(
                "MATCH (:BandModel {model_id: $id})-[:HAS_CONCEPT]->(c:BandConcept) "
                "RETURN c.band_id AS band_id, c.letter AS letter, c.form AS form, c.role AS role, "
                "c.lo AS lo, c.hi AS hi, c.centre AS centre, c.structural_concept_id AS structural, "
                "c.shape_mu AS shape_mu, c.shape_tan AS shape_tan, c.shape_hist AS shape_hist "
                "ORDER BY c.band_id",
                id=m["model_id"],
            ).data()
            if not rows:
                continue
            models[m["model_id"]] = BandModel(
                model_id=m["model_id"], dm_version=m["dm_version"], dim_names=list(m["dim_names"]),
                weights=m["weights"], scale=m["scale"],
                band_ids=[r["band_id"] for r in rows], letters=[r["letter"] for r in rows],
                forms=[r["form"] for r in rows], roles=[r["role"] for r in rows],
                lo=[r["lo"] for r in rows], hi=[r["hi"] for r in rows], centre=[r["centre"] for r in rows],
                alpha=float(m.get("alpha", 5.0)), leaf_weight=float(m.get("leaf_weight", 0.7)),
                root_weight=float(m.get("root_weight", 0.3)),
                structural_ids=[r["structural"] for r in rows],
                shape_points=[_shape(r["shape_mu"]) for r in rows],
                shape_tangents=[_shape(r["shape_tan"]) for r in rows],
                stage2_lambda=float(m.get("stage2_lambda", 0.0)), stage2_topk=int(m.get("stage2_topk", 5)),
                stage2_beta=float(m.get("stage2_beta", 0.3)),
            )
            model = models[m["model_id"]]
            model.shape_contexts = [
                None if sp is None or not r["shape_hist"]
                else np.array(r["shape_hist"], np.float32).reshape(len(sp), sp.shape[1], -1)
                for r, sp in zip(rows, model.shape_points)
            ]
    return models


def _shape(flat, n_points: int = 32):
    """Flat [m * n_points * 2] -> (m, n_points, 2) float32, or None."""
    return None if not flat else np.array(flat, np.float32).reshape(-1, n_points, 2)


def get_image_shape(driver, image_id: str):
    """(points (N, 2), tangents (N, 2)) of the image's dense centre line, or (None, None)."""
    with driver.session() as session:
        record = session.run(
            "MATCH (f:GraphFeatures {image_id: $image_id}) RETURN f.sp AS sp, f.st AS st", image_id=image_id
        ).single()
    if not record or not record["sp"]:
        return None, None
    return np.array(record["sp"], np.float32).reshape(-1, 2), np.array(record["st"], np.float32).reshape(-1, 2)


def get_image_feature_set(driver, image_id: str, dm_version: str) -> List[np.ndarray]:
    """The image's direction map plus, when skeletonization ran a committee, the maps of the extra skeletons."""
    with driver.session() as session:
        record = session.run(
            "MATCH (f:GraphFeatures {image_id: $image_id}) WHERE f.dm_version = $v RETURN f.dm AS dm, f.dm_alt AS alt",
            image_id=image_id, v=dm_version,
        ).single()
    if not record or not record["dm"]:
        return []
    out = [np.array(record["dm"], float)]
    if record["alt"]:
        out += list(np.array(record["alt"], float).reshape(-1, len(out[0])))   # k extra maps, flattened
    return out


def remove_image_features(driver, image_id: str) -> None:
    with driver.session() as session:
        session.run("MATCH (f:GraphFeatures {image_id: $image_id}) DETACH DELETE f", image_id=image_id)
