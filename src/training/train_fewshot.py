"""Few-shot trainer for band concepts.

The teacher shows the system a handful of originals per letter (plus their augmentations):
  1. candidates mode (`--candidates-dir`, the final system): candidate originals, one directory per
     letter, are ingested once through the live pipeline; the system decides how many originals each
     letter needs (adaptive budget: the letter's own spread) and which ones (multi-start k-medoids,
     every common skeleton topology represented), augments the chosen ones and trains on them;
     or (`--train-dir`) a ready training set, one directory per glyph form, with the most typical
     originals of each form chosen by k-medoids;
  2. the training images are ingested through the live pipeline (session `<prefix><form>`), every
     message carrying SKEL below, so contour analysis stores their direction maps and centre lines;
  3. the concept_creator builds the band model: one leaf per original (band concept + shape concept),
     one root per glyph form;
  4. classification containers are restarted so every instance loads the new model.

Usage (repo root, pipeline up, LOCAL_STORAGE=./tests/) — the defaults are the measured best settings:
  python src/training/train_fewshot.py --candidates-dir emnist_cand60 --budget 10 --model-id fsp_B10
  python src/training/train_fewshot.py --train-dir mnist_fs --budget 99 --model-id mn_v13
Classify with the same SKEL parameters plus {"band_mode": "decide", "band_model": <model id>,
"committee_threshold": [150, 190]} (notes/scripts_pipeline/pl_dump.py).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import requests
from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fewshot_selection import SELECTION_SLICE, SELECTION_WEIGHTS, adaptive_budget, select_typical  # noqa: E402
from augment import write_copies
from infrastructure import verify_concept_created, wait_for_kafka_idle  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
STORAGE = REPO / "tests"                       # mounted at /opt/nuclio/shared_storage in the functions
CONNECTOR = "http://localhost:5002"
CONCEPT_CREATOR = "http://localhost:5056"
SKEL = {"skeletonization_threshold": 110, "simplification_epsilon": 4.55, "thick_stroke_threshold": 170, "bridge_protect_stems": True, "dense_features": True, "deslant": True, "normalisation": "moment", "moment_range": 1.7, "bridge_components": True}
POOL_PREFIX = "fs-pool-"      # overridden by --pool-prefix so several training sets can coexist


def _driver():
    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "111122223333"))


def letter_of(form: str) -> str:
    """`uA` / `la` -> `A`; a plain class directory is its own letter."""
    return form[1].upper() if len(form) == 2 and form[0] in "ul" else form


def list_forms(train_dir: str) -> List[str]:
    root = STORAGE / train_dir
    return sorted(d for d in os.listdir(root) if (root / d).is_dir())


def ingest_pool(train_dir: str, forms: List[str]) -> int:
    expected = 0
    with _driver() as driver, driver.session() as s:
        s.run("MATCH (n) WHERE n.session_id STARTS WITH $p DETACH DELETE n", p=POOL_PREFIX)
    for form in forms:
        expected += len([f for f in os.listdir(STORAGE / train_dir / form) if f.lower().endswith(".png")])
        requests.post(CONNECTOR, timeout=120, json={"operation": "train", "parameters": {
            "dataset_path": f"/opt/nuclio/shared_storage/{train_dir}/{form}", "concept_name": form,
            "session_id": f"{POOL_PREFIX}{form}", "direction_map": True, **SKEL}})
    return expected


def wait_for_graph_features(expected: int, stable_polls: int = 5, poll: float = 8.0, prefix: str = None) -> int:
    prefix = prefix or POOL_PREFIX
    last, stable, t0 = -1, 0, time.time()
    with _driver() as driver:
        while stable < stable_polls:
            time.sleep(poll)
            with driver.session() as s:
                n = s.run("MATCH (f:GraphFeatures) WHERE f.session_id STARTS WITH $p RETURN count(f) AS n",
                          p=prefix).single()["n"]
            stable = stable + 1 if n == last else 0
            last = n
            print(f"  features {n}/{expected}  [{time.time()-t0:.0f}s]", flush=True)
            if n >= expected:
                break
        with driver.session() as s:     # the pool is never folded: its node-level graphs are dead weight
            while s.run("MATCH (n) WHERE (n:Point OR n:Vector) AND n.session_id STARTS WITH $p "
                        "WITH n LIMIT 20000 DETACH DELETE n RETURN count(n) AS n", p=prefix).single()["n"]:
                pass
    return last


def load_pool_features(form: str, session_id: str = None) -> Dict[str, np.ndarray]:
    with _driver() as driver, driver.session() as s:
        rows = s.run("MATCH (f:GraphFeatures {session_id: $sid}) RETURN f.image_path AS p, f.dm AS dm",
                     sid=session_id or f"{POOL_PREFIX}{form}").data()
    return {os.path.splitext(os.path.basename(r["p"]))[0]: np.array(r["dm"], float) for r in rows if r["p"]}


def select_from_candidates(candidates_dir: str, total: int, copies: int, reuse: bool) -> tuple:
    """The system decides how many originals each letter needs. Candidates (originals only, one directory per
    letter) are ingested once as `<prefix>cand-<letter>`; the letters' own spread sets k per letter for the
    total budget; the chosen originals get augmented copies in `<candidates_dir>_sel/` which becomes the
    training set. -> (train_dir, {letter: [stems]})"""
    letters = list_forms(candidates_dir)
    cand_session = {L: f"cand-{POOL_PREFIX}{L}" for L in letters}
    if not reuse:
        with _driver() as driver, driver.session() as s:
            s.run("MATCH (n) WHERE n.session_id STARTS WITH $p DETACH DELETE n", p=f"cand-{POOL_PREFIX}")
        expected = 0
        for L in letters:
            expected += len([f for f in os.listdir(STORAGE / candidates_dir / L) if f.lower().endswith(".png")])
            requests.post(CONNECTOR, timeout=120, json={"operation": "train", "parameters": {
                "dataset_path": f"/opt/nuclio/shared_storage/{candidates_dir}/{L}", "concept_name": L,
                "session_id": cand_session[L], "direction_map": True, **SKEL}})
        print(f"ingesting {expected} candidates of {len(letters)} letters", flush=True)
        wait_for_graph_features(expected, prefix=f"cand-{POOL_PREFIX}")
    pools, stems = {}, {}
    for L in letters:
        feats = load_pool_features(L, cand_session[L])
        stems[L] = sorted(feats)
        pools[L] = np.vstack([feats[st] for st in stems[L]])
    plan = adaptive_budget(pools, total, stratify=True)
    chosen = {L: [stems[L][i] for i in idx] for L, (k, idx) in plan.items()}
    print("originals per letter: " + " ".join(f"{L}{k}" for L, (k, _) in sorted(plan.items())), flush=True)
    train_dir = f"{candidates_dir}_sel"
    if (STORAGE / train_dir).exists():
        shutil.rmtree(STORAGE / train_dir)          # a previous selection must not leak into the new pool
    for L, sel in chosen.items():
        for st in sel:
            write_copies(str(STORAGE / candidates_dir / L / f"{st}.png"), str(STORAGE / train_dir / L), copies)
    return train_dir, chosen


def select_originals(forms: List[str], budget: int) -> Dict[str, List[str]]:
    """Budget is per LETTER and is split between the letter's glyph forms (upper case first)."""
    by_letter: Dict[str, List[str]] = {}
    for form in forms:
        by_letter.setdefault(letter_of(form), []).append(form)
    chosen: Dict[str, List[str]] = {}
    for letter, letter_forms in by_letter.items():
        letter_forms.sort(key=lambda f: (not f[0] == "u", f))
        m = len(letter_forms)
        for i, form in enumerate(letter_forms):
            k = budget // m + (1 if i < budget % m else 0)
            if k == 0:
                continue
            pool = load_pool_features(form)
            originals = sorted(n for n in pool if "_aug" not in n)
            if not originals:
                print(f"  WARNING: no direction maps for form {form}")
                continue
            picked = select_typical(np.vstack([pool[n] for n in originals]), k)
            chosen[form] = [originals[j] for j in picked]
    return chosen


def build_model(model_id: str, chosen: Dict[str, List[str]], merge_similar: bool, root_scope: str,
                alpha: float, leaf_weight: float, stage2_lambda: float) -> dict:
    forms = {form: {"letter": letter_of(form), "session_id": f"{POOL_PREFIX}{form}", "originals": originals}
             for form, originals in chosen.items()}
    body = {"operation": "build_band_model", "model_id": model_id, "forms": forms,
            "merge_similar": merge_similar, "root_scope": root_scope, "alpha": alpha, "leaf_weight": leaf_weight,
            "stage2_lambda": stage2_lambda}
    r = requests.post(CONCEPT_CREATOR, data=json.dumps(body), headers={"Content-Type": "text/plain"}, timeout=300)
    r.raise_for_status()
    return r.json()


def _push_files(train_dir: str, form: str, stems: List[str], session_id: str) -> None:
    for stem in stems:
        requests.post(CONNECTOR, timeout=60, json={"operation": "train", "parameters": {
            "dataset_path": f"/opt/nuclio/shared_storage/{train_dir}/{form}/{stem}.png", "concept_name": letter_of(form),
            "session_id": session_id, **SKEL}})


def _fold(session_id: str, concept_id: str) -> bool:
    body = json.dumps({"session_id": session_id, "concept_id": concept_id, "concept_name": concept_id.split("_")[0]})
    try:
        r = requests.post(CONCEPT_CREATOR, data=body, headers={"Content-Type": "text/plain"}, timeout=180)
    except requests.RequestException:
        return False
    return r.status_code == 200 and verify_concept_created(concept_id)


def fold_leaves(model_id: str, train_dir: str) -> dict:
    """Structural concept per band leaf, used ONLY to explain a decision (maximum common subgraph).
    The fold is the existing intersection fold over the leaf's own images; it may fail when an
    augmentation changes the topology, in which case the leaf simply has no structural explanation."""
    with _driver() as driver, driver.session() as s:
        leaves = s.run("MATCH (:BandModel {model_id:$id})-[:HAS_CONCEPT]->(c:BandConcept {role:'leaf'}) "
                       "RETURN c.band_id AS band_id, c.form AS form, c.member_files AS files, c.originals AS originals "
                       "ORDER BY c.band_id", id=model_id).data()
        existing = {r["c"] for r in s.run("MATCH (n:Point) WHERE n.concept_kind = 'leaf_explainer' RETURN DISTINCT n.concept_id AS c")}
    todo = [l for l in leaves if l["band_id"] not in existing]
    for leaf in todo:
        _push_files(train_dir, leaf["form"], leaf["files"], f"fs-leaf-{leaf['band_id']}")
    if todo:
        wait_for_kafka_idle("contour-analysis-output-topic", idle_timeout=10)
    folded, retried, failed = [l["band_id"] for l in leaves if l["band_id"] in existing], [], []
    with _driver() as driver:
        for leaf in todo:
            band_id, session = leaf["band_id"], f"fs-leaf-{leaf['band_id']}"
            ok = _fold(session, band_id)
            if not ok:                      # keep the originals and the augmentations closest to them
                pool = load_pool_features(leaf["form"])
                keep = list(leaf["originals"])
                for original in leaf["originals"]:
                    augs = [f for f in leaf["files"] if f.startswith(f"{original}_aug") and f in pool]
                    dist = [float((((pool[a] - pool[original])[SELECTION_SLICE]) ** 2 /
                                   (np.abs(pool[a][SELECTION_SLICE]) + np.abs(pool[original][SELECTION_SLICE]) + 1e-9)
                                   * SELECTION_WEIGHTS).sum()) for a in augs]
                    keep += [augs[i] for i in np.argsort(dist)[:5]]
                with driver.session() as s:
                    s.run("MATCH (n {session_id:$sid}) WHERE n.concept_id IS NULL DETACH DELETE n", sid=session)
                _push_files(train_dir, leaf["form"], keep, session)
                wait_for_kafka_idle("contour-analysis-output-topic", idle_timeout=6)
                ok = _fold(session, band_id)
                if ok:
                    retried.append(band_id)
            with driver.session() as s:
                if ok:
                    s.run("MATCH (n {concept_id:$c}) SET n.concept_kind = 'leaf_explainer'", c=band_id)
                    folded.append(band_id)
                else:
                    failed.append(band_id)
                # A folded concept inherits the session_id its images shared, so the session
                # clean-up must never match concept nodes (the fold already removed its images).
                s.run("MATCH (n {session_id:$sid}) WHERE n.concept_id IS NULL DETACH DELETE n", sid=session)
        with driver.session() as s:
            s.run("MATCH (:BandModel {model_id:$id})-[:HAS_CONCEPT]->(c:BandConcept {role:'leaf'}) "
                  "WHERE c.band_id IN $ok SET c.structural_concept_id = c.band_id", id=model_id, ok=folded)
    return {"leaves": len(leaves), "with_structural_concept": len(folded), "needed_retry": len(retried), "failed": failed}


def restart_classification(wait: float = 45.0) -> None:
    names = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True).stdout.split()
    for name in [n for n in names if n.startswith("nuclio-nuclio-classification")]:
        subprocess.run(["docker", "restart", name], capture_output=True)
    time.sleep(wait)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-dir", help="relative to tests/, one sub-directory per glyph form (originals + augs)")
    ap.add_argument("--candidates-dir", help="relative to tests/, one directory per letter with candidate originals: "
                    "the system picks how many and which (adaptive budget), augments them and trains on the result")
    ap.add_argument("--copies", type=int, default=10, help="augmented copies per chosen original (candidates mode)")
    ap.add_argument("--budget", type=int, required=True, help="originals per letter")
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--root-scope", default="form", choices=["form", "letter"])
    ap.add_argument("--merge-similar", action="store_true", help="merge originals whose augmentations overlap into one leaf (off measured better)")
    ap.add_argument("--reuse-pool", action="store_true", help="skip ingestion if the pool features are already in Neo4j")
    ap.add_argument("--originals-file", help="JSON {form: [file stems]} to override the typical-medoid selection")
    ap.add_argument("--restart-classification", action="store_true")
    ap.add_argument("--pool-prefix", default="fs-pool-", help="session prefix of the ingested pool (one per training set)")
    ap.add_argument("--alpha", type=float, default=10.0, help="weight of the distance-to-centre term of a band concept")
    ap.add_argument("--leaf-weight", type=float, default=0.5, help="leaf share of the letter score, the root gets the rest")
    ap.add_argument("--stage2-lambda", type=float, default=1.0, help="weight of round 2 (shape concepts) over the band top-5; 0 = off")
    ap.add_argument("--fold-leaves", action="store_true", help="also fold a structural concept per leaf (explanations only)")
    ap.add_argument("--skip-build", action="store_true", help="keep the stored band model (use with --fold-leaves)")
    args = ap.parse_args()
    global POOL_PREFIX
    POOL_PREFIX = args.pool_prefix

    if not args.train_dir and not args.candidates_dir:
        ap.error("--train-dir or --candidates-dir is required")
    if args.candidates_dir:
        train_dir, chosen_from_pool = select_from_candidates(
            args.candidates_dir, args.budget * 26, args.copies, args.reuse_pool)
        args.train_dir = train_dir
        args.root_scope = "form"
        args.originals_file = None
        args.reuse_pool = False
    forms = list_forms(args.train_dir)
    if args.skip_build:
        if args.fold_leaves:
            print(json.dumps(fold_leaves(args.model_id, args.train_dir)), flush=True)
        if args.restart_classification:
            restart_classification()
        return
    if not args.reuse_pool:
        expected = ingest_pool(args.train_dir, forms)
        print(f"ingesting {expected} images of {len(forms)} glyph forms", flush=True)
        wait_for_graph_features(expected)
    if args.candidates_dir:
        chosen = chosen_from_pool
    else:
        chosen = json.load(open(args.originals_file)) if args.originals_file else select_originals(forms, args.budget)
    result = build_model(args.model_id, chosen, args.merge_similar, args.root_scope, args.alpha, args.leaf_weight,
                         args.stage2_lambda)
    out = REPO / "tests" / "_fewshot_ref" / f"selection_{args.model_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(chosen, open(out, "w"), indent=1)
    print(json.dumps(result), flush=True)
    print(f"selection saved to {out}")
    if args.fold_leaves:
        print(json.dumps(fold_leaves(args.model_id, args.train_dir)), flush=True)
    if args.restart_classification:
        restart_classification()


if __name__ == "__main__":
    main()
