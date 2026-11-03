"""M — rebuild Nikita's 13 ComAN concepts under the compliant protocol and switch the active concept set.

  ingest  [subs] --tag t110 --thr 110 --eps 4.55 [--extra '{"bridge_protect_stems": true}']
          send tests/_isl_train/<sub>/*.png through the live pipeline (operation train, session coman-<tag>-<sub>) with
          the given detector, without folding
  export  [subs] --tag t110
          dump every image graph of those sessions as node-link JSON -> tests/_isl/coman_graphs/<tag>/<sub>/<file>.json
  fold    [subs] --tag t110 --set <name> [--interval majority --tau 0.8] [--orders 3] [--write]
          his chain (pairwise max common minor, f = 1) with the concept creator's own code, files in sorted order
          (the first original seeds the concept); an example the concept cannot absorb (no common minor) is skipped
          and counted instead of aborting the concept; --orders N also folds N-1 shuffled orders (Theorem 2);
          concepts -> tests/_isl/coman_sets/<name>.json, and with --write into Neo4j as <d>_<sub>s<name>, inactive
  fold    ... --mode accumulate --taus 1.0,0.8
          his accumulating hypergraph instead of the chain (lab log P5): seed = the first original, every other example
          aligned to the seed (M_k = max common minor), counters f over the absorbed examples for the seed's nodes,
          attractor = f >= tau glued by the contracted seed structure (component of the StartPoint); one set per tau,
          named <name>1 (tau 1.0) / <name>8 (tau 0.8); --orders N checks the order-freedom, plus a second-original
          seed (Theorem 2)
  load <concept_graphs.json>  write a run folder's concepts (ids <sub>s<set>) into Neo4j under their sets, inactive
  activate <name|nikita>...  make those sets the only active structural sets (others: concept_kind='coman_off')
  restart                  restart the classification containers so they reload their concept cache
  status                   active / tagged concepts
"""
import argparse
import copy
import json
import logging
import os
import random
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import networkx as nx
import requests
from neo4j import GraphDatabase

REPO = Path(__file__).resolve().parents[2]
TRAIN = REPO / "tests" / "_isl_train"          # --train-dir picks another folder under tests/
GRAPHS = REPO / "tests" / "_isl" / "coman_graphs"
SETS = REPO / "tests" / "_isl" / "coman_sets"
CONNECTOR = "http://localhost:5002"
SUBS = sorted(p.name for p in TRAIN.iterdir() if p.is_dir() and not p.name.startswith("_"))
DROP = {"id", "uuid", "is_concept", "concept_id", "image_id", "image_path", "node_key", "session_id"}


def driver():
    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "111122223333"))


def ingest(subs, tag, thr, eps, extra=None):
    expected = 0
    for sub in subs:
        files = sorted((TRAIN / sub).glob("*.png"))
        expected += len(files)
        for f in files:
            requests.post(CONNECTOR, timeout=60, json={"operation": "train", "parameters": {
                "dataset_path": f"/opt/nuclio/shared_storage/{TRAIN.name}/{sub}/{f.name}", "concept_name": sub.split("_")[0],
                "session_id": f"coman-{tag}-{sub}", "skeletonization_threshold": thr, "simplification_epsilon": eps,
                **(extra or {})}})
    last, stable = -1, 0
    with driver() as d, d.session() as s:
        while stable < 4:
            time.sleep(6)
            n = s.run("MATCH (p:Point) WHERE p.session_id STARTS WITH $pre AND p.concept_id IS NULL "
                      "RETURN count(DISTINCT p.image_id) AS n", pre=f"coman-{tag}-").single()["n"]
            stable = stable + 1 if n == last else 0
            last = n
            print(f"  images with a graph: {n}/{expected}", flush=True)


def export(subs, tag):
    sys.path.insert(0, str(REPO / "src" / "concept_creator"))
    from src.neo4j_to_networkx import Neo4jToNetworkx
    with driver() as d, d.session() as s:
        for sub in subs:
            ids = [r["i"] for r in s.run("MATCH (p:Point {session_id: $sid}) RETURN DISTINCT p.image_id AS i",
                                         sid=f"coman-{tag}-{sub}").data()]
            out = GRAPHS / tag / sub
            out.mkdir(parents=True, exist_ok=True)
            seen = set()
            for iid in ids:
                g = Neo4jToNetworkx.extract_image_graph(s, iid)
                path = next((nd.get("image_path") for _, nd in g.nodes(data=True) if nd.get("image_path")), iid)
                stem = Path(path).stem
                if stem in seen:                      # a file ingested twice: keep one graph
                    continue
                seen.add(stem)
                for _, nd in g.nodes(data=True):
                    if isinstance(nd.get("labels"), set):
                        nd["labels"] = sorted(nd["labels"])
                (out / f"{stem}.json").write_text(json.dumps(nx.node_link_data(g, edges="edges", name="node_key"), default=str))
            print(f"{sub}: {len(seen)} graphs exported ({len(list((TRAIN / sub).glob('*.png')))} files)")


def _probe():
    for p in (REPO / "src" / "concept_creator", REPO / "src" / "concept_creator" / "visualization", REPO / "common"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    logging.disable(logging.CRITICAL)
    import probe_concept_formation as probe
    return probe


def load_graphs(tag, sub):
    graphs = {}
    for f in sorted((GRAPHS / tag / sub).glob("*.json")):
        g = nx.node_link_graph(json.loads(f.read_text()), edges="edges", name="node_key")
        for _, nd in g.nodes(data=True):
            nd["labels"] = list(nd.get("labels", []))        # the concept creator appends to a list
        graphs[f.stem] = g
    return graphs


def _prepare(graphs, order):
    """Start point over all graphs of the subclass (graphs without it are dropped) and the visitors, as the concept
    creator does. -> (service, {id: graph} in `order`, dropped ids)"""
    probe = _probe()
    ordered = {i: copy.deepcopy(graphs[i]) for i in order}
    dropped_start = []
    while True:                                   # a graph without the subclass' start point cannot take part
        try:
            ordered = probe._determine_start_point(ordered, probe.logger)
            break
        except ValueError as exc:
            bad = str(exc).rsplit(" ", 1)[-1]
            if not str(exc).startswith("No start point found for graph") or bad not in ordered:
                raise
            dropped_start.append(bad)
            del ordered[bad]
    service = probe._build_offline_service()
    for i, g in ordered.items():
        ordered[i] = probe._analyze_graph(g)
    return service, ordered, dropped_start


def fold_chain(graphs, order):
    """His chain C_k = MCM(C_{k-1}, G_k) over `order`; non-absorbable examples are skipped. -> (concept, stats)."""
    service, ordered, dropped_start = _prepare(graphs, order)
    ids = list(ordered)
    concept, absorbed, skipped = ordered[ids[0]], [ids[0]], []
    for i in ids[1:]:
        try:
            res = service.graph_minor_finder.find_max_common_minor(copy.deepcopy(concept), copy.deepcopy(ordered[i]))
        except Exception:                         # noqa: BLE001 — any failure = the example is not absorbed
            res = None
        if res is None or res.number_of_nodes() == 0:
            skipped.append(i)
            continue
        concept = res
        absorbed.append(i)
    return concept, {"absorbed": len(absorbed), "skipped": len(skipped), "no_start": len(dropped_start),
                     "seed": ids[0], "nodes": concept.number_of_nodes(), "edges": concept.number_of_edges(),
                     "originals_absorbed": sum(1 for i in absorbed if "_aug" not in i)}


def align_to_seed(graphs, seed=None):
    """M_k = max common minor of the seed and every other example (nodes keyed by the seed's ids). -> (seed id, seed
    graph, [(example id, M_k)] for the absorbed examples, skipped ids, dropped ids)"""
    service, ordered, dropped = _prepare(graphs, sorted(graphs))
    originals = sorted(i for i in ordered if "_aug" not in i)
    seed_id = seed if seed in ordered else (originals[0] if originals else next(iter(ordered)))
    seed_g = ordered[seed_id]
    aligned, skipped = [], []
    for i, g in ordered.items():
        if i == seed_id:
            continue
        try:
            m = service.graph_minor_finder.find_max_common_minor(copy.deepcopy(seed_g), copy.deepcopy(g))
        except Exception:                         # noqa: BLE001 — any failure = the example is not absorbed
            m = None
        if m is None or m.number_of_nodes() == 0:
            skipped.append(i)
        else:
            aligned.append((i, m))
    return seed_id, seed_g, aligned, skipped, dropped


def accumulate(seed_id, seed_g, aligned, tau, order=None):
    """His accumulating hypergraph on the seed: f(n) over the absorbed examples, attractor = seed nodes with f >= tau,
    glued by the seed's own structure contracted over the removed nodes (a removed node between two others is replaced
    by an edge joining them — an edge contraction, so the attractor is a minor of the seed); the connected component of
    the StartPoint. Properties: merge_values over the minors; labels: their intersection."""
    from src.property_handlers.property_handlers import merge_values
    seq = [aligned[i] for i in order] if order is not None else aligned
    nf, props, labels = Counter(), {}, {}
    for _, m in seq:
        for n, d in m.nodes(data=True):
            if n not in seed_g:
                continue
            nf[n] += 1
            lab = set(d.get("labels", []))
            labels[n] = labels[n] & lab if n in labels else lab
            acc = props.setdefault(n, {})
            for k, v in d.items():
                if k != "labels":
                    acc[k] = merge_values(acc[k], v) if k in acc else v
    n_abs = len(seq)
    if n_abs == 0:
        return copy.deepcopy(seed_g)
    keep = {n for n in seed_g if nf[n] >= tau * n_abs - 1e-9}
    h = nx.Graph(seed_g.edges())
    h.add_nodes_from(seed_g.nodes())
    for n in sorted(set(seed_g) - keep, key=str):
        nb = list(h.neighbors(n))
        if len(nb) == 2:
            h.add_edge(*nb)
        h.remove_node(n)
    g = nx.Graph()
    for n in sorted(keep, key=str):
        g.add_node(n, **{k: v for k, v in props[n].items() if v is not None}, labels=sorted(labels[n]))
    g.add_edges_from(e for e in h.edges() if e[0] != e[1])
    start = next((n for n in g if "StartPoint" in g.nodes[n]["labels"]), None)
    return g.subgraph(nx.node_connected_component(g, start)).copy() if start is not None else nx.Graph()


def fold_accumulate(graphs, taus, seed=None):
    """-> {tau: (concept, stats)} from one alignment pass."""
    seed_id, seed_g, aligned, skipped, dropped = align_to_seed(graphs, seed)
    out = {}
    for tau in taus:
        c = accumulate(seed_id, seed_g, aligned, tau)
        out[tau] = (c, {"absorbed": len(aligned) + 1, "skipped": len(skipped), "no_start": len(dropped), "seed": seed_id,
                        "nodes": c.number_of_nodes(), "edges": c.number_of_edges(), "tau": tau,
                        "originals_absorbed": 1 + sum(1 for i, _ in aligned if "_aug" not in i)})
    return out, (seed_id, seed_g, aligned)


def _same(a, b):
    return nx.is_isomorphic(a, b, node_match=lambda x, y: set(x.get("labels", ())) == set(y.get("labels", ())))


def _set_name(name, tau):
    return f"{name}{'1' if tau >= 1.0 else int(round(tau * 10))}"


def fold(subs, tag, name, interval, tau, orders, write, mode="chain", taus=(1.0, 0.8)):
    if interval == "majority":
        os.environ["CONCEPT_INTERVAL_MODE"] = "majority"
        os.environ["CONCEPT_INTERVAL_TAU"] = str(tau)
    SETS.mkdir(parents=True, exist_ok=True)
    if mode == "accumulate":
        outs = {t: {} for t in taus}
        for sub in subs:
            graphs = load_graphs(tag, sub)
            res, (seed_id, seed_g, aligned) = fold_accumulate(graphs, taus)
            originals = sorted(i for i in graphs if "_aug" not in i)
            second = next((o for o in originals if o != seed_id), None)
            res2 = fold_accumulate(graphs, taus, seed=second)[0] if second else {}
            for t in taus:
                concept, st = res[t]
                iso = []
                for k in range(1, orders):           # Theorem 2: the same minors, presented in another order
                    idx = list(range(len(aligned)))
                    random.Random(k).shuffle(idx)
                    other = accumulate(seed_id, seed_g, aligned, t, idx)
                    iso.append(set(other.nodes) == set(concept.nodes) and set(map(frozenset, other.edges)) ==
                               set(map(frozenset, concept.edges)))
                seed2 = _same(concept, res2[t][0]) if second else None
                print(f"{sub} tau {t}: {st}; orders identical {sum(iso)}/{len(iso)}; second seed isomorphic {seed2}",
                      flush=True)
                outs[t][sub] = {"stats": st, "orders_isomorphic": iso, "second_seed_isomorphic": seed2,
                                "second_seed_stats": res2[t][1] if second else None,
                                "graph": nx.node_link_data(concept, edges="edges", name="node_key")}
        for t in taus:
            nm = _set_name(name, t)
            (SETS / f"{nm}.json").write_text(json.dumps(outs[t], default=str))
            if write:
                _write_set(nm, outs[t])
        return
    out = {}
    for sub in subs:
        graphs = load_graphs(tag, sub)
        concept, st = fold_chain(graphs, sorted(graphs))
        iso = []
        for seed in range(1, orders):
            ids = sorted(graphs)
            random.Random(seed).shuffle(ids)
            other, _ = fold_chain(graphs, ids)
            iso.append(_same(concept, other))
        print(f"{sub}: {st}" + (f"; other orders isomorphic: {sum(iso)}/{len(iso)}" if iso else ""), flush=True)
        out[sub] = {"stats": st, "orders_isomorphic": iso,
                    "graph": nx.node_link_data(concept, edges="edges", name="node_key")}
    (SETS / f"{name}.json").write_text(json.dumps(out, default=str))
    if write:
        _write_set(name, out)


def _write_set(name, out):
    sys.path.insert(0, str(REPO / "src" / "concept_creator"))
    from src.networkx_to_neo4j import NetworkxToNeo4j
    with driver() as d, d.session() as s:
        s.run("MATCH (n {coman_set: $name}) DETACH DELETE n", name=name)
        written = 0
        for sub, rec in out.items():
            if rec["stats"]["originals_absorbed"] < 2:     # rule 1: an attractor is a reduction over a SET
                print(f"{sub}: only {rec['stats']['originals_absorbed']} original absorbed — not written")
                continue
            g = nx.node_link_graph(rec["graph"], edges="edges", name="node_key")
            if g.number_of_nodes() == 0:
                print(f"{sub}: empty attractor — not written")
                continue
            for _, nd in g.nodes(data=True):
                nd["labels"] = set(nd.get("labels", []))
                for k in DROP & set(nd):
                    del nd[k]
                nd["coman_set"] = name
                nd["concept_kind"] = "coman_off"
            s.execute_write(NetworkxToNeo4j.create_structure, g, f"{sub}s{name}")
            written += 1
    print(f"wrote set {name}: {written} of {len(out)} concepts (inactive)")


def load(path):
    """Write the concepts of a run folder's concept_graphs.json (id <sub>s<set> -> node-link graph) into Neo4j under
    their sets, inactive — the same concepts without refolding; then `activate <set>...`."""
    sys.path.insert(0, str(REPO / "src" / "concept_creator"))
    from src.networkx_to_neo4j import NetworkxToNeo4j
    snap = json.loads(Path(path).read_text())
    with driver() as d, d.session() as s:
        for cid, data in snap.items():
            name = cid.split("s", 1)[1]
            s.run("MATCH (n {concept_id: $cid}) DETACH DELETE n", cid=cid)
            g = nx.node_link_graph(data, edges="edges", name="node_key")
            for _, nd in g.nodes(data=True):
                nd["labels"] = set(nd.get("labels", []))
                for k in DROP & set(nd):
                    del nd[k]
                nd["coman_set"] = name
                nd["concept_kind"] = "coman_off"
            s.execute_write(NetworkxToNeo4j.create_structure, g, cid)
    print(f"loaded {len(snap)} concepts (inactive): {dict(Counter(c.split('s', 1)[1] for c in snap))}")


def activate(names):
    with driver() as d, d.session() as s:
        s.run("MATCH (n) WHERE n.concept_id IS NOT NULL AND n.concept_kind IS NULL SET n.concept_kind = 'coman_off'")
        for name in names:
            pred = "n.isl_restored = true" if name == "nikita" else "n.coman_set = $name"
            s.run(f"MATCH (n) WHERE {pred} AND n.concept_kind = 'coman_off' REMOVE n.concept_kind", name=name)
    status()


def status():
    with driver() as d, d.session() as s:
        rows = s.run("MATCH (n:Point) WHERE n.concept_id IS NOT NULL RETURN coalesce(n.concept_kind, 'active') AS kind, "
                     "collect(DISTINCT n.concept_id) AS ids").data()
    for r in rows:
        ids = sorted(r["ids"])
        print(f"{r['kind']}: {len(ids)}" + (f" {ids}" if r["kind"] == "active" else ""))


def restart():
    names = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"], capture_output=True, text=True).stdout.split()
    cls = [n for n in names if n.startswith("nuclio-nuclio-classification")]
    subprocess.run(["docker", "restart", *cls], capture_output=True, check=True)
    for _ in range(40):
        time.sleep(5)
        st = subprocess.run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], capture_output=True, text=True).stdout
        healthy = sum(1 for line in st.splitlines() if line.startswith("nuclio-nuclio-classification") and "healthy" in line
                      and "unhealthy" not in line)
        if healthy == len(cls):
            break
    print(f"classification containers healthy: {healthy}/{len(cls)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["ingest", "export", "fold", "load", "activate", "restart", "status"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--tag", default="t110")
    ap.add_argument("--thr", type=int, default=110)
    ap.add_argument("--eps", type=float, default=4.55)
    ap.add_argument("--extra", default="{}", help="more skeleton parameters (JSON), e.g. {\"bridge_protect_stems\": true}")
    ap.add_argument("--set", default="")
    ap.add_argument("--interval", default="minmax", choices=["minmax", "majority"])
    ap.add_argument("--tau", type=float, default=0.8)
    ap.add_argument("--orders", type=int, default=1)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--mode", default="chain", choices=["chain", "accumulate"])
    ap.add_argument("--taus", default="1.0,0.8", help="accumulate: one set per tau")
    ap.add_argument("--train-dir", default="_isl_train", help="folder under tests/ with <subclass>/*.png")
    a = ap.parse_args()
    global TRAIN
    TRAIN = REPO / "tests" / a.train_dir
    subs = a.args or (sorted(p.name for p in TRAIN.iterdir() if p.is_dir() and not p.name.startswith("_"))
                      if a.cmd in ("ingest", "export", "fold") else [])
    if a.cmd == "ingest":
        ingest(subs, a.tag, a.thr, a.eps, json.loads(a.extra))
    elif a.cmd == "export":
        export(subs, a.tag)
    elif a.cmd == "fold":
        fold(subs, a.tag, a.set, a.interval, a.tau, a.orders, a.write, a.mode, tuple(map(float, a.taus.split(","))))
    elif a.cmd == "load":
        load(a.args[0])
    elif a.cmd == "activate":
        activate(a.args)
    elif a.cmd == "restart":
        restart()
    else:
        status()


if __name__ == "__main__":
    main()
