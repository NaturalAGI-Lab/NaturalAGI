"""Builds a band model: leaf concepts (one per training original, similar originals merged)
and root concepts (one per glyph form or per letter) over the graph-level direction map.

This path never touches the node-level fold, so it cannot fail on "no common minor" and it can
describe a whole glyph form, which the intersection fold cannot. The structural concept of a
leaf, when one exists, is only linked from here (`structural_concept_id`) and serves as the
explanation, not as the decision.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import band_math
from . import shape_concept

ALPHA = 5.0          # weight of the distance-to-centre term in the score
LEAF_WEIGHT = 0.7
ROOT_WEIGHT = 0.3


def _members_of(original: str, features: Dict[str, np.ndarray]) -> Tuple[List[str], np.ndarray]:
    """The original first, then its augmentations (`<original>_aug*`), in name order."""
    names = [original] + sorted(n for n in features if n.startswith(f"{original}_aug"))
    return names, np.vstack([features[n] for n in names])


def assemble_band_model(
    model_id: str,
    forms: Dict[str, dict],
    features: Dict[str, Dict[str, np.ndarray]],
    dim_names: List[str],
    dim_block: List[str],
    dim_grid: List[int],
    dm_version: str,
    merge_similar: bool = True,
    q: float = band_math.DEFAULT_PERCENTILE,
    root_scope: str = "form",
    block_weights: Optional[Dict[str, float]] = None,
    alpha: float = ALPHA,
    leaf_weight: float = LEAF_WEIGHT,
    shapes: Optional[Dict[str, Dict[str, tuple]]] = None,
    stage2_lambda: float = 0.0,
    stage2_topk: int = 5,
    stage2_beta: float = 0.3,
):
    """Pure assembly. ``forms`` = {form: {"letter", "session_id", "originals": [file stems]}},
    ``features`` = {session_id: {file stem: direction map}},
    ``shapes`` = {session_id: {file stem: (centre-line points, tangents)}} (needed for round 2).
    -> (model dict, list of concept dicts, skipped originals)"""
    if block_weights is None and "dorient" in dim_block:
        block_weights = band_math.DENSE_BLOCK_WEIGHTS
    weights = band_math.dim_weights(dim_block, dim_grid, block_weights)
    concepts: List[dict] = []
    skipped: List[str] = []
    per_letter: Dict[str, List[np.ndarray]] = {}
    per_letter_files: Dict[str, List[str]] = {}

    def concept(band_id, letter, form, role, members, originals, files):
        lo, hi, centre = band_math.percentile_band(members, q)
        out = {
            "band_id": band_id, "model_id": model_id, "letter": letter, "form": form, "role": role,
            "lo": lo.tolist(), "hi": hi.tolist(), "centre": centre.tolist(),
            "n": int(len(members)), "sum": members.sum(0).tolist(), "sumsq": (members**2).sum(0).tolist(),
            "originals": list(originals), "member_files": list(files),
        }
        return out

    for form, spec in forms.items():
        letter = spec["letter"]
        pool = features.get(spec["session_id"], {})
        originals = [o for o in spec["originals"] if o in pool]
        skipped += [o for o in spec["originals"] if o not in pool]
        if not originals:
            continue
        members = [_members_of(o, pool) for o in originals]
        vectors = np.vstack([pool[o] for o in originals])
        if merge_similar and len(originals) > 1:
            groups = band_math.merge_similar(vectors, [m for _, m in members], weights)
        else:
            groups = [[i] for i in range(len(originals))]
        form_shapes = (shapes or {}).get(spec["session_id"], {})
        for group in groups:
            suffix = "+".join(originals[i].split("_")[-1] for i in group)
            leaf = concept(
                f"{letter}_{form}_{suffix}", letter, form, "leaf",
                np.vstack([members[i][1] for i in group]),
                [originals[i] for i in group],
                [f for i in group for f in members[i][0]],
            )
            # stage 2: the leaf's SHAPE CONCEPT (one prototype per original of the leaf): anchors with a mean
            # position, a tolerance, a mean shape context and a mean tangent, from the original and its augs
            mu, tol, hist, tan = [], [], [], []
            for i in group:
                names = [n for n in members[i][0] if n in form_shapes]
                if not names or names[0] != members[i][0][0]:
                    continue                                  # the original itself has no shape points
                pts = [np.array(form_shapes[n][0], np.float32).reshape(-1, 2) for n in names]
                tgs = [np.array(form_shapes[n][1], np.float32).reshape(-1, 2) for n in names]
                m_, t_, h_, g_ = shape_concept.leaf_prototype(pts, tgs)
                mu += m_.ravel().tolist(); tol += t_.tolist(); hist += h_.ravel().tolist(); tan += g_.ravel().tolist()
            if mu:
                leaf["shape_mu"], leaf["shape_tol"], leaf["shape_hist"], leaf["shape_tan"] = mu, tol, hist, tan
            concepts.append(leaf)
        form_members = np.vstack([m for _, m in members])
        form_files = [f for names, _ in members for f in names]
        if root_scope == "form":
            concepts.append(concept(f"{letter}_{form}_root", letter, form, "root", form_members, originals, form_files))
        per_letter.setdefault(letter, []).append(form_members)
        per_letter_files.setdefault(letter, []).extend(form_files)

    if root_scope == "letter":
        for letter, chunks in per_letter.items():
            concepts.append(concept(f"{letter}_root", letter, "*", "root", np.vstack(chunks), [], per_letter_files[letter]))

    leaves = [c for c in concepts if c["role"] == "leaf"]
    if not leaves:
        raise ValueError("No leaf concept could be built: none of the requested originals has a direction map")
    scale = band_math.pooled_scale(
        [c["n"] for c in leaves], [np.array(c["sum"]) for c in leaves], [np.array(c["sumsq"]) for c in leaves]
    )
    model = {
        "model_id": model_id, "dm_version": dm_version, "dim_names": list(dim_names),
        "weights": weights.tolist(), "scale": scale.tolist(), "q": float(q), "alpha": float(alpha),
        "leaf_weight": float(leaf_weight), "root_weight": float(1.0 - leaf_weight), "root_scope": root_scope,
        "stage2_lambda": float(stage2_lambda), "stage2_topk": int(stage2_topk), "stage2_beta": float(stage2_beta),
        "merge_similar": bool(merge_similar),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return model, concepts, skipped


class BandConceptService:
    def __init__(self, repository):
        self.repository = repository

    def build_band_model(
        self,
        model_id: str,
        forms: Dict[str, dict],
        merge_similar: bool = True,
        q: float = band_math.DEFAULT_PERCENTILE,
        root_scope: str = "form",
        block_weights: Optional[Dict[str, float]] = None,
        alpha: float = ALPHA,
        leaf_weight: float = LEAF_WEIGHT,
        stage2_lambda: float = 0.0,
        stage2_topk: int = 5,
        stage2_beta: float = 0.3,
    ) -> dict:
        schema = self.repository.read_schema()
        sessions = {spec["session_id"] for spec in forms.values()}
        features = {s: self.repository.read_session_features(s, schema["dm_version"]) for s in sessions}
        model, concepts, skipped = assemble_band_model(
            model_id, forms, features, schema["dim_names"], schema["dim_block"], schema["dim_grid"],
            schema["dm_version"], merge_similar, q, root_scope, block_weights, alpha, leaf_weight,
            shapes={spec["session_id"]: self.repository.read_session_shapes(spec["session_id"]) for spec in forms.values()}
            if stage2_lambda > 0 else None,
            stage2_lambda=stage2_lambda, stage2_topk=stage2_topk, stage2_beta=stage2_beta,
        )
        self.repository.write_model(model, concepts)
        return {
            "model_id": model_id,
            "dm_version": schema["dm_version"],
            "leaves": sum(c["role"] == "leaf" for c in concepts),
            "roots": sum(c["role"] == "root" for c in concepts),
            "letters": len({c["letter"] for c in concepts}),
            "skipped_originals": skipped,
        }
