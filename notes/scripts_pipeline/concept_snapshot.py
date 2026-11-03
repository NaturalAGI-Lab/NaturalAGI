"""Cypher-level snapshot / restore of everything that makes up the recogniser's knowledge in Neo4j
(no APOC): structural concepts (any node with concept_id) and, once the band port lands,
:BandModel / :BandConcept / :DirectionMapSchema nodes.

Usage: concept_snapshot.py dump <file.json> | restore <file.json> | count
"""
import json
import sys

from neo4j import GraphDatabase

KNOWLEDGE = (
    "n.concept_id IS NOT NULL OR n:BandModel OR n:BandConcept OR n:DirectionMapSchema"
)


def main() -> None:
    op = sys.argv[1]
    path = sys.argv[2] if len(sys.argv) > 2 else None
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "111122223333"))
    with driver.session() as s:
        if op == "count":
            print(
                s.run(
                    f"MATCH (n) WHERE {KNOWLEDGE} "
                    "RETURN count(n) AS nodes, count(DISTINCT n.concept_id) AS concepts"
                ).single().data()
            )
        elif op == "dump":
            nodes = [
                {"eid": r["eid"], "labels": r["labels"], "props": r["props"]}
                for r in s.run(
                    f"MATCH (n) WHERE {KNOWLEDGE} "
                    "RETURN elementId(n) AS eid, labels(n) AS labels, properties(n) AS props"
                )
            ]
            keep = {n["eid"] for n in nodes}
            rels = [
                {"a": r["a"], "b": r["b"], "type": r["t"], "props": r["props"]}
                for r in s.run(
                    "MATCH (a)-[r]->(b) RETURN elementId(a) AS a, elementId(b) AS b, "
                    "type(r) AS t, properties(r) AS props"
                )
                if r["a"] in keep and r["b"] in keep
            ]
            with open(path, "w") as fh:
                json.dump({"nodes": nodes, "rels": rels}, fh, default=str)
            print(f"dumped {len(nodes)} nodes, {len(rels)} rels -> {path}")
        elif op == "restore":
            with open(path) as fh:
                snap = json.load(fh)
            for n in snap["nodes"]:
                props = dict(n["props"], _snap_eid=n["eid"])
                s.run(f"CREATE (x:{':'.join(n['labels'])}) SET x = $p", p=props)
            for r in snap["rels"]:
                s.run(
                    f"MATCH (a {{_snap_eid:$a}}), (b {{_snap_eid:$b}}) "
                    f"CREATE (a)-[x:{r['type']}]->(b) SET x = $p",
                    a=r["a"], b=r["b"], p=r["props"],
                )
            s.run("MATCH (n) WHERE n._snap_eid IS NOT NULL REMOVE n._snap_eid")
            print(f"restored {len(snap['nodes'])} nodes, {len(snap['rels'])} rels")
    driver.close()


if __name__ == "__main__":
    main()
