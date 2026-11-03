"""Which few originals to show the system: the most typical examples of each glyph form.

k-medoids inside one form under the 3x3 part of the direction map (the metric every offline
selection was made with), so the teacher's choice is reproducible. Pure numpy.
"""
from __future__ import annotations

from typing import List

import numpy as np

# 83-dim "dm1" layout: g2 blocks occupy 0..23, g3.orient 24..59, g3.ep 60..68, g3.jp 69..77, glob 78..82
SELECTION_SLICE = slice(24, 83)
SELECTION_WEIGHTS = np.concatenate(
    [np.full(36, 8.8 / 36), np.full(9, 0.58 / 9), np.full(9, 0.5 / 9), np.full(5, 1.0 / 5)]
)


def _chi2(P: np.ndarray, Q: np.ndarray, w: np.ndarray) -> np.ndarray:
    out = np.zeros((len(P), len(Q)))
    for i in range(len(P)):
        num = (P[i] - Q) ** 2
        den = np.abs(P[i]) + np.abs(Q) + 1e-9
        out[i] = (num / den * w).sum(1)
    return out


def _kmedoids(D: np.ndarray, k: int, start: int, iters: int = 30) -> tuple:
    """One k-medoids run on a distance matrix: farthest-point seeding from `start`, then swaps.
    -> (medoids, cost = sum of distances to the nearest medoid)"""
    medoids = [int(start)]
    while len(medoids) < k:
        medoids.append(int(np.argmax(D[:, medoids].min(1))))
    for _ in range(iters):
        label = np.argmin(D[:, medoids], 1)
        new = []
        for j in range(k):
            members = np.where(label == j)[0]
            new.append(
                int(members[np.argmin(D[np.ix_(members, members)].sum(1))]) if len(members) else medoids[j]
            )
        if new == medoids:
            break
        medoids = new
    return medoids, float(D[:, medoids].min(1).sum())


SELECTION_STARTS = 12   # multi-start: the k-medoids objective has many local optima and they differ by ~1 pp of accuracy


def select_typical(dm: np.ndarray, k: int) -> List[int]:
    """Row indices of the k samples that best summarise ``dm`` (n, D): the k-medoids solution with the lowest
    cost over SELECTION_STARTS runs (the overall medoid plus evenly spread start points). Deterministic."""
    n = len(dm)
    if k >= n:
        return list(range(n))
    X = dm[:, SELECTION_SLICE]
    D = _chi2(X, X, SELECTION_WEIGHTS)
    order = np.argsort(D.sum(1))                                  # most typical first
    starts = [int(order[0])] + [int(order[i]) for i in np.linspace(1, n - 1, SELECTION_STARTS - 1).astype(int)]
    best = None
    for start in starts:
        medoids, cost = _kmedoids(D, k, start)
        if best is None or cost < best[1] - 1e-12:
            best = (medoids, cost)
    return best[0]


def coverage_radius(dm: np.ndarray, k: int) -> tuple:
    """k typical originals of one letter and how far (90th percentile, chi2 on the selection slice) the
    letter's other candidates lie from their nearest typical one: the letter's spread at budget k."""
    medoids = [int(m) for m in select_typical(dm, min(k, len(dm)))]
    X = dm[:, SELECTION_SLICE]
    d = _chi2(X, X[medoids], SELECTION_WEIGHTS).min(1)
    return medoids, float(np.percentile(d, 90))


def adaptive_budget(pools: dict, total: int, k_min: int = 2, k_max: int = 30, stratify: bool = False) -> dict:
    """How many originals each letter gets, decided by the letters' own spread: the smallest k that
    covers the letter's candidates within one shared radius, the radius tuned so the sum is `total`.
    Wide letters (many writing modes) get more, tight ones fewer. Uses no labels of other letters
    and no test data. -> {letter: (k, [candidate indices])}"""
    radii = {L: {k: coverage_radius(dm, min(k, len(dm))) for k in range(k_min, k_max + 1)} for L, dm in pools.items()}

    def ks_for(r):
        return {L: next((k for k in range(k_min, k_max + 1) if radii[L][k][1] <= r), k_max) for L in pools}

    lo, hi = 0.0, max(radii[L][k_min][1] for L in pools)
    for _ in range(50):
        mid = (lo + hi) / 2
        if sum(ks_for(mid).values()) > total:
            lo = mid
        else:
            hi = mid
    ks = ks_for(hi)
    if stratify:      # the number per letter comes from its spread, the originals themselves cover its structures
        return {L: (ks[L], select_stratified(pools[L], ks[L])) for L in pools}
    return {L: (ks[L], list(radii[L][ks[L]][0])) for L in pools}


SIGNATURE_DIMS = (78, 79, 80)        # glob.n_endpoints, glob.n_junctions, glob.n_cycles in the direction map
STRATUM_MIN_SHARE = 0.10


def select_stratified(dm: np.ndarray, k: int) -> List[int]:
    """k originals that cover the letter's STRUCTURES as well as its shapes: candidates are grouped by their
    topology signature (endpoints, junctions, cycles); every signature held by at least STRATUM_MIN_SHARE of the
    candidates gets its proportional share of k (at least one), the rare ones are pooled; inside each group the
    originals are the multi-start k-medoids. Keeps a minority form (an upper-case Y among many y's) from being
    left out just because the majority is denser."""
    n = len(dm)
    if k >= n:
        return list(range(n))
    signatures = [tuple(int(round(v)) for v in row[list(SIGNATURE_DIMS)]) for row in dm]
    groups: dict = {}
    for j, sig in enumerate(signatures):
        groups.setdefault(sig, []).append(j)
    strata = {sig: g for sig, g in groups.items() if len(g) >= STRATUM_MIN_SHARE * n}
    rest = [j for sig, g in groups.items() if sig not in strata for j in g]
    if rest:
        strata[("rest",)] = rest
    share = {sig: k * len(g) / n for sig, g in strata.items()}
    quota = {sig: max(1, int(np.floor(v))) for sig, v in share.items()}
    while sum(quota.values()) > k:
        quota[max(quota, key=lambda sig: quota[sig] - share[sig])] -= 1
    while sum(quota.values()) < k:
        quota[max(quota, key=lambda sig: share[sig] - quota[sig])] += 1
    picked: List[int] = []
    for sig, g in strata.items():
        q = min(quota[sig], len(g))
        if q > 0:
            picked += [int(g[t]) for t in select_typical(dm[g], q)]
    return picked
