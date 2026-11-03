"""Artefacts of the few-shot report (experiments/fewshot_band_concepts_2026-10/) from the evaluation dumps.

Inputs (written by pl_dump.py, tests/ is not in git):
  tests/_fewshot_ref/final_emnist.jsonl     final system, full EMNIST-letters test (20 800)
  tests/_fewshot_ref/baseline_emnist.jsonl  structural baseline (fold concepts + direct_bridge + calibration), same test
  tests/_fewshot_ref/final_mnist.jsonl      final system, MNIST complete-only test (8 708)
  experiments/run_20260630_235356/          GED baseline on MNIST (Nikita): per_class_metrics.csv + incorrect_results.csv
and, for the ablation of the decision rounds, the kept per-image features in Neo4j (sessions final-emnist / final-mnist).

Outputs: metrics.csv, per_class_*.csv, confusion_*.csv, confusion_*.png, ablation.csv, and markdown snippets on stdout.
Usage: pl_report.py [--no-ablation]
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
REF = REPO / "tests" / "_fewshot_ref"
OUT = REPO / "experiments" / "fewshot_band_concepts_2026-10"
NIKITA = REPO / "experiments" / "run_20260630_235356"
LETTERS = [chr(65 + i) for i in range(26)]
DIGITS = [str(i) for i in range(10)]
NONE = "∅"


def load_dump(path):
    rows = [json.loads(line) for line in open(path)]
    out = []
    for r in rows:
        letters = []
        for x in r.get("ranked") or []:
            if x["c"] not in letters:
                letters.append(x["c"])
        ok = r["status"] == "success"
        pred = r["pred"] if ok and r.get("pred") not in (None, "none") else NONE      # pl_dump's own decision
        out.append({"true": r["true"], "pred": pred, "top3": letters[:3], "failed": not ok})
    return out


def summary(rows, classes, merge_il=False):
    n = len(rows)
    processed = sum(not r["failed"] for r in rows)       # images the pipeline did not drop (DLQ)
    top1 = sum(r["pred"] == r["true"] for r in rows)
    out = {"n": n, "processed": processed, "top1": 100 * top1 / n,
           "top1_processed": 100 * top1 / max(processed, 1)}
    out["top3"] = None if rows[0]["top3"] is None else 100 * sum(r["true"] in r["top3"] for r in rows) / n
    if merge_il:
        out["top1_IL_merged"] = 100 * sum(r["pred"] == r["true"] or {r["pred"], r["true"]} == {"I", "L"} for r in rows) / n
    return out


def confusion(rows, classes):
    cols = classes + ([NONE] if any(r["pred"] == NONE for r in rows) else [])
    m = np.zeros((len(classes), len(cols)), int)
    for r in rows:
        m[classes.index(r["true"]), cols.index(r["pred"] if r["pred"] in cols else NONE)] += 1
    return m, cols


def per_class(m, classes):
    out = []
    for i, c in enumerate(classes):
        tp = m[i, i]; support = m[i].sum(); predicted = m[:, i].sum()
        p = 100 * tp / predicted if predicted else 0.0; rc = 100 * tp / support if support else 0.0
        out.append({"class": c, "support": int(support), "precision": round(p, 2), "recall": round(rc, 2),
                    "f1": round(2 * p * rc / (p + rc), 2) if p + rc else 0.0})
    return out


def nikita_mnist():
    """GED baseline on MNIST complete (run_20260630_235356): rows rebuilt from the per-class support and the
    list of wrong answers (DLQ / not-classified images count as unanswered)."""
    support = {r["class"]: int(r["support"]) for r in csv.DictReader(open(NIKITA / "per_class_metrics.csv"))}
    wrong, dlq = Counter(), Counter()                  # support = answered images; DLQ images come on top
    for r in csv.DictReader(open(NIKITA / "incorrect_results.csv")):
        if r["status"] != "success":
            dlq[r["expected"]] += 1
            continue
        wrong[(r["expected"], r["predicted"] if r["predicted"] in DIGITS else NONE)] += 1
    rows = []
    for c in DIGITS:
        n_wrong = sum(v for (t, _), v in wrong.items() if t == c)
        rows += [{"true": c, "pred": c, "top3": None, "failed": False}] * (support[c] - n_wrong)
        for (t, p), v in wrong.items():
            if t == c:
                rows += [{"true": c, "pred": p, "top3": None, "failed": False}] * v
        rows += [{"true": c, "pred": NONE, "top3": None, "failed": True}] * dlq[c]
    return rows


def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0].keys())
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def plot(m, rows_labels, cols, title, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    share = m / np.maximum(m.sum(1, keepdims=True), 1)            # row-normalised: share of the true class
    big = len(rows_labels) > 12
    fig, ax = plt.subplots(figsize=(13, 11.5) if big else (7.5, 6.5), dpi=130)
    im = ax.imshow(share, cmap="Blues", vmin=0, vmax=1)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m[i, j]
            if v == 0 or (big and i != j and v < 10):
                continue
            ax.text(j, i, str(v), ha="center", va="center", fontsize=6.5 if big else 9,
                    color="white" if share[i, j] > 0.55 else "#1f2933")
    ax.set_xticks(range(len(cols)), cols, fontsize=8 if big else 10)
    ax.set_yticks(range(len(rows_labels)), rows_labels, fontsize=8 if big else 10)
    ax.set_xlabel("відповідь системи" + (" (∅ = без відповіді)" if NONE in cols else ""))
    ax.set_ylabel("правильний клас")
    ax.set_title(title, fontsize=11, loc="left")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("частка правильного класу (рядок)", fontsize=9)
    cb.outline.set_visible(False)
    if big:
        fig.text(0.01, 0.005, "числа: кількість зображень; поза діагоналлю показано клітинки з ≥ 10", fontsize=8, color="#52606d")
    fig.tight_layout()
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def md_matrix(m, rows_labels, cols):
    head = "| | " + " | ".join(cols) + " |\n|" + "---|" * (len(cols) + 1) + "\n"
    body = "".join(f"| **{r}** | " + " | ".join(f"**{v}**" if i == j else (str(v) if v else "·") for j, v in enumerate(m[i])) + " |\n"
                   for i, r in enumerate(rows_labels))
    return head + body


def top_pairs(m, classes, k=12):
    pairs = []
    for i in range(len(classes)):
        for j in range(i + 1, len(classes)):
            pairs.append((m[i, j] + m[j, i], classes[i], classes[j], m[i, j], m[j, i]))
    pairs.sort(reverse=True)
    errors = m.sum() - np.trace(m[:, :len(classes)])
    return [(a, b, tot, ab, ba, 100 * tot / max(errors, 1)) for tot, a, b, ab, ba in pairs[:k]]


def ablation():
    """Decision rounds switched on one by one, production code on the kept features of the final runs."""
    sys.path.insert(0, str(REPO / "src" / "classification"))
    from band.band_repository import load_band_models
    from band.band_scorer import score_letters_committee
    from band.shape_context import rerank
    from neo4j import GraphDatabase

    d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "111122223333"))
    models = load_band_models(d)
    out = []
    for dataset, model_id, session in (("EMNIST", "fs_final_B10", "final-emnist"), ("MNIST", "mn_final", "final-mnist")):
        m = models[model_id]
        with d.session() as s:
            rows = s.run("MATCH (f:GraphFeatures {session_id:$s}) RETURN f.image_path AS p, f.dm AS dm, f.dm_alt AS alt, "
                         "f.sp AS sp, f.st AS st", s=session).data()
        lam = m.stage2_lambda
        hits = Counter()
        for r in rows:
            t = r["p"].split("/")[-2]
            dim = len(r["dm"])
            xs = [np.array(r["dm"], float)] + (list(np.array(r["alt"], float).reshape(-1, dim)) if r["alt"] else [])
            sp = np.array(r["sp"], np.float32).reshape(-1, 2) if r["sp"] else None
            st = np.array(r["st"], np.float32).reshape(-1, 2) if r["st"] else None
            for name, maps, stage2 in (("round 1 only, one skeleton", xs[:1], False),
                                       ("round 1, committee of 3 skeletons", xs, False),
                                       ("round 1 (one skeleton) + round 2", xs[:1], True),
                                       ("round 1 (committee) + round 2 = final", xs, True)):
                ranked = score_letters_committee(maps, m)
                if stage2:
                    m.stage2_lambda = lam
                    ranked = rerank(m, ranked, sp, st)
                hits[(name, 1)] += ranked[0].letter == t
                hits[(name, 3)] += t in [x.letter for x in ranked[:3]]
        for name in ("round 1 only, one skeleton", "round 1, committee of 3 skeletons",
                     "round 1 (one skeleton) + round 2", "round 1 (committee) + round 2 = final"):
            out.append({"dataset": dataset, "configuration": name, "images": len(rows),
                        "top1": round(100 * hits[(name, 1)] / len(rows), 2), "top3": round(100 * hits[(name, 3)] / len(rows), 2)})
    d.close()
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    runs = {
        ("EMNIST", "baseline: fold concepts + direct_bridge + calibration"): (load_dump(REF / "baseline_emnist.jsonl"), LETTERS),
        ("EMNIST", "final: band concepts + shape concepts"): (load_dump(REF / "final_emnist.jsonl"), LETTERS),
        ("MNIST", "baseline: fold concepts + GED (run_20260630_235356)"): (nikita_mnist(), DIGITS),
        ("MNIST", "final: band concepts + shape concepts"): (load_dump(REF / "final_mnist.jsonl"), DIGITS),
    }
    metrics = []
    for (dataset, system), (rows, classes) in runs.items():
        s = summary(rows, classes, merge_il=dataset == "EMNIST")
        metrics.append({"dataset": dataset, "system": system, **{k: round(v, 2) if isinstance(v, float) else v for k, v in s.items()}})
    write_csv(OUT / "metrics.csv", metrics, ["dataset", "system", "n", "processed", "top1", "top1_processed", "top3", "top1_IL_merged"])
    print("## metrics"); [print(r) for r in metrics]

    for dataset, classes in (("emnist", LETTERS), ("mnist", DIGITS)):
        tables = {}
        for (ds, system), (rows, cls) in runs.items():
            if ds.lower() != dataset:
                continue
            tag = "baseline" if system.startswith("baseline") else "final"
            m, cols = confusion(rows, cls)
            tables[tag] = (m, cols)
            with open(OUT / f"confusion_{dataset}_{tag}.csv", "w", newline="") as fh:
                w = csv.writer(fh); w.writerow(["true \\ predicted"] + cols); [w.writerow([c] + list(m[i])) for i, c in enumerate(cls)]
            acc = 100 * np.trace(m[:, :len(cls)]) / m.sum()
            label = {"emnist": "EMNIST-letters, 26 класів", "mnist": "MNIST complete, 10 класів"}[dataset]
            what = "до: fold-концепти + структурне порівняння" if tag == "baseline" else "після: смугові концепти + концепти форми"
            plot(m, cls, cols, f"{label}\n{what}: top-1 {acc:.1f} %, n = {m.sum()}", OUT / f"confusion_{dataset}_{tag}.png")
            print(f"\n## confusion {dataset} {tag}\n" + md_matrix(m, cls, cols))
            print(f"### top pairs {dataset} {tag}")
            for a, b, tot, ab, ba, share in top_pairs(m, cls):
                print(f"| {a}↔{b} | {tot} | {share:.1f} % | {a}→{b} {ab}, {b}→{a} {ba} |")
        pc = []
        for tag, (m, cols) in tables.items():
            for r in per_class(m, classes):
                pc.append({"system": tag, **r})
        write_csv(OUT / f"per_class_{dataset}.csv", pc)
        print(f"\n## per class {dataset} (recall baseline -> final)")
        b = {r["class"]: r for r in pc if r["system"] == "baseline"}; f = {r["class"]: r for r in pc if r["system"] == "final"}
        print("| клас | recall до | recall після | precision до | precision після |\n|---|---|---|---|---|")
        for c in classes:
            print(f"| {c} | {b[c]['recall']:.1f} | {f[c]['recall']:.1f} | {b[c]['precision']:.1f} | {f[c]['precision']:.1f} |")

    if "--no-ablation" not in sys.argv:
        ab = ablation()
        write_csv(OUT / "ablation.csv", ab)
        print("\n## ablation"); [print(r) for r in ab]


if __name__ == "__main__":
    main()
