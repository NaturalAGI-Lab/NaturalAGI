"""Q2 / Q4 — ComAN with a parametric layer read by the soma and topology as a hard structural condition, computed
offline on top of live pl_dump dumps (pre-registration: experiments/isl_transfer_2026-10/lab_Q_param.md).

Concept reaction r(image, c) = MAX over the filter dumps of the GED similarity among `minor` entries + 0.05·log2(cc)
(as coman_rerank.py). A concept's own subclass = cid.split('s')[0]; its own training images = <train-root>/<subclass>/.
Only own positives are used (Axiom 3).

  describe <dir rel. tests/> [--procs 6]
        dense centre-line orientation mass (dense_features.dense_representation, 52 dims) + independent cycles and
        endpoints of the simplified skeleton graph, detector as at recognition (110 / 4.55, stems rule, fixed
        threshold) -> tests/_isl/dense/<dir>.jsonl (resumable)
  run --train-root _isl_train --dev-dumps a+b+.. --dev-dir mnist_dev [--test-dumps ..  --test-dir mnist_all]
        Q2 β grid, Q4a / Q4b gates, acceptance vs β 0 / ungated on dev, the combination, and (with --test-dumps) the
        official test ONCE for the combination -> results_Q_param.csv, tests/_isl/Q_param_test.jsonl
  apply --test-dumps a+b+.. --test-dir mnist_all --out <jsonl> [--beta 0.5]
        the frozen final only (no dev, no selection): per-image stem / true / pred / top3 -> <jsonl>, the input of
        make_run_folder.py (verification of experiments/run_20261024_113123)
"""
import argparse
import csv
import json
import logging
import math
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

import coman_rerank as K
import isl_cache as C

REPO = K.REPO
DENSE = REPO / "tests" / "_isl" / "dense"
EXP = REPO / "experiments" / "isl_transfer_2026-10"
LAM, TAU, WIDTH_FLOOR = 0.05, 0.8, 0.01
BETAS = (0.0, 0.1, 0.2, 0.3, 0.5)
MANIFEST = {r["image_path"].split("/")[-1][:-4]: r["structure"]
            for r in csv.DictReader(open(REPO / "datasets" / "mnist_all_manifest.csv"))}


# ----------------------------------------------------------------------------------------------- descriptors
def _describe(path):
    logging.disable(logging.CRITICAL)
    C._modules()
    import cv2
    from settings import Settings
    from skeleton_gng_mapper import SkeletonGNGMapper
    from networkx_graph_analysis import NetworkxGraphAnalysis
    from dense_features import dense_representation
    out = {"stem": Path(path).stem, "cls": Path(path).parent.name, "orient": None, "cycles": None, "ends": None}
    try:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        m = SkeletonGNGMapper(Settings(N=35), 110, 4.55, thick_stroke_threshold=0, bridge_protect_stems=True)
        skel = m.skeletonize(img, 110)
        dense = dense_representation(skel)
        out["orient"] = dense["orient"] if dense else None
        graph = m._convert_to_networkx(m._simplify_network(m.fit_gng(m.skeleton_to_points(skel))))
        graph = m._normalize(m._merge_junction_bridges(graph, img, 110, skel))
        analysis = NetworkxGraphAnalysis(graph, analysis_result_persistence_service=None, merge_threshold=10.0)
        analysis.merge_close_intersection_points()
        g = analysis.graph if hasattr(analysis, "graph") else graph
        import networkx as nx
        h = nx.Graph()
        h.add_nodes_from(g.nodes)
        h.add_edges_from((u, v) for u, v in g.edges() if u != v)
        out["cycles"] = h.number_of_edges() - h.number_of_nodes() + nx.number_connected_components(h)
        out["ends"] = sum(1 for n in h.nodes if h.degree(n) == 1)
    except Exception as exc:  # noqa: BLE001 — a detector failure = no descriptor for that image
        out["error"] = str(exc)[:120]
    return out


def describe(rel, procs):
    DENSE.mkdir(parents=True, exist_ok=True)
    cache = DENSE / f"{rel.strip('/').replace('/', '__')}.jsonl"
    done = {json.loads(line)["stem"] for line in open(cache)} if cache.exists() else set()
    files = sorted((REPO / "tests" / rel).glob("*/*.png"))
    todo = [f for f in files if f.stem not in done]
    print(f"{rel}: {len(files)} images, {len(todo)} to describe", flush=True)
    with Pool(procs) as pool, open(cache, "a") as fh:
        for i, rec in enumerate(pool.imap_unordered(_describe, todo, chunksize=16), 1):
            fh.write(json.dumps(rec) + "\n")
            if i % 1000 == 0:
                fh.flush()
                print(f"  {i}/{len(todo)}", flush=True)


def load_desc(rel):
    return {r["stem"]: r for r in (json.loads(line) for line in open(DENSE / f"{rel.strip('/').replace('/', '__')}.jsonl"))}


# ----------------------------------------------------------------------------------------------- bands and scores
def band(values, tau=TAU):
    """Shortest interval holding >= tau of the values (Def. 1) -> (lo, hi)."""
    s = sorted(values)
    k = max(1, math.ceil(tau * len(s)))
    i = min(range(len(s) - k + 1), key=lambda j: s[j + k - 1] - s[j])
    return s[i], s[i + k - 1]


def param_score(vec, bands):
    """Mean over dimensions: 1 inside the band, falling linearly to 0 one band-width outside."""
    tot = 0.0
    for v, (lo, hi) in zip(vec, bands):
        w = max(hi - lo, WIDTH_FLOOR)
        tot += 1.0 if lo <= v <= hi else max(0.0, 1.0 - (lo - v if v < lo else v - hi) / w)
    return tot / len(bands)


def subclass_models(train):
    by = defaultdict(list)
    for r in train.values():
        by[r["cls"]].append(r)
    models = {}
    for sub, rows in by.items():
        vecs = [r["orient"] for r in rows if r.get("orient")]
        cyc = [r["cycles"] for r in rows if r.get("cycles") is not None]
        ends = [r["ends"] for r in rows if r.get("ends") is not None]
        models[sub] = {"bands": [band(col) for col in zip(*vecs)] if vecs else None,
                       "cycles": (min(cyc), max(cyc)) if cyc else None, "ends": (min(ends), max(ends)) if ends else None}
    return models


def concept_reactions(spec):
    """{stem: (true, {cid: (class, r)})} — per concept MAX over the filter dumps, + λ·log2(cc)."""
    dumps, _, _ = K.load_spec(spec)
    out = {}
    for path in dumps[0]:
        best = {}
        for d in dumps:
            for e in (d.get(path) or {}).get("ranked", []):
                if e["minor"]:
                    r = (e["sim"] or 0.0) + LAM * math.log2(max(e["cc"] or 1, 1))
                    if e["cid"] not in best or r > best[e["cid"]][1]:
                        best[e["cid"]] = (e["c"], r)
        out[Path(path).stem] = (dumps[0][path]["true"], best)
    return out


def rank(reac, desc, models, beta=0.0, gate=None):
    """{stem: (true, ranked classes)} for one variant."""
    out = {}
    for stem, (true, best) in reac.items():
        d = desc.get(stem, {})
        cands = best
        if gate:
            keep = {}
            for cid, cr in best.items():
                m = models.get(cid.split("s")[0])
                ok = m is not None and d.get("cycles") is not None and m["cycles"] is not None \
                    and m["cycles"][0] <= d["cycles"] <= m["cycles"][1]
                if ok and gate == "Q4b":
                    ok = d.get("ends") is not None and m["ends"] is not None and m["ends"][0] <= d["ends"] <= m["ends"][1]
                if ok:
                    keep[cid] = cr
            cands = keep or best
        scored = []
        for cid, (cls, r) in cands.items():
            m = models.get(cid.split("s")[0])
            p = param_score(d["orient"], m["bands"]) if beta and d.get("orient") and m and m["bands"] else 0.0
            scored.append((r + beta * p, cls))
        scored.sort(key=lambda t: -t[0])
        out[stem] = (true, list(dict.fromkeys(c for _, c in scored)))
    return out


# ----------------------------------------------------------------------------------------------- run
def run(a):
    models = subclass_models(load_desc(a.train_root))
    dev_desc = load_desc(a.dev_dir)
    dev = concept_reactions(a.dev_dumps)
    base = rank(dev, dev_desc, models)
    rows, results = [], {}
    variants = [(f"Q2 beta {b}", b, None) for b in BETAS if b] + [("Q4a cycles gate", 0.0, "Q4a"),
                                                                  ("Q4b cycles + ends gate", 0.0, "Q4b")]
    b1, b3 = K.accuracy(base)
    print(f"base (N final, β 0, ungated)  dev top-1 {b1:6.2f}  top-3 {b3:6.2f}", flush=True)
    for name, beta, gate in variants:
        pr = rank(dev, dev_desc, models, beta, gate)
        t1, t3 = K.accuracy(pr)
        s = K.paired(base, pr)
        acc = s["lo"] > -1.0
        results[name] = (beta, gate, t1, acc)
        print(f"{name:<24} dev top-1 {t1:6.2f}  top-3 {t3:6.2f}  Δ {s['delta']:+.2f} [{s['lo']:+.2f}, {s['hi']:+.2f}] "
              f"McNemar p {s['p']:.2g}  -> {'ACCEPT' if acc else 'REJECT'}", flush=True)
        rows.append(["dev", name, beta, gate or "", round(t1, 2), round(t3, 2), round(s["delta"], 2), round(s["lo"], 2),
                     round(s["hi"], 2), f"{s['p']:.3g}", acc])
    q2 = [(n, v) for n, v in results.items() if n.startswith("Q2") and v[3]]
    q4 = [(n, v) for n, v in results.items() if n.startswith("Q4") and v[3]]
    beta = max(q2, key=lambda kv: kv[1][2])[1][0] if q2 else 0.0
    gate = max(q4, key=lambda kv: kv[1][2])[1][1] if q4 else None
    final = f"final: β {beta}, gate {gate or 'none'}"
    pr = rank(dev, dev_desc, models, beta, gate)
    t1, t3 = K.accuracy(pr)
    s = K.paired(base, pr)
    print(f"{final:<24} dev top-1 {t1:6.2f}  top-3 {t3:6.2f}  Δ {s['delta']:+.2f} [{s['lo']:+.2f}, {s['hi']:+.2f}] "
          f"McNemar p {s['p']:.2g}", flush=True)
    rows.append(["dev", final, beta, gate or "", round(t1, 2), round(t3, 2), round(s["delta"], 2), round(s["lo"], 2),
                 round(s["hi"], 2), f"{s['p']:.3g}", s["lo"] > -1.0])
    if a.test_dumps:
        test_desc = load_desc(a.test_dir)
        test = concept_reactions(a.test_dumps)
        fin = rank(test, test_desc, models, beta, gate)
        nf = rank(test, test_desc, models)
        asis = {Path(p).stem: v for p, v in K.predictions(*K.load_spec(a.asis)).items()}
        with open(REPO / "tests" / "_isl" / "Q_param_test.jsonl", "w") as fh:
            for stem, (true, cl) in fin.items():
                fh.write(json.dumps({"stem": stem, "true": true, "pred": cl[0] if cl else "none", "top3": cl[:3]}) + "\n")
        for part in ("", "complete", "incomplete"):
            sel = lambda pr: {k: v for k, v in pr.items() if not part or MANIFEST.get(k) == part}
            f1, f3 = K.accuracy(sel(fin))
            s1, s2 = K.paired(sel(asis), sel(fin)), K.paired(sel(nf), sel(fin))
            print(f"TEST {part or 'all':<10} n {len(sel(fin)):5}  top-1 {f1:6.2f}  top-3 {f3:6.2f}  "
                  f"vs ComAN as is {s1['delta']:+.2f} [{s1['lo']:+.2f}, {s1['hi']:+.2f}] p {s1['p']:.2g}  "
                  f"vs N final {s2['delta']:+.2f} [{s2['lo']:+.2f}, {s2['hi']:+.2f}] p {s2['p']:.2g}", flush=True)
            rows.append([f"test {part or 'all'}", final, beta, gate or "", round(f1, 2), round(f3, 2),
                         round(s2["delta"], 2), round(s2["lo"], 2), round(s2["hi"], 2), f"{s2['p']:.3g}", ""])
    out = EXP / "results_Q_param.csv"
    first = not out.exists()
    with out.open("a", newline="") as fh:
        wr = csv.writer(fh)
        if first:
            wr.writerow(["split", "variant", "beta", "gate", "top1", "top3", "delta_vs_base", "ci_lo", "ci_hi",
                         "mcnemar_p", "accepted"])
        wr.writerows(rows)


def apply(a):
    models = subclass_models(load_desc(a.train_root))
    fin = rank(concept_reactions(a.test_dumps), load_desc(a.test_dir), models, a.beta)
    with open(a.out, "w") as fh:
        for stem, (true, cl) in fin.items():
            fh.write(json.dumps({"stem": stem, "true": true, "pred": cl[0] if cl else "none", "top3": cl[:3]}) + "\n")
    for part in ("", "complete", "incomplete"):
        sel = {k: v for k, v in fin.items() if not part or MANIFEST.get(k) == part}
        t1, t3 = K.accuracy(sel)
        print(f"{part or 'all':<10} n {len(sel):5}  top-1 {t1:6.2f}  top-3 {t3:6.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["describe", "run", "apply"])
    ap.add_argument("dir", nargs="?")
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--train-root", default="_isl_train")
    ap.add_argument("--dev-dumps")
    ap.add_argument("--dev-dir", default="mnist_dev")
    ap.add_argument("--test-dumps")
    ap.add_argument("--test-dir", default="mnist_all")
    ap.add_argument("--asis", default=str(REPO / "tests" / "_isl" / "coman_mnist_all.jsonl") + "@0.1")
    ap.add_argument("--beta", type=float, default=0.5)
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "describe":
        describe(a.dir, a.procs)
    elif a.cmd == "apply":
        apply(a)
    else:
        run(a)


if __name__ == "__main__":
    sys.exit(main())
