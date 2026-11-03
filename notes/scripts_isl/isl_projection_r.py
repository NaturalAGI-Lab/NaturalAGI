"""R — Section IV toward the band system's EMNIST level within the rules (pre-registration: lab_log.md section R,
variants restated in experiments/isl_transfer_2026-10/lab_R.md). Base = the P final configuration.

  describe <split> [--augs 10]   dense centre-line description (orient 52 dims, 32 points + tangents) of every cached
                                 item, detector as at recognition (110 / 4.55, stems rule); augmentations recomputed
                                 with the ISL cache's seeds (wide, as the best2 training channels) -> tests/_isl/dense_r/
  dev mnist|emnist               base, R1 β ∈ {0.1, 0.2, 0.3, 0.5}, R2 shape anchors, R4 θ ∈ {0.5, 0.7}, R5 homeostasis
                                 (MNIST: his 76 originals, 3 orders; EMNIST: first 10 per letter, 1 order)
  combine                        acceptance on BOTH sets, the combination, the final configuration (dev, both sets)
  test mnist76|mnist10|emnist    the final: official test ONCE
Usage: isl_projection_r.py describe|dev|combine|test ... [--workers 4]
"""
import argparse
import csv
import json
import logging
import math
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

import numpy as np

import isl_cache as C
import isl_projection_n as PN
import isl_projection_p as PP
import isl_sim as S

EXP = S.REPO / "experiments" / "isl_transfer_2026-10"
ISL = S.REPO / "tests" / "_isl"
DENSE = ISL / "dense_r"
CSV = EXP / "results_R.csv"
STATE = ISL / "R_state.json"
SRC = {"base76": "mnist_base76", "cand60": "mnist_cand60", "dev": "mnist_dev", "mtest": "mnist_all",
       "ecand60": "emnist_cand60", "edev": "emnist_dev", "etest": "emnist_testfull"}
SETS = {"mnist": ("base76", None, "dev", (0, 1, 2)), "emnist": ("ecand60", 10, "edev", (0,))}
VARIANTS = {   # name -> (cfg changes, post-training hook)
    "R1 β 0.1": ({"param_beta": 0.1}, "param"), "R1 β 0.2": ({"param_beta": 0.2}, "param"),
    "R1 β 0.3": ({"param_beta": 0.3}, "param"), "R1 β 0.5": ({"param_beta": 0.5}, "param"),
    "R2 shape anchors": ({"shape_anchors": True}, None),
    "R4 θ 0.5": ({}, ("sleep", 0.5)), "R4 θ 0.7": ({}, ("sleep", 0.7)),
    "R5 homeostasis": ({"homeostasis": True}, "homeo"),
}


def base_cfg():
    st = json.loads(PP.STATE.read_text())
    return {**PP.BASE, **st["changes"]}


# ----------------------------------------------------------------------------------------------- descriptors
def _desc(job):
    path, key, seed = job
    logging.disable(logging.CRITICAL)
    C._modules()
    import cv2
    from settings import Settings
    from skeleton_gng_mapper import SkeletonGNGMapper
    from dense_features import dense_representation
    try:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if seed is not None:
            img = C.augment(img, seed, wide=True)
        m = SkeletonGNGMapper(Settings(N=35), 110, 4.55, thick_stroke_threshold=0, bridge_protect_stems=True)
        d = dense_representation(m.skeletonize(img, 110))
        return {"key": key, **d} if d else {"key": key, "error": "short"}
    except Exception as exc:  # noqa: BLE001 — a detector failure = no description
        return {"key": key, "error": str(exc)[:100]}


def describe(split, augs, procs):
    DENSE.mkdir(parents=True, exist_ok=True)
    out = DENSE / f"{split}.jsonl"
    done = {json.loads(line)["key"] for line in open(out)} if out.exists() else set()
    root = S.REPO / "tests" / SRC[split]
    limit = SETS["emnist"][1] if split == "ecand60" else (10 if split == "cand60" else None)
    jobs = []
    for cdir in sorted(p for p in root.iterdir() if p.is_dir()):
        files = sorted(cdir.glob("*.png"))
        for f in files[:limit] if limit else files:
            jobs.append((f, f.stem, None))
            jobs += [(f, f"{f.stem}_a{j}", zlib.crc32(f"{f.stem}:{j}".encode())) for j in range(1, augs + 1)]
    todo = [j for j in jobs if j[1] not in done]
    print(f"{split}: {len(jobs)} items, {len(todo)} to describe", flush=True)
    with Pool(procs) as pool, open(out, "a") as fh:
        for rec in pool.imap_unordered(_desc, todo, chunksize=32):
            fh.write(json.dumps(rec) + "\n")


def attach(items, split):
    cache = {}
    for line in open(DENSE / f"{split}.jsonl"):
        r = json.loads(line)
        if "orient" in r:
            cache[r["key"]] = {"orient": r["orient"], "points": r["points"], "tangents": r["tangents"]}
    missing = 0
    for it in items:
        it["dense"] = cache.get(it["stem"])
        missing += it["dense"] is None
    return missing


def family_vectors(items):
    fv = {}
    for it in items:
        if it.get("dense"):
            fv.setdefault((it["cls"], it["family"]), []).append(it["dense"]["orient"])
    return fv


def post(neurons, hook, stimuli, fv, cfg):
    if hook == "param" or cfg.get("param_beta"):
        S.attach_param_bands(neurons, fv)
    if isinstance(hook, tuple) and hook[0] == "sleep":
        neurons = S.consolidate(neurons, cfg, hook[1])
    if cfg.get("sleep_theta"):
        neurons = S.consolidate(neurons, cfg, cfg["sleep_theta"])
    if hook == "param" or cfg.get("param_beta"):              # bands after a possible merge
        S.attach_param_bands(neurons, fv)
    if hook == "homeo" or cfg.get("homeostasis"):
        S.attach_homeostasis(neurons, stimuli)
    return neurons


# ----------------------------------------------------------------------------------------------- dev
def run(tag, name, cfg, hook, stimuli, fv, dev, orders, base_rows=None):
    t0 = time.time()
    res = []
    for seed in orders:
        neurons = post(S.train(stimuli, cfg, seed), hook, stimuli, fv, cfg)
        rows = S.evaluate(neurons, dev, cfg)
        sm = S.summarise(rows, neurons)
        res.append((sm["top1"], sm["top3"], PN.census(neurons, cfg.get("min_originals", 1)), rows))
    out = {"set": tag, "config": name, "orders": len(orders), "top1": round(float(np.mean([r[0] for r in res])), 2),
           "top1_sd": round(float(np.std([r[0] for r in res])), 2), "top3": round(float(np.mean([r[1] for r in res])), 2),
           "competing": round(float(np.mean([r[2]["competing"] for r in res])), 1),
           "orig_in_competing": round(float(np.mean([r[2]["orig_in_competing"] for r in res])), 1),
           "min_orig_competing": min(r[2]["min_orig_competing"] for r in res)}
    if base_rows is not None:
        dl, lo, hi, p = PP.paired(base_rows, res[0][3])
        out.update({"delta_o0": round(dl, 2), "ci_lo": round(lo, 2), "ci_hi": round(hi, 2), "mcnemar_p": f"{p:.2g}",
                    "accepted": bool(lo > -1.0)})
    out["secs"] = round(time.time() - t0, 1)
    print(f"[{tag}] {name:<22} top1 {out['top1']:6.2f} ±{out['top1_sd']:<5} top3 {out['top3']:6.2f} competing "
          f"{out['competing']} ({out['orig_in_competing']} %, min {out['min_orig_competing']})"
          + (f"  Δ(o0) {out['delta_o0']:+.2f} [{out['ci_lo']:+.2f}, {out['ci_hi']:+.2f}] p {out['mcnemar_p']} "
             f"{'ACCEPT' if out['accepted'] else 'reject'}" if base_rows is not None else "") + f"  {out['secs']}s",
          flush=True)
    fields = ["set", "config", "orders", "top1", "top1_sd", "top3", "competing", "orig_in_competing",
              "min_orig_competing", "delta_o0", "ci_lo", "ci_hi", "mcnemar_p", "accepted", "secs"]
    first = not CSV.exists()
    with CSV.open("a", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields)
        if first:
            wr.writeheader()
        wr.writerow({k: out.get(k, "") for k in fields})
    return out, res


def load_set(tag, cfg):
    tr_split, limit, dev_split, orders = SETS[tag]
    tr = S.load(tr_split, cfg["train_channels"], limit)
    dev = [it for it in S.load(dev_split, cfg["channels"]) if it["aug"] == 0]
    m1, m2 = attach(tr, tr_split), attach(dev, dev_split)
    print(f"[{tag}] train {tr_split}: {len(tr)} items ({m1} without a description); dev {len(dev)} ({m2} without)",
          flush=True)
    return tr, dev, orders


def stage_dev(tag):
    cfg0 = base_cfg()
    tr, dev, orders = load_set(tag, cfg0)
    fv = family_vectors(tr)
    stim = {False: S.build_stimuli(tr, cfg0)}
    base_out, base_res = run(tag, "base (P final)", cfg0, None, stim[False], fv, dev, orders)
    outs = {}
    for name, (ch, hook) in VARIANTS.items():
        cfg = {**cfg0, **ch}
        sa = bool(cfg.get("shape_anchors"))
        if sa not in stim:
            S._ACT_CACHE.clear()
            stim[sa] = S.build_stimuli(tr, cfg)
        outs[name] = run(tag, name, cfg, hook, stim[sa], fv, dev, orders, base_res[0][3])[0]
        if sa:
            S._ACT_CACHE.clear()
    path = ISL / f"R_dev_{tag}.json"
    path.write_text(json.dumps({"base": base_out, "variants": outs}, indent=1))


# ----------------------------------------------------------------------------------------------- combination / tests
def _changes(name):
    ch, hook = VARIANTS[name]
    return {**ch, **({"sleep_theta": hook[1]} if isinstance(hook, tuple) else {})}


def stage_combine():
    dev = {t: json.loads((ISL / f"R_dev_{t}.json").read_text()) for t in SETS}
    acc = [n for n in VARIANTS if dev["mnist"]["variants"][n]["accepted"] and dev["emnist"]["variants"][n]["accepted"]]
    score = lambda n: dev["mnist"]["variants"][n]["delta_o0"] + dev["emnist"]["variants"][n]["delta_o0"]
    print(f"accepted on both sets: {acc}", flush=True)
    chosen = []                                   # one β and one θ (best on the sum of Δ over both sets) + R2 / R5
    for prefix in ("R1", "R4", "R2", "R5"):
        group = [n for n in acc if n.startswith(prefix)]
        if group:
            chosen.append(max(group, key=score))
    final, changes = "base (P final)", {}
    if len(chosen) == 1:
        final, changes = chosen[0], _changes(chosen[0])
    elif len(chosen) > 1:
        comb = {k: v for n in chosen for k, v in _changes(n).items()}
        ok = True
        for tag in SETS:
            cfg0 = base_cfg()
            tr, devset, orders = load_set(tag, cfg0)
            fv = family_vectors(tr)
            base_res = run(tag, "base (P final, re-run)", cfg0, None, S.build_stimuli(tr, cfg0), fv, devset, orders[:1])[1]
            S._ACT_CACHE.clear()
            cfg = {**cfg0, **comb}
            o = run(tag, "combination: " + " + ".join(chosen), cfg, None, S.build_stimuli(tr, cfg), fv, devset, orders,
                    base_res[0][3])[0]
            ok = ok and o["accepted"]
            S._LOADED.clear(), S._ACT_CACHE.clear()
        final, changes = ("combination: " + " + ".join(chosen), comb) if ok else (max(chosen, key=score),
                                                                              _changes(max(chosen, key=score)))
    print(f"FINAL: {final} {changes}", flush=True)
    STATE.write_text(json.dumps({"final": final, "changes": changes, "accepted": acc, "chosen": chosen}, indent=1))


TESTS = {"mnist76": ("base76", None, "mtest", "P_final_test.jsonl"), "mnist10": ("cand60", 10, "mtest", "P_p10_test.jsonl"),
         "emnist": ("ecand60", 10, "etest", "P_final_etest.jsonl")}


def stage_test(which, workers):
    st = json.loads(STATE.read_text())
    cfg = {**base_cfg(), **st["changes"]}
    tr_split, limit, test_split, ref = TESTS[which]
    tr = S.load(tr_split, cfg["train_channels"], limit)
    attach(tr, tr_split)
    stimuli = S.build_stimuli(tr, cfg)
    neurons = post(S.train(stimuli, cfg, 0), None, stimuli, family_vectors(tr), cfg)
    print(f"[{which}] FINAL {st['final']}: census {PN.census(neurons, 2)}", flush=True)
    test = [it for it in S.load(test_split, cfg["channels"]) if it["aug"] == 0]
    attach(test, test_split)
    rows = S.evaluate_parallel(neurons, test, {**cfg, "workers": workers}, workers)
    with open(ISL / f"R_{which}_test.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps({"config": st["final"], **r}) + "\n")
    ours = {r["stem"]: r for r in rows}
    refs = {"P final": {json.loads(l)["stem"]: json.loads(l) for l in open(ISL / ref)}}
    if which != "emnist":
        refs["ComAN as is"] = {Path(json.loads(l)["path"]).stem: json.loads(l) for l in open(ISL / "coman_mnist_all.jsonl")}
    parts = ("all", "complete", "incomplete") if which != "emnist" else ("all",)
    for part in parts:
        keys = sorted(k for k in ours if part == "all" or PP.MANIFEST.get(k) == part)
        t1 = 100.0 * sum(ours[k]["pred"] == ours[k]["true"] for k in keys) / len(keys)
        t3 = 100.0 * sum(ours[k]["true"] in ours[k]["top3"] for k in keys) / len(keys)
        line = f"TEST {which} {part:<10} n {len(keys):5}  top-1 {t1:6.2f}  top-3 {t3:6.2f}"
        if which == "emnist":
            il = 100.0 * sum(ours[k]["pred"] == ours[k]["true"] or {ours[k]["pred"], ours[k]["true"]} == {"I", "L"}
                             for k in keys) / len(keys)
            line += f"  (I+L {il:.2f})"
        for name, ref_rows in refs.items():
            a = [ref_rows[k]["pred"] == ref_rows[k]["true"] for k in keys]
            b = [ours[k]["pred"] == ours[k]["true"] for k in keys]
            d = np.array([int(y) - int(x) for x, y in zip(a, b)])
            half = 1.96 * d.std(ddof=1) / math.sqrt(len(d)) if d.any() else 0.0
            p, _, _ = S.mcnemar(a, b)
            line += (f" | vs {name} {100 * np.mean(a):.2f}: Δ {100 * d.mean():+.2f} [{100 * (d.mean() - half):+.2f}, "
                     f"{100 * (d.mean() + half):+.2f}] p {p:.2g}")
        print(line, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["describe", "dev", "combine", "test"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--augs", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.stage == "describe":
        describe(a.arg, a.augs, a.workers)
    elif a.stage == "dev":
        stage_dev(a.arg)
    elif a.stage == "combine":
        stage_combine()
    else:
        stage_test(a.arg, a.workers)


if __name__ == "__main__":
    main()
