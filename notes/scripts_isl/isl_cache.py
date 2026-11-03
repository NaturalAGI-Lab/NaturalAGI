"""B0 — primitive cache for the matching-free ISL simulator.

The detector D is the production skeletonisation (src/skeletonization) run ONCE at a fixed binarisation threshold — no
search for a connected graph (that search is a global success criterion; Track B does not need connected graphs) —
followed by the contour-analysis junction merge. Stored per image: graph nodes (x, y) and edges after the merge, and the
thinned centre-line pixels (for curvature near the nodes).

Augmentation (manuscript §12: it explores the PARAMETRIC space and must not change structure): rotation ±10° and shift
±3 px only; family of `--augs` copies per original, seeded by file name.

Usage: isl_cache.py <split> <src dir rel. tests/> [--thr 110] [--augs 0] [--rules] [--limit N] [--procs 6]
  -> tests/_isl/skel/t<thr>[r]/<split>/<class>/<stem>[_a<j>].json
"""
import argparse
import json
import logging
import os
import sys
import zlib
from multiprocessing import Pool
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "tests" / "_isl" / "skel"
logging.disable(logging.CRITICAL)


def _modules():
    for rel in ("src/skeletonization", "src", "src/contour_analysis"):
        if str(REPO / rel) not in sys.path:
            sys.path.insert(0, str(REPO / rel))
    os.environ.update(KAFKA_TOPIC="-", DLQ_TOPIC="-", KAFKA_BOOTSTRAP_SERVERS="-")


def augment(img, seed, wide=False):
    """rotation ±10°, shift ±3 px; wide: also scale ±10 % and shear ±0.2 (structure-preserving, §12)."""
    import cv2
    rng = np.random.default_rng(seed)
    angle, dx, dy = rng.uniform(-10, 10), rng.uniform(-3, 3), rng.uniform(-3, 3)
    h, w = img.shape
    scale = rng.uniform(0.9, 1.1) if wide else 1.0
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    if wide:
        shear = rng.uniform(-0.2, 0.2)
        m = np.vstack([m, [0, 0, 1]])
        sh = np.array([[1, shear, -shear * h / 2], [0, 1, 0], [0, 0, 1]])
        m = (sh @ m)[:2]
    m[:, 2] += (dx, dy)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)


def primitives(img, thr, eps=4.55, rules=False, nodes=35):
    """One production skeleton attempt at a fixed threshold + contour-analysis junction merge.
    rules: the production skeleton rules — thick strokes (median width >= 8 px) binarised at 170, and a short
    junction-junction edge kept when a straight stem passes through (H stays H)."""
    _modules()
    from settings import Settings
    from skeleton_gng_mapper import SkeletonGNGMapper
    from networkx_graph_analysis import NetworkxGraphAnalysis
    m = SkeletonGNGMapper(Settings(N=nodes), thr, eps, thick_stroke_threshold=170 if rules else 0,
                          bridge_protect_stems=True if rules else None)
    if rules and m.median_stroke_width(img, thr) >= m.thick_stroke_px:
        thr = max(thr, m.thick_stroke_threshold)
    skel = m.skeletonize(img, thr)
    graph = m._convert_to_networkx(m._simplify_network(m.fit_gng(m.skeleton_to_points(skel))))
    graph = m._normalize(m._merge_junction_bridges(graph, img, thr, skel))
    analysis = NetworkxGraphAnalysis(graph, analysis_result_persistence_service=None, merge_threshold=10.0)
    analysis.merge_close_intersection_points()
    graph = analysis.graph if hasattr(analysis, "graph") else graph
    ids = list(graph.nodes)
    index = {n: i for i, n in enumerate(ids)}
    ys, xs = np.nonzero(skel)
    return {"nodes": [[round(float(graph.nodes[n]["x"]), 2), round(float(graph.nodes[n]["y"]), 2)] for n in ids],
            "edges": [[index[u], index[v]] for u, v in graph.edges() if u != v],
            "skel": np.stack([xs, ys], 1).astype(int).tolist(), "thr": thr}


def job(args):
    src, dst, thr, aug_seed, rules, fine, wide = args
    if dst.exists():
        return True
    import cv2
    try:
        img = cv2.imread(str(src), cv2.IMREAD_GRAYSCALE)
        if aug_seed is not None:
            img = augment(img, aug_seed, wide)
        out = primitives(img, thr, eps=2.5 if fine else 4.55, rules=rules, nodes=60 if fine else 35)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(out, separators=(",", ":")))
        return True
    except Exception as e:  # an empty / degenerate skeleton is a legitimate detector failure
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps({"error": str(e)[:200], "thr": thr}))
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split"), ap.add_argument("src")
    ap.add_argument("--thr", type=int, default=110)
    ap.add_argument("--augs", type=int, default=0)
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--rules", action="store_true", help="production skeleton rules (thick strokes, protected stems)")
    ap.add_argument("--limit", type=int, default=0, help="first N originals per class only")
    ap.add_argument("--fine", action="store_true", help="fine-scale skeleton: 60 GNG nodes, simplification 2.5")
    ap.add_argument("--wide", action="store_true", help="wider augmentation: + scale ±10 %, shear ±0.2")
    a = ap.parse_args()
    root = REPO / "tests" / a.src
    jobs = []
    tag = f"t{a.thr}{'r' if a.rules else ''}{'f' if a.fine else ''}{'w' if a.wide else ''}"
    for cdir in sorted(p for p in root.iterdir() if p.is_dir()):
        files = sorted(cdir.glob("*.png"))
        for f in files[:a.limit] if a.limit else files:
            base = CACHE / tag / a.split / cdir.name
            jobs.append((f, base / f"{f.stem}.json", a.thr, None, a.rules, a.fine, a.wide))
            for j in range(1, a.augs + 1):
                jobs.append((f, base / f"{f.stem}_a{j}.json", a.thr, zlib.crc32(f"{f.stem}:{j}".encode()), a.rules,
                             a.fine, a.wide))
    with Pool(a.procs) as pool:
        ok = sum(pool.imap_unordered(job, jobs, chunksize=16))
    print(f"{a.split} {tag}: {ok}/{len(jobs)} skeletons", flush=True)


if __name__ == "__main__":
    main()
