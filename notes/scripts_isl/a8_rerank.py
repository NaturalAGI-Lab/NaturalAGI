"""A8 — soma readout variants of the structural (ComAN) path, re-ranked offline from pl_dump dumps (no new live runs).

Every dump row keeps, for every concept, its similarity `sim`, concept complexity `cc` and image complexity `ic`.
Variants (pre-registered; none uses other classes' images — Axiom 3):
  base        sim + 0.10·log2(cc)              the deployed rule (λ = 0.10 was tuned on the full MNIST test — disclosed)
  lam0        sim                              λ removed
  cov{α}      sim · min(cc/ic, 1)^α            coverage as feedforward inhibition (α ∈ {0.5, 1})
  self        (sim − μ_c) / σ_c                μ_c, σ_c = the concept's own similarity on its OWN class's training
                                               positives (intrinsic plasticity, Desai 1999), from a dump of the training set
Usage: a8_rerank.py <dev dump.jsonl> [--positives <dump of the training images laid out as <concept_id>/<file>.png>]
"""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


def rows(path):
    return [json.loads(line) for line in open(path)]


def score(entry, variant, stats=None):
    sim, cc, ic = entry["sim"] or 0.0, max(entry["cc"] or 1, 1), max(entry["ic"] or 1, 1)
    if variant == "base":
        return sim + 0.10 * math.log2(cc)
    if variant == "lam0":
        return sim
    if variant.startswith("cov"):
        return sim * min(cc / ic, 1.0) ** float(variant[3:])
    if variant.startswith("self"):
        base = sim + (0.10 * math.log2(cc) if variant == "self_lam" else 0.0)
        mu, sd = stats.get(entry["cid"], (None, None))
        return (base - mu) / sd if mu is not None else -1e9
    raise KeyError(variant)


def own_positive_stats(train_rows, variant):
    """μ, σ of each concept's score on its own training images (directory name = concept id)."""
    per = defaultdict(list)
    for r in train_rows:
        own = Path(r["path"]).parent.name
        for e in r["ranked"]:
            if e["minor"] and e["cid"] == own:
                base = e["sim"] + (0.10 * math.log2(max(e["cc"] or 1, 1)) if variant == "self_lam" else 0.0)
                per[e["cid"]].append(base)
    return {c: (float(np.mean(v)), max(float(np.std(v)), 1e-3)) for c, v in per.items() if len(v) >= 3}


def evaluate(dev, variant, stats=None):
    correct, preds = 0, []
    for r in dev:
        cands = [e for e in r["ranked"] if e["minor"]]
        if not cands:
            preds.append("none")
            continue
        best = max(cands, key=lambda e: score(e, variant, stats))
        preds.append(best["c"])
        correct += best["c"] == r["true"]
    return 100.0 * correct / len(dev), preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dev")
    ap.add_argument("--positives")
    a = ap.parse_args()
    dev = rows(a.dev)
    variants = ["base", "lam0", "cov0.5", "cov1"]
    stats = {}
    if a.positives:
        train = rows(a.positives)
        for v in ("self", "self_lam"):
            stats[v] = own_positive_stats(train, v)
            variants.append(v)
    base_acc, base_pred = evaluate(dev, "base")
    for v in variants:
        acc, pred = evaluate(dev, v, stats.get(v))
        flips = sum(p != q for p, q in zip(pred, base_pred))
        print(f"{v:<10} top-1 {acc:6.2f}   Δ vs base {acc - base_acc:+6.2f}   changed answers {flips}")


if __name__ == "__main__":
    main()
