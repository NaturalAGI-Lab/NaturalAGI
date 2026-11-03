"""O1 — EMNIST-letters with the Section IV projection model in its compliant form (every competing neuron rests on
>= 2 originals) and his point 3 ('distinct' competition). Pre-registration: lab_log.md, section O.

  grid   10 originals per letter, edev, 1 order: rho 0.5 / 0.6 / 0.7 x competition argmax / distinct (tau 0.8, consolidation)
  then   the selected configuration: official test (etest) once; its competing neurons -> ComAN subclasses
         (tests/_isl/emnist_groups_10.json, used by O2); the same configuration with 60 per letter: edev + etest once
Usage: isl_emnist_o.py [--workers 4]
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

import isl_sim as S
import isl_projection_n as PN

ISL = S.REPO / "tests" / "_isl"
PN.CSV = S.REPO / "experiments" / "isl_transfer_2026-10" / "results_O.csv"


def test_once(tag, cfg, stimuli, workers):
    S._ACT_CACHE.clear()
    neurons = S.train(stimuli, cfg, 0)
    test = [it for it in S.load("etest", cfg["channels"]) if it["aug"] == 0]
    rows = S.evaluate_parallel(neurons, test, {**cfg, "workers": workers}, workers)
    with open(ISL / f"O_{tag}_etest.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps({"config": tag, **r}) + "\n")
    n = len(rows)
    t1 = 100.0 * sum(r["pred"] == r["true"] for r in rows) / n
    t3 = 100.0 * sum(r["true"] in r["top3"] for r in rows) / n
    il = 100.0 * sum(r["pred"] == r["true"] or {r["pred"], r["true"]} == {"I", "L"} for r in rows) / n
    per = {c: 100.0 * np.mean([r["pred"] == c for r in rows if r["true"] == c]) for c in sorted({r["true"] for r in rows})}
    conf = Counter(f"{r['true']}→{r['pred']}" for r in rows if r["pred"] != r["true"]).most_common(8)
    comp = [n for n in neurons if len(n.families) >= cfg.get("min_originals", 1)]
    sizes = [len(n.families) for n in comp]
    print(f"TEST {tag}: n {n}  top-1 {t1:.2f}  top-3 {t3:.2f}  (I+L as one class {il:.2f})", flush=True)
    print(f"TEST {tag} per letter: " + ", ".join(f"{c} {v:.0f}" for c, v in per.items()), flush=True)
    print(f"TEST {tag} confusions: " + ", ".join(f"{k} {v}" for k, v in conf), flush=True)
    print(f"TEST {tag} competing neurons {len(comp)} of {len(neurons)}, originals per neuron min {min(sizes)} "
          f"median {int(np.median(sizes))}, share of originals inside them "
          f"{100.0 * sum(sizes) / sum(len(n.families) for n in neurons):.1f} %", flush=True)
    return neurons, comp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    base = {**S.DEFAULT, **S.IMPROVEMENTS["best2"], "tau": 0.8, "min_originals": 2, "workers": 1}
    tr = S.load("ecand60", base["train_channels"], 10)
    dev = [it for it in S.load("edev", base["channels"]) if it["aug"] == 0]
    print(f"train ecand60:10: {len({(i['cls'], i['family']) for i in tr})} originals; edev {len(dev)}", flush=True)
    stimuli = S.build_stimuli(tr, base)
    cands = {}
    for rho in (0.5, 0.6, 0.7):
        for comp in ("argmax", "distinct"):
            cfg = {**base, "rho": rho, **({"competition": comp} if comp != "argmax" else {})}
            name = f"O1 10/letter rho{rho} {comp}"
            cands[name] = (cfg, PN.run_cfg(name, cfg, stimuli, dev, (0,))[0])
    sel = max(cands, key=lambda k: cands[k][1]["top1"])
    scfg = cands[sel][0]
    print(f"SELECTED (pre-registered rule): {sel} — edev {cands[sel][1]['top1']}", flush=True)
    (ISL / "O_selected.json").write_text(json.dumps({"selected": sel, "edev": cands[sel][1]}, indent=1))

    neurons, comp = test_once("10", scfg, stimuli, a.workers)
    groups, k = {}, Counter()
    for n in comp:                                     # ComAN subclasses for O2: the consolidated neurons
        k[n.cls] += 1
        groups[f"{n.cls}_{k[n.cls]}"] = sorted(fam for _, fam in n.members)
    (ISL / "emnist_groups_10.json").write_text(json.dumps(groups, indent=1))
    print(f"groups for ComAN: {len(groups)} over {len(k)} letters (letters without a group: "
          f"{sorted(set(r['cls'] for r in tr) - set(k))})", flush=True)

    S._LOADED.clear(), S._ACT_CACHE.clear()
    tr60 = S.load("ecand60", base["train_channels"], 60)
    stim60 = S.build_stimuli(tr60, scfg)
    PN.run_cfg(f"O1 60/letter [{sel}]", scfg, stim60, dev, (0,))
    test_once("60", scfg, stim60, a.workers)


if __name__ == "__main__":
    main()
