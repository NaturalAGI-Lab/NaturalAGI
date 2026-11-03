"""P1 — two maps, one competition: the ComAN winner and the Section IV winner compete by their reaction normalised by the
neuron's own mean reaction on its OWN training positives (intrinsic plasticity, Desai 1999; Axiom 3 kept: no other-class
statistics, nothing tuned). Pre-registration: lab_log.md, section P.

ComAN reaction of a concept = MAX over the detector filters of the GED similarity + λ·log2(cc) (the N final readout);
its own-positive mean = the mean of that reaction over the training images of its own subclass (a pl_dump of
tests/_isl_train/<subclass>/ with the same configuration; a concept that does not match an own image scores 0 there).
Section IV: the winner's response and its own-positive mean come from the P1 dumps of the offline driver.

Usage: p1_two_maps.py --coman-train <4 dumps of tests/_isl_train> --coman-dev <4 dumps> --proj-dev P1_projection_dev.jsonl
                      [--coman-test <4 dumps> --proj-test P1_projection_mtest.jsonl]   (dumps joined with '+')
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import coman_rerank as K

LAM = 0.05
MANIFEST = {r["image_path"].split("/")[-1][:-4]: r["structure"]
            for r in csv.DictReader(open(K.REPO / "datasets" / "mnist_all_manifest.csv"))}


def coman_reactions(spec):
    """{stem: (true, {cid: (class, reaction)})} — per concept MAX over the filter dumps, + λ·log2(cc)."""
    dumps, _, _ = K.load_spec(spec)
    out = {}
    for path in dumps[0]:
        best = {}
        for d in dumps:
            for e in (d.get(path) or {}).get("ranked", []):
                if e["minor"]:
                    r = (e["sim"] or 0.0) + LAM * math.log2(max(e["cc"] or 1, 1))
                    if e["cid"] not in best or r > best[e["cid"]][1]:
                        best[e["cid"]] = (e["c"], r)
        out[Path(path).stem] = (dumps[0][path]["true"], best, Path(path).parent.name)
    return out


def own_means(train):
    """μ_c = mean reaction of concept c over the training images of its own subclass (cid = <subclass>s<set>)."""
    cids = {cid for _, best, _ in train.values() for cid in best}
    by_sub = defaultdict(list)
    for cid in cids:
        by_sub[cid.split("s")[0]].append(cid)
    per = defaultdict(list)
    for _, best, folder in train.values():
        for cid in by_sub.get(folder, ()):
            per[cid].append(best.get(cid, (None, 0.0))[1])
    return {c: max(sum(v) / len(v), 1e-6) for c, v in per.items() if v}


def combine(coman, mu_c, proj):
    """{stem: (true, pred)} — the larger normalised winner reaction decides."""
    out = {}
    for stem, (true, best, _) in coman.items():
        p = proj.get(stem)
        if best:
            cid, (cls_c, r_c) = max(best.items(), key=lambda kv: kv[1][1])
            n_c = r_c / mu_c.get(cid, 1.0)
        else:
            cls_c, n_c = None, -1.0
        if p is not None and p["r"] > 0:
            n_p = p["r"] / max(p["mu"], 1e-6)
            cls_p = p["pred"]
        else:
            cls_p, n_p = None, -1.0
        out[stem] = (true, cls_c if n_c >= n_p else cls_p, cls_c, cls_p)
    return out


def report(name, comb):
    for part in ("", "complete", "incomplete"):
        keys = [k for k in comb if not part or MANIFEST.get(k) == part]
        if not keys:
            continue
        acc = 100.0 * sum(comb[k][1] == comb[k][0] for k in keys) / len(keys)
        a_c = 100.0 * sum(comb[k][2] == comb[k][0] for k in keys) / len(keys)
        a_p = 100.0 * sum(comb[k][3] == comb[k][0] for k in keys) / len(keys)
        print(f"{name} {part or 'all':<10} n {len(keys):5}  two maps {acc:6.2f}   ComAN alone {a_c:6.2f}   "
              f"Section IV alone {a_p:6.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coman-train", required=True)
    ap.add_argument("--coman-dev", required=True)
    ap.add_argument("--proj-dev", required=True)
    ap.add_argument("--coman-test")
    ap.add_argument("--proj-test")
    a = ap.parse_args()
    mu_c = own_means(coman_reactions(a.coman_train))
    print(f"ComAN own-positive means for {len(mu_c)} concepts (median {sorted(mu_c.values())[len(mu_c) // 2]:.3f})")
    load = lambda f: {r["stem"]: r for r in (json.loads(line) for line in open(f))}
    report("DEV ", combine(coman_reactions(a.coman_dev), mu_c, load(a.proj_dev)))
    if a.coman_test:
        comb = combine(coman_reactions(a.coman_test), mu_c, load(a.proj_test))
        report("TEST", comb)
        with open(K.REPO / "tests" / "_isl" / "P1_two_maps_test.jsonl", "w") as fh:
            for stem, (true, pred, pc, pp) in comb.items():
                fh.write(json.dumps({"stem": stem, "true": true, "pred": pred, "top3": [pred], "coman": pc, "proj": pp}) + "\n")


if __name__ == "__main__":
    main()
