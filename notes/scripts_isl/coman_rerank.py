"""M — offline scoring of live ComAN dumps (pl_dump.py) for the compliant-improvement steps; no new live runs.

A dump spec is  path[+path...][@λ]:
  several paths  = the same images seen through several detector filters (thresholds); per concept the MAX of the
                   GED similarity over the filters (complex-cell MAX, his point 2)
  @λ             = complexity term in the neuron's reaction, score = sim + λ·log2(cc) (§15); default λ = 0
  @λ^α           = also coverage inhibition, sim · min(cc / ic, 1)^α (a small attractor in a large image is damped)
Only concepts that matched as a minor compete (as in production); no match -> "none".

  compare <base spec> <new spec> [--subset complete|incomplete] [--step S --out results_M.csv]
                                         accuracy, paired Δ with 95 % CI, exact McNemar p
  lamgrid <spec> [--lams 0,0.05,0.1,0.2] accuracy for each λ (pre-registered grid)
  report  <spec>                         top-1 / top-3 on all, `complete`, `incomplete` (official test manifest),
                                         per class, most frequent confusions
"""
import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "experiments" / "isl_transfer_2026-10"
MANIFEST = REPO / "datasets" / "mnist_all_manifest.csv"


def subset(pred, name):
    """Restrict {path: ...} to the curated `complete` / `incomplete` part of the official MNIST test."""
    if not name:
        return pred
    keep = {r["image_path"].split("/")[-1] for r in csv.DictReader(open(MANIFEST)) if r["structure"] == name}
    return {p: v for p, v in pred.items() if Path(p).name in keep}


def load_spec(spec):
    paths, _, lam = spec.partition("@")
    lam, _, alpha = lam.partition("^")
    dumps = []
    for p in paths.split("+"):
        rows = {}
        for line in open(p):
            r = json.loads(line)
            rows[r["path"]] = r
        dumps.append(rows)
    return dumps, float(lam) if lam else 0.0, float(alpha) if alpha else 0.0


def predictions(dumps, lam, alpha=0.0):
    """{path: (true, ranked classes)} — per concept MAX similarity over the dumps, then
    score = sim · min(cc / ic, 1)^α + λ·log2(cc)."""
    out = {}
    for path in dumps[0]:
        best = {}
        for d in dumps:
            r = d.get(path)
            for e in (r or {}).get("ranked", []):
                if e["minor"] and (e["cid"] not in best or (e["sim"] or 0.0) > best[e["cid"]]["sim"]):
                    best[e["cid"]] = {**e, "sim": e["sim"] or 0.0}
        scored = sorted(best.values(), key=lambda e: -(e["sim"] * min((e.get("cc") or 1) / max(e.get("ic") or 1, 1), 1.0) ** alpha
                                                         + lam * math.log2(max(e["cc"] or 1, 1))))
        classes = list(dict.fromkeys(e["c"] for e in scored))
        out[path] = (dumps[0][path]["true"], classes)
    return out


def accuracy(pred):
    n = len(pred)
    top1 = sum(1 for t, cl in pred.values() if cl and cl[0] == t)
    top3 = sum(1 for t, cl in pred.values() if t in cl[:3])
    return 100.0 * top1 / n, 100.0 * top3 / n


def mcnemar(a, b):
    """Two-sided exact McNemar p for paired correctness lists (same as isl_sim.mcnemar)."""
    b01 = sum(1 for x, y in zip(a, b) if x and not y)
    b10 = sum(1 for x, y in zip(a, b) if y and not x)
    m = b01 + b10
    if m == 0:
        return 1.0, b01, b10
    k = min(b01, b10)
    return min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m), b01, b10


def paired(base, new):
    """Δ top-1 (pp) of new vs base with a 95 % normal CI on the paired differences, and McNemar p."""
    keys = sorted(set(base) & set(new))
    a = [bool(base[k][1]) and base[k][1][0] == base[k][0] for k in keys]
    b = [bool(new[k][1]) and new[k][1][0] == new[k][0] for k in keys]
    d = [int(y) - int(x) for x, y in zip(a, b)]
    n = len(d)
    mean = sum(d) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (n - 1))
    half = 1.96 * sd / math.sqrt(n)
    p, only_base, only_new = mcnemar(a, b)
    return {"n": n, "delta": 100 * mean, "lo": 100 * (mean - half), "hi": 100 * (mean + half), "p": p,
            "only_base": only_base, "only_new": only_new}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["compare", "lamgrid", "report"])
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--lams", default="0,0.05,0.1,0.2")
    ap.add_argument("--step", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--subset", default="", choices=["", "complete", "incomplete"])
    a = ap.parse_args()
    if a.cmd == "lamgrid":
        dumps, _, alpha = load_spec(a.specs[0])
        for lam in map(float, a.lams.split(",")):
            t1, t3 = accuracy(predictions(dumps, lam, alpha))
            print(f"λ {lam:<5} top-1 {t1:6.2f}  top-3 {t3:6.2f}")
        return
    if a.cmd == "report":
        pred = predictions(*load_spec(a.specs[0]))
        for name in ("", "complete", "incomplete"):
            part = subset(pred, name)
            if not part:                         # dev / other splits are not in the test manifest
                continue
            t1, t3 = accuracy(part)
            print(f"{name or 'all':<10} n {len(part):5}  top-1 {t1:6.2f}  top-3 {t3:6.2f}")
        per = Counter(t for t, _ in pred.values())
        hit = Counter(t for t, cl in pred.values() if cl and cl[0] == t)
        print("per class: " + ", ".join(f"{c} {100 * hit[c] / per[c]:.1f}" for c in sorted(per)))
        conf = Counter(f"{t}→{cl[0] if cl else 'none'}" for t, cl in pred.values() if not cl or cl[0] != t)
        print("confusions: " + ", ".join(f"{k} {v}" for k, v in conf.most_common(8)))
        return
    base = subset(predictions(*load_spec(a.specs[0])), a.subset)
    new = subset(predictions(*load_spec(a.specs[1])), a.subset)
    (b1, b3), (n1, n3) = accuracy(base), accuracy(new)
    s = paired(base, new)
    accepted = s["lo"] > -1.0
    print(f"base {b1:6.2f} (top-3 {b3:.2f})  new {n1:6.2f} (top-3 {n3:.2f})  Δ {s['delta']:+.2f} pp "
          f"[{s['lo']:+.2f}, {s['hi']:+.2f}]  McNemar p {s['p']:.2g} (base-only {s['only_base']}, new-only "
          f"{s['only_new']})  -> {'ACCEPT' if accepted else 'REJECT'} (lower bound > -1 pp)")
    if a.out:
        out = OUT_DIR / a.out
        first = not out.exists()
        with out.open("a", newline="") as fh:
            wr = csv.writer(fh)
            if first:
                wr.writerow(["step", "base", "new", "n", "base_top1", "new_top1", "new_top3", "delta", "ci_lo", "ci_hi",
                             "mcnemar_p", "accepted"])
            wr.writerow([a.step, a.specs[0], a.specs[1], s["n"], round(b1, 2), round(n1, 2), round(n3, 2),
                         round(s["delta"], 2), round(s["lo"], 2), round(s["hi"], 2), f"{s['p']:.3g}", accepted])


if __name__ == "__main__":
    main()
