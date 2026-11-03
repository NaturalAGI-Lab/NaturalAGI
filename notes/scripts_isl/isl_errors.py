"""Error analysis of the matching-free ISL model in the terms of the theory (on DEV only — never on the test).

For every misclassified dev image:
  rank / margin      where the true class ends up in the competition (WTA, §15) and by how much it lost
  attractor overlap  weighted Jaccard of the winner's attractor and the best true-class neuron's attractor
                     (separability of attractors, §9 / eq. 105: d(A_i, A_j) > δ)
  topology           (endpoints, junctions, cycles) of the image vs the training ORIGINALS of the true and the predicted
                     class (detector / projection D, §2.1: anchors lost or added in preprocessing)
Categories (first match):
  D  detector  — the image's topology occurs in no training original of its class, but in the predicted class
  S  separab.  — topology occurs in both classes and the two attractors overlap strongly (>= the pair's median)
  C  coverage  — the true class responds clearly weaker (r_true < 0.9 r_win): no detector of the class covers the image
  M  margin    — the true class lost by < 10 %: competition decided by small differences
Usage: isl_errors.py --train ecand60:60 --dev edev [--tau 0.8 --rho 0.7 --variant best --workers 4]
"""
import argparse
import json
from collections import Counter, defaultdict

import numpy as np

import isl_sim as S


def topology(data):
    """(endpoints, junctions, independent cycles) of one cached skeleton graph."""
    if "error" in data or not data.get("nodes"):
        return None
    n = len(data["nodes"])
    deg = Counter()
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    edges = {tuple(sorted(e)) for e in data["edges"] if e[0] != e[1]}
    for u, v in edges:
        deg[u] += 1
        deg[v] += 1
        parent[find(u)] = find(v)
    comps = len({find(i) for i in range(n)})
    return (sum(1 for i in range(n) if deg[i] == 1), sum(1 for i in range(n) if deg[i] >= 3), len(edges) - n + comps)


def jaccard(a, b):
    keys = a.keys() | b.keys()
    num = sum(min(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    den = sum(max(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    return num / den if den else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default="ecand60:60")
    ap.add_argument("--dev", default="edev")
    ap.add_argument("--variant", default="best")
    ap.add_argument("--tau", type=float, default=0.8)
    ap.add_argument("--rho", type=float, default=0.7)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    split, _, lim = a.train.partition(":")
    cfg = {**S.DEFAULT, **S.IMPROVEMENTS[a.variant], "tau": a.tau, "rho": a.rho, "workers": a.workers,
           "class_scores": True}
    tr = S.load(split, cfg["channels"], int(lim) if lim else None)
    dev = [it for it in S.load(a.dev, cfg["channels"]) if it["aug"] == 0]
    neurons = S.train(S.build_stimuli(tr, cfg), cfg, 0)
    rows = S.evaluate_parallel(neurons, dev, cfg, a.workers)

    train_topo = defaultdict(Counter)
    for it in tr:
        if it["aug"] == 0:
            train_topo[it["cls"]][topology(it["data"][0])] += 1
    errors, cats = [], Counter()
    pair_cat = defaultdict(Counter)
    ranks = Counter()
    for it, r in zip(dev, rows):
        if r["pred"] == r["true"]:
            continue
        sc = r["class_scores"]
        order = sorted(sc, key=lambda c: -sc[c][0])
        rank = order.index(r["true"]) + 1 if r["true"] in sc else 99
        ranks[min(rank, 6)] += 1
        r_win, i_win = sc[r["pred"]]
        r_true, i_true = sc.get(r["true"], (0.0, None))
        topo = topology(it["data"][0])
        in_true, in_pred = train_topo[r["true"]][topo] > 0, train_topo[r["pred"]][topo] > 0
        overlap = jaccard(neurons[i_win].att, neurons[i_true].att) if i_true is not None else 0.0
        errors.append({"stem": r["stem"], "true": r["true"], "pred": r["pred"], "rank": rank,
                       "ratio": r_true / r_win if r_win else 0.0, "overlap": overlap, "topo": topo,
                       "topo_in_true": in_true, "topo_in_pred": in_pred})
    by_pair = defaultdict(list)
    for e in errors:
        by_pair["↔".join(sorted((e["true"], e["pred"])))].append(e["overlap"])
    pair_median = {p: float(np.median(v)) for p, v in by_pair.items()}
    for e in errors:
        pair = "↔".join(sorted((e["true"], e["pred"])))
        if not e["topo_in_true"] and e["topo_in_pred"]:
            c = "D"
        elif e["topo_in_true"] and e["topo_in_pred"] and e["overlap"] >= max(pair_median[pair], 0.3):
            c = "S"
        elif e["ratio"] < 0.9:
            c = "C"
        else:
            c = "M"
        e["cat"] = c
        cats[c] += 1
        pair_cat[pair][c] += 1
    n, ne = len(rows), len(errors)
    print(f"dev {n}, errors {ne} ({100 * ne / n:.1f} %), top-1 {100 * (n - ne) / n:.2f}")
    print("true class rank among errors: " + ", ".join(f"{k if k < 6 else '6+'}: {v}" for k, v in sorted(ranks.items())))
    print("categories: " + ", ".join(f"{c} {v} ({100 * v / ne:.0f} %)" for c, v in cats.most_common()))
    print(f"r_true / r_win: median {np.median([e['ratio'] for e in errors]):.3f}; "
          f"attractor overlap winner vs true: median {np.median([e['overlap'] for e in errors]):.3f}")
    print("top pairs (count; categories; median attractor overlap):")
    for pair, cnt in Counter("↔".join(sorted((e["true"], e["pred"]))) for e in errors).most_common(12):
        print(f"  {pair:<6} {cnt:4d}  {dict(pair_cat[pair])}  overlap {pair_median[pair]:.2f}")
    single = sum(1 for e in errors if e["topo"] == (2, 0, 0))
    print(f"errors on a single open stroke (2 ends, 0 junctions, 0 cycles): {single} ({100 * single / ne:.0f} %)")
    if a.out:
        with open(a.out, "w") as fh:
            for e in errors:
                fh.write(json.dumps({**e, "topo": list(e["topo"]) if e["topo"] else None}) + "\n")


if __name__ == "__main__":
    main()
