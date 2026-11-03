"""P-projection — Section IV ideas on top of the N-projection selection (pre-registration: lab_log.md section P,
variants restated in experiments/isl_transfer_2026-10/lab_P_projection.md).

  dev      base, P3a runs, P3b comanfeat, P6 distinct_iter / distinct_iter_free / distinct_pool, P7 fixations 1 / 2 / 3,
           then the combination of the accepted ones (3 orders each; paired test on order 0 vs the base)
  final    the final configuration: P1 dumps on dev and on the official test (mtest), the official test report
  emnist   (only if the final differs from the base) the final with 10 originals per letter: edev + etest once
  p4       the base trained on 60 originals per digit: dev + mtest once
  p10      the final trained on the first 10 originals per digit: dev + mtest once (lab log P9)
Usage: isl_projection_p.py dev|final|emnist|p4|p10 [--workers 3]
"""
import argparse
import csv
import json
import math
import time
from collections import Counter
from pathlib import Path

import numpy as np

import isl_sim as S
import isl_projection_n as PN

EXP = S.REPO / "experiments" / "isl_transfer_2026-10"
ISL = S.REPO / "tests" / "_isl"
CSV = EXP / "results_P_projection.csv"
STATE = ISL / "P_projection_state.json"
MANIFEST = {r["image_path"].split("/")[-1][:-4]: r["structure"]
            for r in csv.DictReader(open(S.REPO / "datasets" / "mnist_all_manifest.csv"))}
BASE = {**S.DEFAULT, **S.IMPROVEMENTS["best2"], "workers": 1, "tau": 0.8, "rho": 0.6, "min_originals": 2,
        "competition": "distinct"}
VARIANTS = {   # name -> cfg changes on top of the base (pre-declared in lab_P_projection.md)
    "P3a runs": {"runs": True},
    "P3b comanfeat": {"comanfeat": True},
    "P6i distinct_iter": {"competition": "distinct_iter"},
    "P6i' distinct_iter_free": {"competition": "distinct_iter_free"},
    "P6ii distinct_pool": {"competition": "distinct_pool"},
    "P7 fixations 1": {"fixations": 1},
    "P7 fixations 2": {"fixations": 2},
    "P7 fixations 3": {"fixations": 3},
}
ACT_KEYS = ("runs", "comanfeat", "fixations")


def paired(base_rows, rows):
    a = {r["stem"]: r["pred"] == r["true"] for r in base_rows}
    b = {r["stem"]: r["pred"] == r["true"] for r in rows}
    keys = sorted(a.keys() & b.keys())
    d = np.array([int(b[k]) - int(a[k]) for k in keys])
    half = 1.96 * d.std(ddof=1) / math.sqrt(len(d)) if d.any() else 0.0
    p, _, _ = S.mcnemar([a[k] for k in keys], [b[k] for k in keys])
    return 100 * d.mean(), 100 * (d.mean() - half), 100 * (d.mean() + half), p


def run(name, cfg, stimuli, dev, orders, base_rows=None):
    t0 = time.time()
    res = []
    for seed in orders:
        neurons = S.train(stimuli, cfg, seed)
        rows = S.evaluate(neurons, dev, cfg)
        res.append((S.summarise(rows, neurons)["top1"], S.summarise(rows, neurons)["top3"],
                    PN.census(neurons, cfg.get("min_originals", 1)), rows))
    top1 = [r[0] for r in res]
    out = {"config": name, "orders": len(orders), "top1": round(float(np.mean(top1)), 2),
           "top1_sd": round(float(np.std(top1)), 2), "top3": round(float(np.mean([r[1] for r in res])), 2),
           **{k: round(float(np.mean([r[2][k] for r in res])), 1) for k in ("neurons", "competing", "orig_in_competing")},
           "min_orig_competing": min(r[2]["min_orig_competing"] for r in res)}
    if base_rows is not None:
        dl, lo, hi, p = paired(base_rows, res[0][3])
        out.update({"delta_o0": round(dl, 2), "ci_lo": round(lo, 2), "ci_hi": round(hi, 2), "mcnemar_p": f"{p:.2g}",
                    "accepted": lo > -1.0})
    out["secs"] = round(time.time() - t0, 1)
    print(f"{name:<32} top1 {out['top1']:6.2f} ±{out['top1_sd']:<5} top3 {out['top3']:6.2f} competing "
          f"{out['competing']:5.1f} ({out['orig_in_competing']} %, min {out['min_orig_competing']})"
          + (f"  Δ(o0) {out['delta_o0']:+.2f} [{out['ci_lo']:+.2f}, {out['ci_hi']:+.2f}] p {out['mcnemar_p']} "
             f"{'ACCEPT' if out['accepted'] else 'reject'}" if base_rows is not None else "") + f"  {out['secs']}s",
          flush=True)
    first = not CSV.exists()
    fields = ["config", "orders", "top1", "top1_sd", "top3", "neurons", "competing", "orig_in_competing",
              "min_orig_competing", "delta_o0", "ci_lo", "ci_hi", "mcnemar_p", "accepted", "secs"]
    with CSV.open("a", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields)
        if first:
            wr.writeheader()
        wr.writerow({k: out.get(k, "") for k in fields})
    return out, res


def stage_dev():
    tr = S.load("base76", BASE["train_channels"])
    dev = [it for it in S.load("dev", BASE["channels"]) if it["aug"] == 0]
    orders = (0, 1, 2)
    stim = {(): S.build_stimuli(tr, BASE)}
    base_out, base_res = run("base (N selection)", BASE, stim[()], dev, orders)
    base_rows = base_res[0][3]
    outs = {}
    for name, ch in VARIANTS.items():
        cfg = {**BASE, **ch}
        akey = tuple((k, cfg.get(k)) for k in ACT_KEYS if cfg.get(k))
        if akey not in stim:
            S._ACT_CACHE.clear()
            stim = {(): stim[()], akey: S.build_stimuli(tr, cfg)}
        outs[name] = run(name, cfg, stim[akey], dev, orders, base_rows)[0]
    accepted = [n for n, o in outs.items() if o["accepted"]]       # the pre-declared rule only
    # combination of the accepted ones: activation switches + the best accepted competition rule + the best accepted F
    comb = {}
    for n in accepted:
        ch = VARIANTS[n]
        if "competition" in ch and "competition" in comb:
            if outs[n]["top1"] <= outs[comb["_comp_src"]]["top1"]:
                continue
        if "fixations" in ch and "fixations" in comb:
            if outs[n]["top1"] <= outs[comb["_fix_src"]]["top1"]:
                continue
        comb.update(ch)
        if "competition" in ch:
            comb["_comp_src"] = n
        if "fixations" in ch:
            comb["_fix_src"] = n
    comb = {k: v for k, v in comb.items() if not k.startswith("_")}
    final_name, final_changes = "base (N selection)", {}
    if len(accepted) == 1:
        final_name, final_changes = accepted[0], VARIANTS[accepted[0]]
    elif len(accepted) > 1:
        cfg = {**BASE, **comb}
        S._ACT_CACHE.clear()
        st = S.build_stimuli(tr, cfg)
        name = "combination: " + " + ".join(accepted)
        o = run(name, cfg, st, dev, orders, base_rows)[0]
        if o["accepted"]:
            final_name, final_changes = name, comb
        else:
            best = max(accepted, key=lambda n: outs[n]["top1"])
            final_name, final_changes = best, VARIANTS[best]
    print(f"accepted alone: {accepted}; FINAL: {final_name} {final_changes}", flush=True)
    STATE.write_text(json.dumps({"final": final_name, "changes": final_changes, "accepted": accepted,
                                 "base_dev": base_out, "variants": outs}, indent=1, default=str))


def _p1_rows(neurons, stimuli, rows):
    for n in neurons:
        n.mu = S.own_mean(n, stimuli)
    out = []
    for r in rows:
        w = r["winner"]
        mu = neurons[w].mu if w >= 0 else 0.0
        out.append({"stem": r["stem"], "true": r["true"], "pred": r["pred"], "winner": w,
                    "cls_win": neurons[w].cls if w >= 0 else "none", "r": r.get("r_win", 0.0), "mu": round(mu, 6),
                    "norm": round(r.get("r_win", 0.0) / mu, 6) if mu > 0 else 0.0,
                    "class_best": {c: [v[0], round(neurons[v[1]].mu, 6), v[1]] for c, v in r["class_scores"].items()}})
    return out


def report(tag, rows):
    ours = {r["stem"]: r for r in rows}
    n_proj = {json.loads(l)["stem"]: json.loads(l) for l in open(ISL / "N_projection_test.jsonl")}
    com = {Path(json.loads(l)["path"]).stem: json.loads(l) for l in open(ISL / "coman_mnist_all.jsonl")}
    for part in ("all", "complete", "incomplete"):
        keys = sorted(k for k in ours if part == "all" or MANIFEST.get(k) == part)
        t1 = 100.0 * sum(ours[k]["pred"] == ours[k]["true"] for k in keys) / len(keys)
        t3 = 100.0 * sum(ours[k]["true"] in ours[k]["top3"] for k in keys) / len(keys)
        line = f"TEST {tag} {part:<10} n {len(keys):5}  top-1 {t1:6.2f}  top-3 {t3:6.2f}"
        for ref_name, ref in (("N-proj", n_proj), ("ComAN", com)):
            a = [ref[k]["pred"] == ref[k]["true"] for k in keys]
            b = [ours[k]["pred"] == ours[k]["true"] for k in keys]
            d = np.array([int(y) - int(x) for x, y in zip(a, b)])
            half = 1.96 * d.std(ddof=1) / math.sqrt(len(d)) if d.any() else 0.0
            p, _, _ = S.mcnemar(a, b)
            line += f" | vs {ref_name} {100 * np.mean(a):.2f}: Δ {100 * d.mean():+.2f} [{100 * (d.mean() - half):+.2f}, {100 * (d.mean() + half):+.2f}] p {p:.2g}"
        print(line, flush=True)
    per = {c: 100.0 * np.mean([r["pred"] == c for r in rows if r["true"] == c]) for c in sorted({r["true"] for r in rows})}
    print(f"TEST {tag} per class: " + ", ".join(f"{c} {v:.1f}" for c, v in per.items()), flush=True)


def stage_final(workers):
    st = json.loads(STATE.read_text())
    cfg = {**BASE, **st["changes"], "class_scores": True}
    tr = S.load("base76", cfg["train_channels"])
    stimuli = S.build_stimuli(tr, cfg)
    neurons = S.train(stimuli, cfg, 0)
    print(f"FINAL {st['final']}: census {PN.census(neurons, 2)}", flush=True)
    dev = [it for it in S.load("dev", cfg["channels"]) if it["aug"] == 0]
    rows = S.evaluate_parallel(neurons, dev, {**cfg, "workers": workers}, workers)
    with open(ISL / "P1_projection_dev.jsonl", "w") as fh:
        for r in _p1_rows(neurons, stimuli, rows):
            fh.write(json.dumps(r) + "\n")
    print(f"P1 dev dump: top-1 {100 * np.mean([r['pred'] == r['true'] for r in rows]):.2f}", flush=True)
    S._LOADED.clear(), S._ACT_CACHE.clear()
    test = [it for it in S.load("mtest", cfg["channels"]) if it["aug"] == 0]
    rows = S.evaluate_parallel(neurons, test, {**cfg, "workers": workers}, workers)
    p1 = _p1_rows(neurons, stimuli, rows)
    with open(ISL / "P1_projection_mtest.jsonl", "w") as fh:
        for r in p1:
            fh.write(json.dumps(r) + "\n")
    if st["changes"]:
        with open(ISL / "P_final_test.jsonl", "w") as fh:
            for r in rows:
                fh.write(json.dumps({"config": st["final"], **{k: v for k, v in r.items() if k != "class_scores"}}) + "\n")
    report("final" if st["changes"] else "final (= base, re-run for the P1 fields)", rows)


def stage_emnist(workers):
    st = json.loads(STATE.read_text())
    if not st["changes"]:
        print("final = base: EMNIST not re-run (O1 already has it)", flush=True)
        return
    cfg = {**BASE, **st["changes"]}
    tr = S.load("ecand60", cfg["train_channels"], 10)
    dev = [it for it in S.load("edev", cfg["channels"]) if it["aug"] == 0]
    stimuli = S.build_stimuli(tr, cfg)
    run(f"EMNIST 10/letter [{st['final']}]", cfg, stimuli, dev, (0,))
    S._ACT_CACHE.clear()
    neurons = S.train(stimuli, cfg, 0)
    test = [it for it in S.load("etest", cfg["channels"]) if it["aug"] == 0]
    rows = S.evaluate_parallel(neurons, test, {**cfg, "workers": workers}, workers)
    with open(ISL / "P_final_etest.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps({"config": st["final"], **r}) + "\n")
    n = len(rows)
    t1 = 100.0 * sum(r["pred"] == r["true"] for r in rows) / n
    t3 = 100.0 * sum(r["true"] in r["top3"] for r in rows) / n
    il = 100.0 * sum(r["pred"] == r["true"] or {r["pred"], r["true"]} == {"I", "L"} for r in rows) / n
    print(f"TEST EMNIST 10/letter: n {n} top-1 {t1:.2f} top-3 {t3:.2f} (I+L {il:.2f}); census {PN.census(neurons, 2)}",
          flush=True)


def stage_p4(workers):
    tr = S.load("cand60", BASE["train_channels"], 60)
    dev = [it for it in S.load("dev", BASE["channels"]) if it["aug"] == 0]
    stimuli = S.build_stimuli(tr, BASE)
    run("P4 base, 60 originals per digit", BASE, stimuli, dev, (0,))
    S._ACT_CACHE.clear()
    neurons = S.train(stimuli, BASE, 0)
    test = [it for it in S.load("mtest", BASE["channels"]) if it["aug"] == 0]
    rows = S.evaluate_parallel(neurons, test, {**BASE, "workers": workers}, workers)
    with open(ISL / "P_p4_test.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps({"config": "P4 60/digit", **r}) + "\n")
    print(f"P4 census {PN.census(neurons, 2)}", flush=True)
    report("P4 60/digit", rows)


def stage_p10(workers):
    st = json.loads(STATE.read_text())
    cfg = {**BASE, **st["changes"]}
    tr = S.load("cand60", cfg["train_channels"], 10)
    dev = [it for it in S.load("dev", cfg["channels"]) if it["aug"] == 0]
    stimuli = S.build_stimuli(tr, cfg)
    run(f"P9 final, 10 originals per digit [{st['final']}]", cfg, stimuli, dev, (0,))
    S._ACT_CACHE.clear()
    neurons = S.train(stimuli, cfg, 0)
    test = [it for it in S.load("mtest", cfg["channels"]) if it["aug"] == 0]
    rows = S.evaluate_parallel(neurons, test, {**cfg, "workers": workers}, workers)
    with open(ISL / "P_p10_test.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps({"config": "P9 final 10/digit", **r}) + "\n")
    print(f"P9 census {PN.census(neurons, 2)}", flush=True)
    report("P9 final 10/digit", rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "final", "emnist", "p4", "p10"])
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    {"dev": stage_dev, "final": lambda: stage_final(a.workers), "emnist": lambda: stage_emnist(a.workers),
     "p4": lambda: stage_p4(a.workers), "p10": lambda: stage_p10(a.workers)}[a.stage]()


if __name__ == "__main__":
    main()
