"""One row for the external EMNIST baseline table (regime | model | budget | train n | top-1 | top-3 | Precision |
Recall | F1 | params | train (s) | infer (ms/img) | worst classes) from an official-test dump of the ISL models.

Precision / Recall / F1 are macro averages over the 26 letters (as sklearn `average='macro'`); worst classes = the three
lowest per-class recalls. With --time, the configuration is retrained on the training set (train time, single process)
and evaluated on --time-n test images in one process (inference ms / image); params = the elements the trained map
stores: attractor synapses of the competing neurons (+ two band ends per dimension of the parametric layer, if any).
Usage: emnist_table_row.py <dump.jsonl> [--model NAME] [--time --cfg <json file with the isl_sim cfg> --train ecand60:10]
"""
import argparse
import json
import time
from collections import Counter

import numpy as np


def metrics(rows):
    classes = sorted({r["true"] for r in rows})
    tp = Counter(r["true"] for r in rows if r["pred"] == r["true"])
    pred_n = Counter(r["pred"] for r in rows)
    true_n = Counter(r["true"] for r in rows)
    prec = [tp[c] / pred_n[c] if pred_n[c] else 0.0 for c in classes]
    rec = [tp[c] / true_n[c] for c in classes]
    f1 = [2 * p * r / (p + r) if p + r else 0.0 for p, r in zip(prec, rec)]
    worst = [c for _, c in sorted(zip(rec, classes))[:3]]
    n = len(rows)
    return {"top1": 100.0 * sum(tp.values()) / n, "top3": 100.0 * sum(r["true"] in r["top3"] for r in rows) / n,
            "precision": 100.0 * np.mean(prec), "recall": 100.0 * np.mean(rec), "f1": 100.0 * np.mean(f1),
            "worst": " ".join(worst), "n": n}


def timing(cfg, train_split, n_test):
    import isl_sim as S
    split, _, lim = train_split.partition(":")
    tr = S.load(split, cfg["train_channels"], int(lim) if lim else None)
    t0 = time.time()
    stimuli = S.build_stimuli(tr, cfg)
    neurons = S.train(stimuli, cfg, 0)
    train_s = time.time() - t0
    test = [it for it in S.load("etest", cfg["channels"]) if it["aug"] == 0][:n_test]
    t0 = time.time()
    S.evaluate(neurons, test, {**cfg, "workers": 1})
    infer_ms = 1000.0 * (time.time() - t0) / len(test)
    comp = [nr for nr in neurons if len(nr.families) >= cfg.get("min_originals", 1)]
    params = sum(len(nr.att) for nr in comp) + sum(2 * len(getattr(nr, "bands", {}) or {}) for nr in comp)
    return {"train_n": len({(i["cls"], i["family"]) for i in tr}), "train_s": train_s, "infer_ms": infer_ms,
            "params": params, "neurons": len(comp)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--model", default="ISL (ours)")
    ap.add_argument("--time", action="store_true")
    ap.add_argument("--cfg")
    ap.add_argument("--train", default="ecand60:10")
    ap.add_argument("--time-n", type=int, default=1000)
    a = ap.parse_args()
    m = metrics([json.loads(line) for line in open(a.dump)])
    t = timing(json.load(open(a.cfg)), a.train, a.time_n) if a.time else {}
    print(f"| fewshot | {a.model} | single_fit | {t.get('train_n', 260)} | {m['top1']:.2f} | {m['top3']:.2f} | "
          f"{m['precision']:.2f} | {m['recall']:.2f} | {m['f1']:.2f} | {t.get('params', '—')} | "
          f"{t.get('train_s', float('nan')):.1f} | {t.get('infer_ms', float('nan')):.3f} | {m['worst']} |")
    if t:
        print(f"(params = attractor synapses of {t['neurons']} competing neurons; no trained weights)")


if __name__ == "__main__":
    main()
