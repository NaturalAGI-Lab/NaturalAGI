"""N-projection — Section IV projection model in forms compliant with rule 1 (every competing neuron rests on >= 2
originals), plus his point 3 (vector reaction, local WTA). Pre-registration: experiments/isl_transfer_2026-10/lab_N_projection.md.

  P1  his 13 hand subclasses (fixed map), tau 1.0 / 0.8
  P2  novelty map + consolidation (min_originals 2), rho 0.5..0.8 x tau 1.0 / 0.8, 3 orders, with a census
  P3  competition 'distinct' / 'pareto' on top of the best of P1 / P2
Selection: highest dev top-1 among the compliant configurations -> the official MNIST test ONCE (all / complete /
incomplete, top-3, McNemar vs ComAN as is).
Usage: isl_projection_n.py [--workers 2]     (dev in one process with cached activations; the test in forked workers)
"""
import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np

import isl_sim as S

REPO = S.REPO
EXP = REPO / "experiments" / "isl_transfer_2026-10"
ISL = REPO / "tests" / "_isl"
CSV = EXP / "results_N_projection.csv"
MANIFEST = {r["image_path"].split("/")[-1][:-4]: r["structure"]
            for r in csv.DictReader(open(REPO / "datasets" / "mnist_all_manifest.csv"))}


def census(neurons, need=2):
    comp = [n for n in neurons if len(n.families) >= need]
    orig = sum(len(n.families) for n in neurons)
    return {"neurons": len(neurons), "competing": len(comp),
            "orig_in_competing": round(100.0 * sum(len(n.families) for n in comp) / max(orig, 1), 1),
            "min_orig_competing": min((len(n.families) for n in comp), default=0)}


def run_cfg(name, cfg, stimuli, dev, orders):
    t0 = time.time()
    res = []
    for seed in orders:
        neurons = S.train(stimuli, cfg, seed)
        rows = S.evaluate(neurons, dev, cfg)
        sm = S.summarise(rows, neurons)
        res.append((sm, census(neurons, cfg.get("min_originals", 1) if not cfg.get("groups") else 1), rows))
    top1 = [r[0]["top1"] for r in res]
    out = {"config": name, "tau": cfg["tau"], "rho": cfg["rho"] if not cfg.get("groups") else "",
           "map": "hand" if cfg.get("groups") else "novelty", "min_originals": cfg.get("min_originals", 1),
           "competition": cfg.get("competition", "argmax"), "orders": len(orders),
           "top1": round(float(np.mean(top1)), 2), "top1_sd": round(float(np.std(top1)), 2),
           "top3": round(float(np.mean([r[0]["top3"] for r in res])), 2),
           **{k: round(float(np.mean([r[1][k] for r in res])), 1) for k in ("neurons", "competing", "orig_in_competing")},
           "min_orig_competing": min(r[1]["min_orig_competing"] for r in res), "secs": round(time.time() - t0, 1)}
    print(f"{name:<40} top1 {out['top1']:6.2f} ±{out['top1_sd']:<5} top3 {out['top3']:6.2f}  neurons {out['neurons']:5.1f} "
          f"competing {out['competing']:5.1f} ({out['orig_in_competing']:5.1f} % of originals, min {out['min_orig_competing']})"
          f"  {out['secs']}s", flush=True)
    first = not CSV.exists()
    with CSV.open("a", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(out))
        if first:
            wr.writeheader()
        wr.writerow(out)
    return out, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    base = {**S.DEFAULT, **S.IMPROVEMENTS["best2"], "workers": 1}
    groups = json.loads((ISL / "base76_subclasses.json").read_text())
    tr = S.load("base76", base["train_channels"])
    dev = [it for it in S.load("dev", base["channels"]) if it["aug"] == 0]
    print(f"train base76: {len({(i['cls'], i['family']) for i in tr})} originals; dev {len(dev)}", flush=True)
    stimuli = S.build_stimuli(tr, base)
    orders = (0, 1, 2)
    cands = {}
    for tau in (1.0, 0.8):                                                    # P1
        cfg = {**base, "tau": tau, "groups": groups}
        cands[f"P1 hand tau{tau}"] = (cfg, (0,), run_cfg(f"P1 hand tau{tau}", cfg, stimuli, dev, (0,))[0])
    for rho in (0.5, 0.6, 0.7, 0.8):                                          # P2
        for tau in (1.0, 0.8):
            cfg = {**base, "tau": tau, "rho": rho, "min_originals": 2}
            name = f"P2 novelty+consol rho{rho} tau{tau}"
            cands[name] = (cfg, orders, run_cfg(name, cfg, stimuli, dev, orders)[0])
    best_name = max(cands, key=lambda k: cands[k][2]["top1"])
    print(f"best compliant P1/P2: {best_name}", flush=True)
    bcfg, borders, _ = cands[best_name]
    for rule in ("distinct", "pareto"):                                      # P3
        name = f"P3 {rule} on [{best_name}]"
        cfg = {**bcfg, "competition": rule}
        cands[name] = (cfg, borders, run_cfg(name, cfg, stimuli, dev, borders)[0])
    sel = max(cands, key=lambda k: cands[k][2]["top1"])
    scfg = cands[sel][0]
    print(f"SELECTED (pre-registered rule): {sel} — dev {cands[sel][2]['top1']}", flush=True)
    (ISL / "N_projection_selected.json").write_text(json.dumps({"selected": sel, "dev": cands[sel][2]}, indent=1))

    # official test, once, order 0 of the selected configuration
    S._ACT_CACHE.clear()
    neurons = S.train(stimuli, scfg, 0)
    test = [it for it in S.load("mtest", scfg["channels"]) if it["aug"] == 0]
    rows = S.evaluate_parallel(neurons, test, {**scfg, "workers": a.workers}, a.workers)
    with open(ISL / "N_projection_test.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps({"config": sel, **r}) + "\n")
    ours = {r["stem"]: r for r in rows}
    com = {Path(json.loads(l)["path"]).stem: json.loads(l) for l in open(ISL / "coman_mnist_all.jsonl")}
    for part in ("all", "complete", "incomplete"):
        keys = sorted(k for k in ours if part == "all" or MANIFEST.get(k) == part)
        t1 = 100.0 * sum(ours[k]["pred"] == ours[k]["true"] for k in keys) / len(keys)
        t3 = 100.0 * sum(ours[k]["true"] in ours[k]["top3"] for k in keys) / len(keys)
        c1 = 100.0 * sum(com[k]["pred"] == com[k]["true"] for k in keys) / len(keys)
        p, only_c, only_o = S.mcnemar([com[k]["pred"] == com[k]["true"] for k in keys],
                                      [ours[k]["pred"] == ours[k]["true"] for k in keys])
        d = np.array([int(ours[k]["pred"] == ours[k]["true"]) - int(com[k]["pred"] == com[k]["true"]) for k in keys])
        half = 1.96 * d.std(ddof=1) / np.sqrt(len(d))
        print(f"TEST {part:<10} n {len(keys):5}  top-1 {t1:6.2f}  top-3 {t3:6.2f}  ComAN {c1:6.2f}  "
              f"Δ {100 * d.mean():+.2f} [{100 * (d.mean() - half):+.2f}, {100 * (d.mean() + half):+.2f}]  "
              f"McNemar p {p:.2g} (ComAN-only {only_c}, ours-only {only_o})", flush=True)
    per = {c: 100.0 * np.mean([r["pred"] == c for r in rows if r["true"] == c]) for c in sorted({r["true"] for r in rows})}
    print("TEST per digit: " + ", ".join(f"{c} {v:.1f}" for c, v in per.items()), flush=True)
    sizes = [len(n.families) for n in neurons if len(n.families) >= scfg.get("min_originals", 1)]
    print(f"TEST neurons competing {len(sizes)}, originals per neuron min {min(sizes)} median {int(np.median(sizes))}",
          flush=True)


if __name__ == "__main__":
    main()
