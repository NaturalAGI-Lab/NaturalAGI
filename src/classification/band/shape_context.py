"""Round 2 of band classification: the image's centre line against the leaves' SHAPE CONCEPTS.

Every sampled centre-line point is described by where the rest of the line lies around it (a shape
context: log-polar histogram, 5 radii x 12 angles, radii relative to the mean point distance, so
scale-free; Belongie et al.). A leaf's shape concept is N anchors with a mean position, a mean shape
context and a mean tangent, built from one original and its augmentations by the concept creator
(band_concepts/shape_concept.py); no individual example is kept. The image is compared with a shape
concept by how well each point finds an anchor with similar surroundings, position and tangent.
The comparison is elastic — it tolerates the stretch and slant a fixed grid cannot. No learning;
the matched point / anchor pairs are the explanation.

Round 1 (band concepts) proposes the top-k letters; this round re-ranks them.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np

RADIAL_BINS = 5
ANGULAR_BINS = 12
POSITION_WEIGHT = 0.3


def shape_context(points: np.ndarray) -> np.ndarray:
    """(N, 2) unit-box points -> (N, RADIAL_BINS * ANGULAR_BINS) normalised histograms."""
    points = np.asarray(points, np.float32)
    d = np.linalg.norm(points[:, None] - points[None], axis=2)
    mean = d[d > 0].mean() if (d > 0).any() else 1.0
    r = d / mean
    edges = np.logspace(np.log10(0.125), np.log10(2.0), RADIAL_BINS + 1)
    rb = np.clip(np.searchsorted(edges, r) - 1, 0, RADIAL_BINS - 1)
    ang = np.arctan2(points[None, :, 1] - points[:, None, 1], points[None, :, 0] - points[:, None, 0]) % (2 * np.pi)
    tb = np.minimum((ang / (2 * np.pi) * ANGULAR_BINS).astype(int), ANGULAR_BINS - 1)
    hist = np.zeros((len(points), RADIAL_BINS * ANGULAR_BINS), np.float32)
    valid = (r > 0) & (r <= edges[-1])
    for i in range(len(points)):
        np.add.at(hist[i], rb[i][valid[i]] * ANGULAR_BINS + tb[i][valid[i]], 1.0)
    return hist / np.maximum(hist.sum(1, keepdims=True), 1e-6)


def distances(h, p, t, proto_h, proto_p, proto_t, beta: float) -> np.ndarray:
    """One image (N,B), (N,2), (N,2) against M shape concepts (M,N,B), (M,N,2), (M,N,2) -> (M,) costs:
    mean over the points of the best partner's cost, in both directions (image -> anchors and back)."""
    num = (h[None, :, None, :] - proto_h[:, None, :, :]) ** 2
    den = h[None, :, None, :] + proto_h[:, None, :, :] + 1e-6
    cost = 0.5 * (num / den).sum(3)
    cost = cost + POSITION_WEIGHT * np.linalg.norm(p[None, :, None, :] - proto_p[:, None, :, :], axis=3)
    if beta:
        cost = cost + beta * 0.5 * (1.0 - np.einsum("id,mjd->mij", t, proto_t))
    return 0.5 * (cost.min(2).mean(1) + cost.min(1).mean(1))


def letter_distance(model, letter: str, h, p, t) -> float:
    """Distance of the image to the closest shape concept among the letter's leaves."""
    best = float("inf")
    for i, (l, role) in enumerate(zip(model.letters, model.roles)):
        if l != letter or role != "leaf" or model.shape_contexts[i] is None:
            continue
        d = distances(h, p, t, model.shape_contexts[i], model.shape_points[i], model.shape_tangents[i], model.stage2_beta)
        best = min(best, float(d.min()))
    return best


def rerank(model, ranked: List, points: Optional[np.ndarray], tangents: Optional[np.ndarray]) -> List:
    """Re-rank the top `stage2_topk` letters by band score + stage2_lambda * shape-context distance
    (both standardised within those letters). Returns the list unchanged when stage 2 is off or the
    image carries no shape points."""
    k = min(int(model.stage2_topk), len(ranked))
    if model.stage2_lambda <= 0 or points is None or k < 2:
        return ranked
    h = shape_context(points)
    sc = np.array([letter_distance(model, ls.letter, h, points, tangents) for ls in ranked[:k]])
    if not np.isfinite(sc).all():
        return ranked
    band = np.array([ls.score for ls in ranked[:k]])
    zb = (band - band.mean()) / (band.std() + 1e-9)
    zs = (sc - sc.mean()) / (sc.std() + 1e-9)
    order = np.argsort(zb + model.stage2_lambda * zs, kind="stable")
    return [ranked[i] for i in order] + ranked[k:]
