"""A0 — is the structural attractor independent of the presentation order? (manuscript eq. 39–40, Theorem 2, §III.7.1)

  ingest <sub>...   send tests/_isl_train/<sub>/*.png through the live pipeline (session isl-ord-<sub>, D = 110/4.55,
                    the classification parameters) without folding
  export <sub>...   dump every image graph of those sessions as node-link JSON -> tests/_isl/order/<sub>/
  fold <sub>... [--orders 5]
                    fold the graphs with the concept creator's own code (start point + pairwise max common minor, as in
                    visualization/probe_concept_formation.py) in several presentation orders and compare the results
"""
import argparse
import copy
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

import networkx as nx
import requests
from neo4j import GraphDatabase

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "tests" / "_isl" / "order"
CONNECTOR = "http://localhost:5002"
SKEL = {"skeletonization_threshold": 110, "simplification_epsilon": 4.55}


def driver():
    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "111122223333"))


def ingest(subs):
    expected = 0
    for sub in subs:
        files = sorted((REPO / "tests" / "_isl_train" / sub).glob("*.png"))
        expected += len(files)
        for f in files:
            requests.post(CONNECTOR, timeout=60, json={"operation": "train", "parameters": {
                "dataset_path": f"/opt/nuclio/shared_storage/_isl_train/{sub}/{f.name}", "concept_name": sub.split("_")[0],
                "session_id": f"isl-ord-{sub}", **SKEL}})
    last, stable = -1, 0
    with driver() as d, d.session() as s:
        while stable < 4:
            time.sleep(6)
            n = s.run("MATCH (p:Point) WHERE p.session_id STARTS WITH 'isl-ord-' AND p.concept_id IS NULL "
                      "RETURN count(DISTINCT p.image_id) AS n").single()["n"]
            stable = stable + 1 if n == last else 0
            last = n
            print(f"  images with a graph: {n}/{expected}", flush=True)


def export(subs):
    sys.path.insert(0, str(REPO / "src" / "concept_creator"))
    from src.neo4j_to_networkx import Neo4jToNetworkx
    with driver() as d, d.session() as s:
        for sub in subs:
            ids = [r["i"] for r in s.run("MATCH (p:Point {session_id: $sid}) RETURN DISTINCT p.image_id AS i",
                                         sid=f"isl-ord-{sub}").data()]
            (OUT / sub).mkdir(parents=True, exist_ok=True)
            for iid in ids:
                g = Neo4jToNetworkx.extract_image_graph(s, iid)
                for _, nd in g.nodes(data=True):
                    if isinstance(nd.get("labels"), set):
                        nd["labels"] = sorted(nd["labels"])
                (OUT / sub / f"{iid}.json").write_text(json.dumps(nx.node_link_data(g, edges="edges", name="node_key"), default=str))
            print(f"{sub}: {len(ids)} graphs exported")


def _signature(g):
    labels = Counter(frozenset(d.get("labels", ())) for _, d in g.nodes(data=True))
    return {"nodes": g.number_of_nodes(), "edges": g.number_of_edges(),
            "labels": {"+".join(sorted(k)): v for k, v in labels.items()}}


def fold(subs, orders):
    for p in (REPO / "src" / "concept_creator", REPO / "src" / "concept_creator" / "visualization", REPO / "common"):
        sys.path.insert(0, str(p))
    import logging
    logging.disable(logging.CRITICAL)
    import probe_concept_formation as probe
    for sub in subs:
        files = sorted((OUT / sub).glob("*.json"))
        graphs = {}
        for f in files:
            g = nx.node_link_graph(json.loads(f.read_text()), edges="edges", name="node_key")
            for _, nd in g.nodes(data=True):
                nd["labels"] = list(nd.get("labels", []))        # the concept creator appends to a list
            graphs[f.stem] = g
        results = []
        for seed in range(orders):
            ids = sorted(graphs)
            random.Random(seed).shuffle(ids)
            ordered = {i: copy.deepcopy(graphs[i]) for i in ids}
            service = probe._build_offline_service()
            ordered = probe._determine_start_point(ordered, probe.logger)
            res = probe._run_offline(service, ordered, None, [0], capture_failure=True)
            sig = _signature(res.concept_graph) if not res.is_error else None
            results.append((seed, res, sig))
            print(f"{sub} order {seed}: {'FAILED ' + str(res.error_message)[:80] if res.is_error else sig}", flush=True)
        ok = [(s, r) for s, r, sig in results if sig]
        same = sum(nx.is_isomorphic(ok[0][1].concept_graph, r.concept_graph,
                                    node_match=lambda a, b: set(a.get("labels", ())) == set(b.get("labels", ())))
                   for _, r in ok[1:])
        print(f"{sub}: {len(ok)}/{orders} orders folded; isomorphic to the first: {same}/{max(len(ok) - 1, 0)}; "
              f"distinct signatures: {len({json.dumps(sig, sort_keys=True) for _, _, sig in results if sig})}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["ingest", "export", "fold"])
    ap.add_argument("subs", nargs="+")
    ap.add_argument("--orders", type=int, default=5)
    a = ap.parse_args()
    {"ingest": lambda: ingest(a.subs), "export": lambda: export(a.subs), "fold": lambda: fold(a.subs, a.orders)}[a.cmd]()


if __name__ == "__main__":
    main()
