"""A0 — switch the active structural concept set between the EMNIST fold concepts and Nikita's 13 MNIST concepts.

  off-emnist     tag the 91 active EMNIST concepts concept_kind='isl_off' (ConceptRepository loads concept_kind IS NULL)
  on-emnist      remove that tag
  restore-mnist  write the 13 concepts of experiments/run_20260630_235356/concept_graphs.json back to Neo4j
                 (same writer as the concept creator; nodes tagged isl_restored=true)
  remove-mnist   delete the restored nodes (only those tagged isl_restored)
  status         count active / tagged concepts
Restart the classification containers afterwards so they reload their concept cache.
A full snapshot of the knowledge taken before these experiments: tests/_isl/knowledge_before_isl.json.
"""
import json
import sys
from pathlib import Path

import networkx as nx
from neo4j import GraphDatabase

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src" / "concept_creator"))
from src.networkx_to_neo4j import NetworkxToNeo4j  # noqa: E402

SNAPSHOT = REPO / "experiments" / "run_20260630_235356" / "concept_graphs.json"
DROP = {"id", "uuid", "is_concept", "concept_id"}


def driver():
    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "111122223333"))


def status(s):
    rows = s.run("MATCH (n:Point) WHERE n.concept_id IS NOT NULL "
                 "RETURN coalesce(n.concept_kind, 'active') AS kind, count(DISTINCT n.concept_id) AS concepts").data()
    print({r["kind"]: r["concepts"] for r in rows})


def main():
    op = sys.argv[1]
    with driver() as d, d.session() as s:
        if op == "off-emnist":
            ids = [r["c"] for r in s.run("MATCH (n:Point) WHERE n.concept_id =~ '[A-Z]_[0-9]+' AND n.concept_kind IS NULL "
                                         "RETURN DISTINCT n.concept_id AS c").data()]
            s.run("MATCH (n) WHERE n.concept_id IN $ids AND n.concept_kind IS NULL SET n.concept_kind = 'isl_off'", ids=ids)
            print(f"tagged {len(ids)} EMNIST concepts isl_off")
        elif op == "on-emnist":
            s.run("MATCH (n) WHERE n.concept_kind = 'isl_off' REMOVE n.concept_kind")
        elif op == "restore-mnist":
            snap = json.loads(SNAPSHOT.read_text())
            clash = s.run("MATCH (n) WHERE n.concept_id IN $ids RETURN count(n) AS c", ids=list(snap)).single()["c"]
            if clash:
                raise SystemExit(f"{clash} nodes with these concept ids already exist")
            for cid, data in snap.items():
                g = nx.node_link_graph(data, edges="edges")
                for _, nd in g.nodes(data=True):
                    nd["labels"] = set(nd.get("labels", []))
                    for k in DROP & set(nd):
                        del nd[k]
                    nd["isl_restored"] = True
                s.execute_write(NetworkxToNeo4j.create_structure, g, cid)
            print(f"restored {len(snap)} MNIST concepts")
        elif op == "remove-mnist":
            n = s.run("MATCH (n {isl_restored: true}) DETACH DELETE n RETURN count(n) AS c").single()["c"]
            print(f"deleted {n} restored nodes")
        status(s)


if __name__ == "__main__":
    main()
