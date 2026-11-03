"""In-memory form of a band model loaded from Neo4j (:BandModel / :BandConcept)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class BandModel:
    model_id: str
    dm_version: str
    dim_names: List[str]
    weights: np.ndarray            # (D,)
    scale: np.ndarray              # (D,) per-dimension std over all leaf members
    band_ids: List[str]            # (C,)
    letters: List[str]             # (C,)
    forms: List[str]               # (C,)
    roles: List[str]               # (C,) "leaf" | "root"
    lo: np.ndarray                 # (C, D)
    hi: np.ndarray                 # (C, D)
    centre: np.ndarray             # (C, D)
    alpha: float = 5.0             # weight of the distance-to-centre term
    leaf_weight: float = 0.7
    root_weight: float = 0.3
    structural_ids: List[Optional[str]] = field(default_factory=list)
    # round 2 — the leaf's SHAPE CONCEPT on the dense centre line, per concept (None for roots):
    # (m, N, 2) mean anchor positions, (m, N, 2) mean tangents, (m, N, B) mean shape contexts,
    # m = originals in the leaf, N anchors each
    shape_points: List[Optional[np.ndarray]] = field(default_factory=list)
    shape_tangents: List[Optional[np.ndarray]] = field(default_factory=list)
    shape_contexts: List[Optional[np.ndarray]] = field(default_factory=list)
    stage2_lambda: float = 0.0           # weight of round 2; 0 = off
    stage2_topk: int = 5
    stage2_beta: float = 0.3

    def __post_init__(self) -> None:
        self.weights = np.asarray(self.weights, float)
        self.scale = np.maximum(np.asarray(self.scale, float), 1e-6)
        self.lo = np.atleast_2d(np.asarray(self.lo, float))
        self.hi = np.atleast_2d(np.asarray(self.hi, float))
        self.centre = np.atleast_2d(np.asarray(self.centre, float))
        self.w_over_scale = self.weights / self.scale
        if not self.structural_ids:
            self.structural_ids = [None] * len(self.band_ids)
        for name in ("shape_points", "shape_tangents", "shape_contexts"):
            if not getattr(self, name):
                setattr(self, name, [None] * len(self.band_ids))
