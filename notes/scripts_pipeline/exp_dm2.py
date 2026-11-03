"""Backlog #2 — dm2 = dm1 + curvature and signed endpoint directions, offline on the skeleton caches.

New blocks (all from the post-merge skeleton graph, bbox-normalised like dm1):
  curv   per cell (2x2 and 3x3): turning angle mass at degree-2 nodes, split into bends toward the
         glyph centroid (concave, "dents in") and away from it (convex, "bulges out")   -> 8 + 18
  sharp  per 3x3 cell: number of turns sharper than 60 deg (V-corner vs U-arc)           -> 9
  epdir  per 2x2 cell: outward direction of each endpoint's last edge, 8 signed bins
         (which way a tail points: g/q, t/f)                                             -> 32
Baseline and dm2 models use the fsbn configuration (no merge, per-form root) on the rot+-8 aug set.
Knobs (block weights) are chosen on the TUNE half of the test (even stems), reported on HELD-OUT.
Usage: exp_dm2.py [compute|eval]
"""
import json
import math
import sys
import time
from itertools import product
from multiprocessing import Pool
from pathlib import Path

import networkx as nx
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.argv = [sys.argv[0], "--post-merge"] + sys.argv[1:]
sys.path.insert(0, str(REPO / "notes" / "scripts_pipeline"))
import pl_band_parity as P  # noqa: E402  (loads production modules, POST_MERGE on)
from direction_map import _cell_weights  # noqa: E402
from band.band_scorer import score_letters  # noqa: E402
from band.band_model import BandModel  # noqa: E402
from band_concepts import band_math as bm  # noqa: E402

EXTRA_BLOCKS = [("curv", 2, 8), ("curv", 3, 18), ("sharp", 3, 9), ("epdir", 2, 32)]
N_EXTRA = sum(n for _, _, n in EXTRA_BLOCKS)


def _dir_bins(vecs, bins=8):
    w = np.zeros((len(vecs), bins))
    if not len(vecs):
        return w
    ang = np.arctan2(vecs[:, 1], vecs[:, 0]) % (2 * math.pi)
    x = ang / (2 * math.pi) * bins
    b0 = np.floor(x).astype(int) % bins
    fr = x - np.floor(x)
    rows = np.arange(len(vecs))
    np.add.at(w, (rows, b0), 1 - fr); np.add.at(w, (rows, (b0 + 1) % bins), fr)
    return w


def extra_dims(graph: nx.Graph) -> np.ndarray:
    nodes = list(graph.nodes)
    if not nodes:
        return np.zeros(N_EXTRA)
    xy = np.array([[graph.nodes[n]["x"], graph.nodes[n]["y"]] for n in nodes], float)
    lo, hi = xy.min(0), xy.max(0)
    unit = (xy - lo) / np.maximum(hi - lo, 1e-6)
    pos = {n: unit[i] for i, n in enumerate(nodes)}
    centroid = unit.mean(0)
    turn_pos, turn_val, toward, sharp_pos = [], [], [], []
    for n in nodes:
        nb = list(graph.neighbors(n))
        if len(nb) != 2:
            continue
        a, b = pos[nb[0]] - pos[n], pos[nb[1]] - pos[n]
        na, nb_ = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-9 or nb_ < 1e-9:
            continue
        a, b = a / na, b / nb_
        theta = math.pi - math.acos(max(-1.0, min(1.0, float(a @ b))))   # 0 = straight
        concave = a + b
        turn_pos.append(pos[n]); turn_val.append(theta)
        toward.append(float(concave @ (centroid - pos[n])) > 0)
        if theta > math.radians(60):
            sharp_pos.append(pos[n])
    turn_pos = np.array(turn_pos).reshape(-1, 2); turn_val = np.array(turn_val); toward = np.array(toward, bool)
    ep_pos, ep_dir = [], []
    for n in nodes:
        nb = list(graph.neighbors(n))
        if len(nb) == 1:
            d = pos[n] - pos[nb[0]]
            if np.linalg.norm(d) > 1e-9:
                ep_pos.append(pos[n]); ep_dir.append(d / np.linalg.norm(d))
    ep_pos = np.array(ep_pos).reshape(-1, 2); ep_dir = np.array(ep_dir).reshape(-1, 2)
    parts = []
    for g in (2, 3):
        cells = _cell_weights(turn_pos, g)
        parts.append(np.concatenate([(cells * (turn_val * toward)[:, None]).sum(0), (cells * (turn_val * ~toward)[:, None]).sum(0)]))
    parts.append(_cell_weights(np.array(sharp_pos).reshape(-1, 2), 3).sum(0))
    parts.append((_cell_weights(ep_pos, 2)[:, :, None] * _dir_bins(ep_dir)[:, None, :]).sum(0).ravel())
    return np.concatenate(parts)


def _one(path):
    return extra_dims(P._merged(nx.node_link_graph(json.load(open(path)))))


def load_extra(split):
    cache = P.REF / f"dm2x_{split}.npz"
    if cache.exists():
        return np.load(cache)["x"]
    rows = []
    for cdir in sorted((P.REF / "skel_cache" / split).iterdir()):
        rows += [str(f) for f in sorted(cdir.glob("*.json"))]
    t0 = time.time()
    with Pool(4) as pool:
        x = np.array(pool.map(_one, rows, chunksize=64))
    np.savez_compressed(cache, x=x)
    print(f"{split}: {len(x)} extra vectors in {time.time()-t0:.0f}s", flush=True)
    return x


def predict(D, model, chunk=2000):
    """Top-1 letter per row of D, same rule as band_scorer.score_letters, vectorised."""
    keys = sorted({(l, f) for l, f, r in zip(model.letters, model.forms, model.roles) if r == "leaf"})
    leaf_cols = {key: [i for i, (l, f, r) in enumerate(zip(model.letters, model.forms, model.roles)) if r == "leaf" and (l, f) == key] for key in keys}
    root_col = {(l, f): i for i, (l, f, r) in enumerate(zip(model.letters, model.forms, model.roles)) if r == "root"}
    letters = sorted({l for l, _ in keys})
    out = []
    for s in range(0, len(D), chunk):
        X = D[s:s + chunk]
        outside = np.maximum(model.lo[None] - X[:, None], 0.0) + np.maximum(X[:, None] - model.hi[None], 0.0)
        S = (outside * model.w_over_scale).sum(2)
        S += model.alpha * (((X[:, None] - model.centre[None]) ** 2 / (np.abs(X[:, None]) + np.abs(model.centre[None]) + 1e-9)) * model.weights).sum(2)
        per_letter = np.full((len(X), len(letters)), np.inf)
        for (l, f), cols in leaf_cols.items():
            leaf = S[:, cols].min(1)
            r = root_col.get((l, f), root_col.get((l, "*")))
            total = model.leaf_weight * leaf + model.root_weight * S[:, r] if r is not None else leaf
            j = letters.index(l)
            per_letter[:, j] = np.minimum(per_letter[:, j], total)
        out.append(np.array(letters)[per_letter.argmin(1)])
    return np.concatenate(out)


def evaluate():
    names, blocks, grids = P.dim_schema()
    tr_cls, tr_stem, tr_dm = P.load_split("e52_train")
    _, ag_stem, ag_dm = P.load_split("e52_train_aug")
    te_cls, te_stem, te_dm = P.load_split("testfull")
    xtr, xag, xte = load_extra("e52_train"), load_extra("e52_train_aug"), load_extra("testfull")
    truth = np.array(te_cls)
    stem_no = np.array([int(s.split("_")[-1]) if s.split("_")[-1].isdigit() else i for i, s in enumerate(te_stem)])
    tune, held = stem_no % 2 == 0, stem_no % 2 == 1
    ext_blocks = [b for b, g, n in EXTRA_BLOCKS for _ in range(n)]
    ext_grids = [g for b, g, n in EXTRA_BLOCKS for _ in range(n)]
    ext_names = [f"{b}{g}_{i}" for b, g, n in EXTRA_BLOCKS for i in range(n)]

    def run(budget, w_curv, w_sharp, w_epdir):
        use = [b for b, w in (("curv", w_curv), ("sharp", w_sharp), ("epdir", w_epdir)) if w > 0]
        keep = np.array([b in use for b in ext_blocks])
        bw = dict(bm.DEFAULT_BLOCK_WEIGHTS, curv=w_curv, sharp=w_sharp, epdir=w_epdir)
        all_blocks = list(blocks) + [b for b, k in zip(ext_blocks, keep) if k]
        all_grids = list(grids) + [g for g, k in zip(ext_grids, keep) if k]
        # dm1's own weights must not change when blocks are appended: its grid levels stay (2,3)
        w1 = bm.dim_weights(blocks, grids)
        w2 = bm.dim_weights([b for b, k in zip(ext_blocks, keep) if k], [g for g, k in zip(ext_grids, keep) if k], bw) if keep.any() else np.zeros(0)
        weights = np.concatenate([w1, w2])
        nm = list(names) + [n for n, k in zip(ext_names, keep) if k]
        D_tr, D_ag, D_te = (np.hstack([tr_dm, xtr[:, keep]]), np.hstack([ag_dm, xag[:, keep]]), np.hstack([te_dm, xte[:, keep]]))
        model = P.build_model(budget, "form", tr_cls, tr_stem, D_tr, ag_stem, D_ag, weights, nm, merge=False)
        pred = predict(D_te, model)
        ok = pred == truth
        return 100 * ok[tune].mean(), 100 * ok[held].mean(), 100 * ok.mean()

    print(f"test {len(te_dm)} (tune {tune.sum()} / held {held.sum()}); fsbn config (no merge, form root), rot8 augmentation")
    for budget in (2, 4, 10):
        base = run(budget, 0, 0, 0)
        print(f"\nB={budget}: dm1 baseline tune {base[0]:.2f} held {base[1]:.2f} all {base[2]:.2f}")
        res = []
        for wc, ws, we in product((0, 0.5, 1, 2, 4), (0, 0.5, 1, 2), (0, 0.5, 1, 2)):
            if wc == ws == we == 0:
                continue
            r = run(budget, wc, ws, we)
            res.append((r[0], r[1], r[2], wc, ws, we))
        res.sort(reverse=True)
        for r in res[:5]:
            print(f"   tune {r[0]:.2f} held {r[1]:.2f} all {r[2]:.2f} (delta held {r[1]-base[1]:+.2f}) curv={r[3]} sharp={r[4]} epdir={r[5]}")
        for tag, key in (("curv only", lambda r: r[4] == 0 and r[5] == 0), ("sharp only", lambda r: r[3] == 0 and r[5] == 0), ("epdir only", lambda r: r[3] == 0 and r[4] == 0)):
            best = max((r for r in res if key(r)), key=lambda r: r[0])
            print(f"   {tag:10s}: best tune {best[0]:.2f} held {best[1]:.2f} (delta held {best[1]-base[1]:+.2f}) w={best[3] or best[4] or best[5]}")


if __name__ == "__main__":
    if "compute" in sys.argv:
        for s in ("e52_train", "e52_train_aug", "testfull"):
            load_extra(s)
    else:
        evaluate()
