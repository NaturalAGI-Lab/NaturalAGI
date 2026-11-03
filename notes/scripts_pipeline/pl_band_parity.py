"""Parity checks for the band-concept port.

  offline   run the PRODUCTION modules (direction_map, band_math, band_scorer, fewshot_selection) on the
            frozen reference skeletons and reproduce the offline few-shot numbers of fs_root.py.
            Options: --post-merge  compute the map after merge_close_intersection_points (the pipeline-native graph)
  ingest-pool  push every glyph-form directory of tests/emnist52/train through the LIVE pipeline as session
            fs-pool-<form> with direction_map on (never folded), and wait until the features have landed.
  features  parity (a): :GraphFeatures.dm written by the pipeline vs the offline post-merge map, by file name.
  pipeline <dump.jsonl> <B>   parity (c): predictions of the live pipeline in band mode vs the offline
            predictions (root per form) on the same images.
  replay <session_id> [dump.jsonl]   score the :GraphFeatures kept from a pipeline run with the PRODUCTION scorer
            for every stored band model; with a dump, first prove replay == end-to-end for that model.
  smoke <dump.jsonl>          default-unchanged check against tests/_fewshot_ref/baseline_smoke.jsonl.
  bands     parity (b): :BandModel / :BandConcept fs_B2|4|10 stored by the concept_creator vs the offline build.

Reference (notes/fewshot_error_analysis_2026-09-18.md §11, full EMNIST-letters test, merge-if-similar):
  root per form   B=2 64.71  B=4 66.58  B=10 68.42     root per letter  B=2 65.70  B=4 67.23  B=10 68.09
"""
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import networkx as nx
import numpy as np

REPO = Path(__file__).resolve().parents[2]
for rel in ("src/contour_analysis/logic", "src/concept_creator/src", "src/classification", "src/training"):
    sys.path.insert(0, str(REPO / rel))
from direction_map import compute_direction_map, dim_schema, DM_VERSION  # noqa: E402
from band_concepts import band_math as bm  # noqa: E402
from band.band_model import BandModel  # noqa: E402
from band.band_scorer import score_letters  # noqa: E402
from fewshot_selection import select_typical  # noqa: E402

REF = REPO / "tests" / "_fewshot_ref"
LETTERS = [chr(65 + i) for i in range(26)]
# offline references per descriptor version (top-1, full test, merge on):
#   dm1 pre-merge graphs = the numbers of fs_root.py (Step 2 acceptance);
#   dm2 = post-merge graphs, production modules, 2026-09-25 (regression reference, see port_log).
REFERENCES = {
    "dm1": {"form": {2: 64.71, 4: 66.58, 10: 68.42}, "letter": {2: 65.70, 4: 67.23, 10: 68.09}},
    "dm2": {"form": {2: 66.83, 4: 69.39, 10: 71.57}, "letter": {2: 68.15, 4: 69.26, 10: 71.41}},
}
REFERENCE = REFERENCES[DM_VERSION]
POST_MERGE = "--post-merge" in sys.argv


def _merged(graph: nx.Graph) -> nx.Graph:
    sys.path.insert(0, str(REPO / "src" / "contour_analysis"))
    from networkx_graph_analysis import NetworkxGraphAnalysis
    analysis = NetworkxGraphAnalysis(graph, analysis_result_persistence_service=None, merge_threshold=10.0)
    analysis.merge_close_intersection_points()
    return analysis.graph if hasattr(analysis, "graph") else graph


def _dm(path: str) -> np.ndarray:
    graph = nx.node_link_graph(json.load(open(path)))
    if POST_MERGE:
        graph = _merged(graph)
    return compute_direction_map(graph)


def _forms(split, dirs, stems):
    """The glyph form is the file-name prefix (uA_00 -> uA). Directory names cannot be trusted:
    macOS is case-insensitive and the cache was created as 'ua' for the dataset directory 'uA'."""
    return [s.split("_")[0] for s in stems] if split.startswith("e52") else dirs


def load_split(split: str):
    """-> (class_dirs, file_stems, dm[n, 83]) in sorted order, cached per DM_VERSION."""
    tag = f"{DM_VERSION}{'_postmerge' if POST_MERGE else ''}"
    cache = REF / f"{tag}_{split}.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        return _forms(split, [str(c) for c in z["cls"]], [str(s) for s in z["stem"]]), [str(s) for s in z["stem"]], z["dm"]
    rows = []
    for cdir in sorted((REF / "skel_cache" / split).iterdir()):
        rows += [(cdir.name, f.name.replace(".png.json", ""), str(f)) for f in sorted(cdir.glob("*.json"))]
    with Pool(4) as pool:
        dm = np.array(pool.map(_dm, [r[2] for r in rows], chunksize=64))
    np.savez_compressed(cache, cls=np.array([r[0] for r in rows]), stem=np.array([r[1] for r in rows]), dm=dm)
    return _forms(split, [r[0] for r in rows], [r[1] for r in rows]), [r[1] for r in rows], dm


def build_model(budget, root_scope, tr_cls, tr_stem, tr_dm, ag_stem, ag_dm, weights, names, merge=True):
    aug_of = {}
    for j, stem in enumerate(ag_stem):
        aug_of.setdefault(stem.split("_aug")[0], []).append(j)
    tr_cls = np.array(tr_cls)
    ids, letters, forms, roles, lo, hi, centre = [], [], [], [], [], [], []
    counts, sums, sumsqs = [], [], []

    def add(band_id, letter, form, role, members):
        l, h, c = bm.percentile_band(members)
        ids.append(band_id); letters.append(letter); forms.append(form); roles.append(role)
        lo.append(l); hi.append(h); centre.append(c)
        if role == "leaf":
            counts.append(len(members)); sums.append(members.sum(0)); sumsqs.append((members**2).sum(0))

    for letter in LETTERS:
        letter_members = []
        for form, k in ((f"u{letter}", (budget + 1) // 2), (f"l{letter.lower()}", budget // 2)):
            pool_idx = np.where(tr_cls == form)[0]
            if not len(pool_idx) or k == 0:
                continue
            chosen = [int(pool_idx[i]) for i in select_typical(tr_dm[pool_idx], k)]
            members = [np.vstack([tr_dm[[i]], ag_dm[aug_of.get(tr_stem[i], [])]]) for i in chosen]
            groups = bm.merge_similar(tr_dm[chosen], members, weights) if merge and len(chosen) > 1 else [[g] for g in range(len(chosen))]
            for g in groups:
                add(f"{letter}_{form}_" + "+".join(tr_stem[chosen[i]].split("_")[-1] for i in g), letter, form, "leaf",
                    np.vstack([members[i] for i in g]))
            if root_scope == "form":
                add(f"{letter}_{form}_root", letter, form, "root", np.vstack(members))
            letter_members += members
        if root_scope == "letter" and letter_members:
            add(f"{letter}_root", letter, "*", "root", np.vstack(letter_members))
    scale = bm.pooled_scale(counts, sums, sumsqs)
    return BandModel(f"offline_B{budget}_{root_scope}", DM_VERSION, names, weights, scale, ids, letters, forms, roles, lo, hi, centre)


def main():
    t0 = time.time()
    names, blocks, grids = dim_schema()
    weights = bm.dim_weights(blocks, grids)
    tr_cls, tr_stem, tr_dm = load_split("e52_train")
    _, ag_stem, ag_dm = load_split("e52_train_aug")
    te_cls, _, te_dm = load_split("testfull")
    truth = np.array(te_cls)
    print(f"dm[{DM_VERSION}{' post-merge' if POST_MERGE else ''}]: train {len(tr_dm)}, aug {len(ag_dm)}, test {len(te_dm)}  [{time.time()-t0:.0f}s]", flush=True)
    worst = 0.0
    out = {}
    for root_scope in ("form", "letter"):
        for budget in (2, 4, 10):
            model = build_model(budget, root_scope, tr_cls, tr_stem, tr_dm, ag_stem, ag_dm, weights, names)
            ranked = [[s.letter for s in score_letters(x, model)[:3]] for x in te_dm]
            top1 = 100 * np.mean([r[0] == t for r, t in zip(ranked, truth)])
            top3 = 100 * np.mean([t in r for r, t in zip(ranked, truth)])
            ref = REFERENCE[root_scope][budget]
            worst = max(worst, abs(top1 - ref))
            n_leaf = sum(r == "leaf" for r in model.roles)
            print(f"root={root_scope:6s} B={budget:<2d} concepts {len(model.band_ids):3d} (leaves {n_leaf:3d}) | top-1 {top1:6.2f}  top-3 {top3:6.2f} | reference {ref:5.2f}  delta {top1-ref:+.2f}", flush=True)
            out[f"{root_scope}_B{budget}"] = {"top1": top1, "top3": top3, "pred": [r[0] for r in ranked]}
    tag = "postmerge" if POST_MERGE else "premerge"
    json.dump(out, open(REF / f"offline_predictions_{tag}.json", "w"))
    verdict = "PASS" if worst <= 0.05 else ("(side-check, no pass criterion)" if POST_MERGE and DM_VERSION == "dm1" else "FAIL")
    print(f"max |delta| vs reference: {worst:.3f} pp -> {verdict}  [{time.time()-t0:.0f}s]")


SKEL = {"skeletonization_threshold": 110, "simplification_epsilon": 4.55}


def _neo4j():
    from neo4j import GraphDatabase
    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "111122223333"))


def ingest_pool():
    import requests
    train = REPO / "tests" / "emnist52" / "train"
    forms = sorted(d for d in os.listdir(train) if (train / d).is_dir())
    expected = sum(len([f for f in os.listdir(train / d) if f.endswith(".png")]) for d in forms)
    driver = _neo4j()
    with driver.session() as s:
        s.run("MATCH (n) WHERE n.session_id STARTS WITH 'fs-pool-' DETACH DELETE n")
    t0 = time.time()
    for d in forms:
        requests.post("http://localhost:5002", timeout=120, json={"operation": "train", "parameters": {
            "dataset_path": f"/opt/nuclio/shared_storage/emnist52/train/{d}", "concept_name": d,
            "session_id": f"fs-pool-{d}", "direction_map": True, **SKEL}})
    print(f"pushed {len(forms)} form directories, {expected} images", flush=True)
    last, stable = -1, 0
    while stable < 6:
        time.sleep(10)
        with driver.session() as s:
            n = s.run("MATCH (f:GraphFeatures) WHERE f.session_id STARTS WITH 'fs-pool-' RETURN count(f) AS n").single()["n"]
        stable = stable + 1 if n == last else 0
        last = n
        print(f"  {n}/{expected} features  [{time.time()-t0:.0f}s]", flush=True)
    driver.close()


def features_parity():
    global POST_MERGE
    POST_MERGE = True
    stems, dms = [], []
    for split in ("e52_train", "e52_train_aug"):
        _, st, dm = load_split(split)
        stems += st; dms.append(dm)
    offline = dict(zip(stems, np.vstack(dms)))
    driver = _neo4j()
    with driver.session() as s:
        rows = s.run("MATCH (f:GraphFeatures) WHERE f.session_id STARTS WITH 'fs-pool-' RETURN f.image_path AS p, f.dm AS dm, f.dm_version AS v").data()
    driver.close()
    online = {os.path.basename(r["p"]).replace(".png", ""): np.array(r["dm"]) for r in rows if r["p"]}
    shared = sorted(set(online) & set(offline))
    diffs = np.array([np.abs(online[k] - offline[k]).max() for k in shared])
    cover = 100 * len(shared) / len(offline)
    exact = 100 * np.mean(diffs <= 1e-6)
    print(f"pipeline features {len(online)} | offline {len(offline)} | shared {len(shared)} ({cover:.1f}% of offline)")
    print(f"max|d| <= 1e-6: {exact:.1f}%   <= 1e-3: {100*np.mean(diffs<=1e-3):.1f}%   <= 0.05: {100*np.mean(diffs<=0.05):.1f}%   median {np.median(diffs):.2e}  worst {diffs.max():.3f}")
    print("only offline:", len(set(offline) - set(online)), "| only pipeline:", len(set(online) - set(offline)), "| dm_version:", {r["v"] for r in rows})
    worst = [shared[i] for i in np.argsort(-diffs)[:5]]
    print("worst files:", [(k, round(float(np.abs(online[k]-offline[k]).max()), 3)) for k in worst])
    print("PARITY (a):", "PASS" if cover >= 99 and exact >= 97 else "FAIL")


def bands_parity():
    global POST_MERGE
    POST_MERGE = True
    names, blocks, grids = dim_schema()
    weights = bm.dim_weights(blocks, grids)
    tr_cls, tr_stem, tr_dm = load_split("e52_train")
    _, ag_stem, ag_dm = load_split("e52_train_aug")
    driver = _neo4j(); ok = True
    for budget in (2, 4, 10):
        ref = build_model(budget, "form", tr_cls, tr_stem, tr_dm, ag_stem, ag_dm, weights, names)
        with driver.session() as s:
            m = s.run("MATCH (m:BandModel {model_id:$id}) RETURN m.scale AS scale, m.weights AS w, m.dm_version AS v", id=f"fs_B{budget}").single()
            rows = s.run("MATCH (:BandModel {model_id:$id})-[:HAS_CONCEPT]->(c) RETURN c.band_id AS id, c.role AS role, c.lo AS lo, c.hi AS hi, c.centre AS c, c.n AS n", id=f"fs_B{budget}").data()
        live = {r["id"]: r for r in rows}
        ref_ids = set(ref.band_ids)
        same_ids = ref_ids == set(live)
        worst = 0.0
        for i, bid in enumerate(ref.band_ids):
            if bid in live:
                worst = max(worst, np.abs(np.array(live[bid]["lo"]) - ref.lo[i]).max(), np.abs(np.array(live[bid]["hi"]) - ref.hi[i]).max(),
                            np.abs(np.array(live[bid]["c"]) - ref.centre[i]).max())
        d_scale = np.abs(np.array(m["scale"]) - ref.scale).max(); d_w = np.abs(np.array(m["w"]) - weights).max()
        passed = same_ids and worst <= 1e-9 and d_scale <= 1e-9 and d_w <= 1e-12
        ok &= passed
        print(f"fs_B{budget}: live {len(live)} concepts / offline {len(ref_ids)} | identical ids & grouping: {same_ids} | max|d| bands {worst:.2e} scale {d_scale:.2e} weights {d_w:.2e} -> {'ok' if passed else 'MISMATCH'}")
        if not same_ids:
            print("   only live:", sorted(set(live) - ref_ids)[:6], "| only offline:", sorted(ref_ids - set(live))[:6])
    driver.close()
    print("PARITY (b):", "PASS" if ok else "FAIL")


def pipeline_parity(dump_path: str, budget: int):
    z = np.load(REF / "dm1_postmerge_testfull.npz", allow_pickle=True)
    offline_pred = json.load(open(REF / "offline_predictions_postmerge.json"))[f"form_B{budget}"]["pred"]
    offline = dict(zip([str(s) for s in z["stem"]], offline_pred))
    rows = [json.loads(l) for l in open(dump_path)]
    n = len(rows); ok = [r for r in rows if r["status"] == "success" and r["ranked"]]
    stem = lambda r: os.path.basename(r["path"]).replace(".png", "")
    shared = [r for r in ok if stem(r) in offline]
    agree = np.mean([r["ranked"][0]["c"] == offline[stem(r)] for r in shared])
    acc_live = np.mean([r["ranked"][0]["c"] == r["true"] for r in shared]); acc_off = np.mean([offline[stem(r)] == r["true"] for r in shared])
    top3 = np.mean([r["true"] in [c["c"] for c in r["ranked"][:3]] for r in shared])
    print(f"B={budget}: submitted {n}, answered {len(ok)}, shared with offline {len(shared)}")
    print(f"  pipeline top-1 {100*acc_live:.2f}%  top-3 {100*top3:.2f}%  | offline top-1 on the same images {100*acc_off:.2f}%  | identical predictions {100*agree:.2f}%")
    print(f"  over ALL submitted images: top-1 {100*sum(r['ranked'][0]['c']==r['true'] for r in ok)/n:.2f}%")
    passed = abs(acc_live - acc_off) <= 0.015 and agree >= 0.95
    print("PARITY (c):", "PASS" if passed else "FAIL")


def replay(session_id: str, dump_path=None, dump_model="fs_B10"):
    """Score the kept direction maps of one session with every band model of the same dm_version."""
    from band.band_repository import load_band_models
    driver = _neo4j()
    models = load_band_models(driver)
    with driver.session() as s:
        rows = s.run("MATCH (f:GraphFeatures {session_id:$sid}) RETURN f.image_path AS p, f.dm AS dm, f.dm_version AS v", sid=session_id).data()
    driver.close()
    versions = {r["v"] for r in rows}
    if len(versions) != 1:
        raise SystemExit(f"session {session_id} mixes descriptor versions {versions}; use one session per dm_version")
    version = versions.pop()
    models = {k: m for k, m in models.items() if m.dm_version == version}
    feats = {r["p"]: np.array(r["dm"], float) for r in rows if r["p"]}
    truth = {p: p.split("/")[-2] for p in feats}
    print(f"{len(feats)} kept {version} direction maps from session {session_id}; models: {sorted(models)}")
    if dump_path:
        dump = {json.loads(l)["path"]: json.loads(l) for l in open(dump_path)}
        model = models[dump_model]
        same = sum(1 for p, x in feats.items() if dump[p]["ranked"] and score_letters(x, model)[0].letter == dump[p]["ranked"][0]["c"])
        print(f"replay == end-to-end ({dump_model}): {same}/{len(feats)} identical predictions")
    total = 20800
    for name in sorted(models, key=lambda k: int(k.split("B")[-1])):
        ranked = {p: [ls.letter for ls in score_letters(x, models[name])[:3]] for p, x in feats.items()}
        t1 = sum(ranked[p][0] == truth[p] for p in feats); t3 = sum(truth[p] in ranked[p] for p in feats)
        print(f"  {name}: answered top-1 {100*t1/len(feats):.2f}%  top-3 {100*t3/len(feats):.2f}%  | over all {total}: top-1 {100*t1/total:.2f}%  top-3 {100*t3/total:.2f}%")


def smoke_check(dump_path: str):
    base = {json.loads(l)["path"]: json.loads(l) for l in open(REF / "baseline_smoke.jsonl")}
    new = {json.loads(l)["path"]: json.loads(l) for l in open(dump_path)}
    ok = sum(1 for p in new if new[p]["status"] == "success")
    same = sum(1 for p in base if p in new and base[p]["ranked"] and new[p]["ranked"] and base[p]["ranked"][0]["cid"] == new[p]["ranked"][0]["cid"])
    leaked = [k for p in new for c in new[p]["ranked"][:1] for k in ("bs", "br") if c.get(k) is not None]
    print(f"success {ok}/{len(new)} | identical top-1 concept vs baseline: {same}/{len(base)} (run-to-run self-agreement was 49/52) | band fields set in off mode: {len(leaked)}")
    print("DEFAULT UNCHANGED:", "PASS" if ok == len(new) and same >= 47 and not leaked else "FAIL")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "offline":
        main()
    elif mode == "ingest-pool":
        ingest_pool()
    elif mode == "features":
        features_parity()
    elif mode == "bands":
        bands_parity()
    elif mode == "pipeline":
        pipeline_parity(sys.argv[2], int(sys.argv[3]))
    elif mode == "smoke":
        smoke_check(sys.argv[2])
    elif mode == "replay":
        replay(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None, sys.argv[4] if len(sys.argv) > 4 else "fs_B10")
    else:
        print(__doc__)
