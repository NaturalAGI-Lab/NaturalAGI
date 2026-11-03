"""Confusion analysis of a band model on the kept full-test direction maps (production scorer, no pipeline run).
Usage: pl_band_confusion.py <model_id> [session]   -> prints the summary, writes tests/_fewshot_ref/confusion_<model>.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src" / "classification"))
from band.band_repository import load_band_models  # noqa: E402
from band.band_scorer import score_letters  # noqa: E402
from neo4j import GraphDatabase  # noqa: E402

L = [chr(65 + i) for i in range(26)]


def main():
    name = sys.argv[1]
    sid = sys.argv[2] if len(sys.argv) > 2 else "fs-test-full"
    drv = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "111122223333"))
    model = load_band_models(drv)[name]
    with drv.session() as s:
        rows = s.run("MATCH (f:GraphFeatures {session_id:$sid}) RETURN f.image_path AS p, f.dm AS dm", sid=sid).data()
    drv.close()
    C = np.zeros((26, 26), int)
    rank_of_truth, margins, win_form = [], [], Counter()
    for r in rows:
        t = r["p"].split("/")[-2].upper()
        x = np.array(r["dm"], float)
        ranked = score_letters(x, model)
        letters = [ls.letter for ls in ranked]
        C[L.index(t), L.index(letters[0])] += 1
        rk = letters.index(t)
        rank_of_truth.append(rk)
        if rk > 0:
            margins.append((ranked[rk].score - ranked[0].score) / max(ranked[0].score, 1e-9))
            win_form[(ranked[0].form[0], ranked[rk].form[0])] += 1
    n = C.sum(); err = n - np.trace(C)
    print(f"{name}: {n} images, top-1 {100*np.trace(C)/n:.2f}%, errors {err}")
    rk = np.array(rank_of_truth)
    print(f"truth rank among 26:  1st {100*(rk==0).mean():.1f}%  2nd {100*(rk==1).mean():.1f}%  3rd {100*(rk==2).mean():.1f}%  4-5th {100*((rk>=3)&(rk<=4)).mean():.1f}%  6th+ {100*(rk>=5).mean():.1f}%")
    m = np.array(margins)
    print(f"errors: truth loses by <5%: {100*(m<0.05).mean():.1f}%  <10%: {100*(m<0.10).mean():.1f}%  <20%: {100*(m<0.20).mean():.1f}%  (relative score gap to the winner)")
    rec = C.diagonal() / C.sum(1); prec = C.diagonal() / np.maximum(C.sum(0), 1)
    print("\nrecall (worst first):   " + "  ".join(f"{L[i]} {100*rec[i]:.0f}" for i in np.argsort(rec)))
    print("precision (worst first): " + "  ".join(f"{L[i]} {100*prec[i]:.0f}" for i in np.argsort(prec)))
    print("answers given per letter (800 expected): " + "  ".join(f"{L[i]} {C[:, i].sum()}" for i in np.argsort(-C.sum(0))[:8]) + "  ...  " + "  ".join(f"{L[i]} {C[:, i].sum()}" for i in np.argsort(C.sum(0))[:5]))
    pairs = sorted(((C[i, j] + C[j, i], L[i], L[j], C[i, j], C[j, i]) for i in range(26) for j in range(i + 1, 26)), reverse=True)
    print("\ntop confusion pairs (both directions):")
    cum = 0
    for k, (tot, a, b, ab, ba) in enumerate(pairs[:20]):
        cum += tot
        print(f"  {a}<->{b}: {tot:4d} ({100*tot/err:4.1f}% of errors, cum {100*cum/err:4.1f}%)   {a}->{b} {ab}, {b}->{a} {ba}")
    print(f"pairs needed for 50% of errors: {next(k+1 for k in range(len(pairs)) if sum(p[0] for p in pairs[:k+1]) >= err/2)} of 325")
    per_letter_err = sorted(((C[i].sum() - C[i, i], L[i]) for i in range(26)), reverse=True)
    print("errors by true letter: " + "  ".join(f"{l} {e}" for e, l in per_letter_err))
    tot = max(sum(win_form.values()), 1)
    print("errors by (form of the winning wrong leaf, form of the nearest own leaf): " + "  ".join(f"{w}/{o} {100*v/tot:.1f}%" for (w, o), v in sorted(win_form.items(), key=lambda kv: -kv[1])) + "   (l = lowercase, u = uppercase)")
    json.dump({"letters": L, "matrix": C.tolist()}, open(REPO / "tests" / "_fewshot_ref" / f"confusion_{name}.json", "w"))


if __name__ == "__main__":
    main()
