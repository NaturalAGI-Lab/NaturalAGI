"""Write an experiments/run_* folder in the layout of the pipeline's run folders (metrics.csv, per_class_metrics.csv,
incorrect_results.csv, confusion_matrix.png, run_config.json, findings.md [, concept_graphs.json]) from an official-test
dump of the ISL models (rows with stem / true / pred / top3), plus the numbers behind the picture: confusion_matrix.csv
(rows expected, columns predicted, "none" = no answer) and top_confusions.csv (the most frequent expected → predicted
errors).

MNIST: the benchmark is the curated `complete` subset of the official test (datasets/mnist_all_manifest.csv), as in
Nikita's runs: metrics.csv / per_class_metrics.csv / confusion_matrix.* are on `complete`; the *_all10000 files on all
10 000 test images. EMNIST (--dataset emnist): all 20 800 official test images. Precision / Recall / F1 are macro
averages over the classes; recall of a class = its accuracy; an image without an answer counts as an error (Nikita's
runs dropped such images — "Failed (DLQ)" — from the denominator).
Usage: make_run_folder.py <dump.jsonl> <out dir> --config <json> --findings <md> [--concepts <json>] [--dataset emnist]
"""
import argparse
import csv
import json
import shutil
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
MANIFEST = {r["image_path"].split("/")[-1][:-4]: r["structure"]
            for r in csv.DictReader(open(REPO / "datasets" / "mnist_all_manifest.csv"))}


def scores(rows):
    classes = sorted({r["true"] for r in rows})
    tp = Counter(r["true"] for r in rows if r["pred"] == r["true"])
    pred_n = Counter(r["pred"] for r in rows)
    true_n = Counter(r["true"] for r in rows)
    top3_n = Counter(r["true"] for r in rows if r["true"] in (r.get("top3") or [r["pred"]]))
    per = []
    for c in classes:
        p = 100.0 * tp[c] / pred_n[c] if pred_n[c] else 0.0
        r = 100.0 * tp[c] / true_n[c]
        per.append((c, p, r, 2 * p * r / (p + r) if p + r else 0.0, true_n[c], 100.0 * top3_n[c] / true_n[c]))
    failed = sum(1 for r in rows if r["pred"] in (None, "", "none"))
    n = len(rows)
    summary = [("Total Images", float(n)), ("Failed (no answer)", float(failed)),
               ("Successfully Classified", float(n - failed)), ("Success Rate (%)", 100.0 * (n - failed) / n),
               ("Accuracy (%)", 100.0 * sum(tp.values()) / n),
               ("Precision (%)", float(np.mean([x[1] for x in per]))), ("Recall (%)", float(np.mean([x[2] for x in per]))),
               ("F1 Score (%)", float(np.mean([x[3] for x in per]))),
               ("Top-3 Accuracy (%)", 100.0 * sum(r["true"] in (r.get("top3") or [r["pred"]]) for r in rows) / n)]
    return summary, per, classes


def write(out, tag, rows, title):
    summary, per, classes = scores(rows)
    with open(out / f"metrics{tag}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Metric", "Value"])
        w.writerows(summary)
    with open(out / f"per_class_metrics{tag}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["class", "precision", "recall", "f1_score", "support", "top3_accuracy"])
        w.writerows(per)
    idx = {c: i for i, c in enumerate(classes)}
    m = np.zeros((len(classes), len(classes) + 1), dtype=int)  # last column: no answer
    for r in rows:
        m[idx[r["true"]], idx.get(r["pred"], len(classes))] += 1
    with open(out / f"confusion_matrix{tag}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["expected \\ predicted", *classes, "none"])
        w.writerows([c, *m[i]] for i, c in enumerate(classes))
    errors = sorted(((m[i, j], c, (classes + ["none"])[j]) for i, c in enumerate(classes)
                     for j in range(len(classes) + 1) if j != i and m[i, j]), reverse=True)
    with open(out / f"top_confusions{tag}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["expected", "predicted", "count", "share_of_class_%", "share_of_errors_%"])
        w.writerows((t, p, k, round(100.0 * k / m[idx[t]].sum(), 2), round(100.0 * k / sum(e[0] for e in errors), 2))
                    for k, t, p in errors[:40])
    m = m[:, :len(classes)]
    big = len(classes) > 10
    fig, ax = plt.subplots(figsize=(13, 11) if big else (7, 6))
    ax.imshow(m, cmap="Blues")
    for i in range(len(classes)):
        for j in range(len(classes)):
            if m[i, j] or not big:
                ax.text(j, i, m[i, j], ha="center", va="center", fontsize=7,
                        color="white" if m[i, j] > m.max() / 2 else "black")
    ax.set_xticks(range(len(classes)), classes), ax.set_yticks(range(len(classes)), classes)
    ax.set_xlabel("predicted"), ax.set_ylabel("expected")
    ax.set_title(f"Confusion matrix — {title} (n = {len(rows)})")
    fig.tight_layout()
    fig.savefig(out / f"confusion_matrix{tag}.png", dpi=120)
    plt.close(fig)
    return dict(summary)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("out")
    ap.add_argument("--config", required=True)
    ap.add_argument("--findings", required=True)
    ap.add_argument("--concepts")
    ap.add_argument("--dataset", choices=("mnist", "emnist"), default="mnist")
    a = ap.parse_args()
    rows = [json.loads(line) for line in open(a.dump)]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.dataset == "emnist":
        main_m = all_m = write(out, "", rows, "EMNIST-letters official test")
    else:
        main_m = write(out, "", [r for r in rows if MANIFEST.get(r["stem"]) == "complete"], "complete")
        all_m = write(out, "_all10000", rows, "all10000")
    root = "tests/emnist_testfull" if a.dataset == "emnist" else "tests/mnist_all"
    with open(out / "incorrect_results.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["stem", "image_path", "subset", "expected", "predicted", "top3", "correct"])
        for r in rows:
            if r["pred"] != r["true"]:
                w.writerow([r["stem"], f"{root}/{r['true']}/{r['stem']}.png", MANIFEST.get(r["stem"], ""),
                            r["true"], r["pred"], " ".join(r.get("top3") or []), False])
    shutil.copy(a.config, out / "run_config.json")
    shutil.copy(a.findings, out / "findings.md")
    if a.concepts:
        shutil.copy(a.concepts, out / "concept_graphs.json")
    print(f"{out}: main {main_m['Accuracy (%)']:.2f} (F1 {main_m['F1 Score (%)']:.2f}); all {all_m['Accuracy (%)']:.2f}")


if __name__ == "__main__":
    main()
