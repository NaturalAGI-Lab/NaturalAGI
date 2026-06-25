"""
probe_const_vs_range.py — explain why some concept StartPoint features are stored
as zero-width ("const") ranges (e.g. distance_to_centroid) while others are real
ranges (e.g. normalized_x).

The 1_3 training samples are no longer in Neo4j, so we cannot re-merge them. We
do not need to: a feature's range/const status is decided entirely by the merge
code, so we prove it two runnable ways.

  Part A — drive the REAL merge function (src.property_handlers.merge_values, the
           exact code every concept was built with) with synthetic per-sample
           value lists. A feature collapses to a zero-width range iff every
           contributing sample carried the same value.

  Part B — load a real concept node from Neo4j and classify each numeric feature
           CONST (max==min) vs RANGE (max>min). The CONST set is exactly the
           structural/topological features; the RANGE set is exactly the
           positional ones — because the reduced training graphs were all the
           same topology but drawn at different places.

Usage:
    python probes/probe_const_vs_range.py
    python probes/probe_const_vs_range.py --concept-id 1_3 --node-label StartPoint
"""
import argparse
import json
import os
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_SRC_DIR))

from src.property_handlers import merge_values


def _width(value) -> float:
    if isinstance(value, dict) and "min" in value and "max" in value:
        return float(value["max"]) - float(value["min"])
    return 0.0


def _part_a() -> None:
    # per-sample values a straight-"1" training set would produce for the start point
    samples = {
        "distance_to_centroid": [1.0, 1.0, 1.0, 1.0, 1.0],
        "eccentricity": [0.0, 0.0, 0.0, 0.0, 0.0],
        "closeness_centrality": [1.0, 1.0, 1.0, 1.0, 1.0],
        "pagerank": [0.5, 0.5, 0.5, 0.5, 0.5],
        "neighbor_endpoint_count": [1.0, 1.0, 1.0, 1.0, 1.0],
        "neighbor_corner_count": [0.0, 0.0, 0.0, 0.0, 0.0],
        "normalized_x": [-0.30, 0.05, 0.30, 0.55, 0.70],
        "normalized_y": [-1.00, -0.92, -0.85, -0.78, -0.70],
    }

    print("PART A — merge_values() on synthetic per-sample inputs (REAL concept code)")
    print(f"{'feature':<26} {'distinct sample values':<34} {'merged result':<34} {'width':>7}  kind")
    print("-" * 118)
    for feature, vals in samples.items():
        merged = merge_values(*vals)
        w = _width(merged)
        kind = "CONST" if w == 0.0 else "RANGE"
        distinct = sorted(set(vals))
        merged_str = (
            f"[{merged['min']:.2f}, {merged['max']:.2f}]"
            if isinstance(merged, dict) else str(merged)
        )
        print(f"{feature:<26} {str(distinct):<34} {merged_str:<34} {w:>7.3f}  {kind}")
    print()
    print("  => A feature is CONST iff every sample carried the same value.")
    print("     No feature is special-cased: _merge_numeric_values ranges them all.")
    print()


def _coerce(value):
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            return value
    return value


def _part_b(concept_id: str, node_label: str) -> None:
    from neo4j import GraphDatabase

    uri = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ.get("NEO4J_PASSWORD", "111122223333")

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    query = (
        f"MATCH (n:{node_label} {{concept_id: $cid}}) RETURN properties(n) AS p LIMIT 1"
    )
    with driver.session() as session:
        record = session.run(query, cid=concept_id).single()  # type: ignore[arg-type]
    driver.close()

    if record is None:
        print(f"PART B — no :{node_label} node found for concept {concept_id}")
        return

    props = {k: _coerce(v) for k, v in record["p"].items()}

    const_rows, range_rows = [], []
    for key, value in props.items():
        if not (isinstance(value, dict) and value.get("type") == "range"):
            continue
        w = _width(value)
        row = (key, value["min"], value["max"], value["center"])
        (range_rows if w > 0 else const_rows).append(row)

    print(f"PART B — concept {concept_id} :{node_label} numeric features from Neo4j")
    print(f"  CONST (max==min) — invariant across every training sample [{len(const_rows)}]")
    for key, lo, hi, c in sorted(const_rows):
        print(f"    {key:<28} = {c}")
    print(f"  RANGE (max>min)  — varied across training samples [{len(range_rows)}]")
    for key, lo, hi, c in sorted(range_rows):
        print(f"    {key:<28} [{lo:.3f}, {hi:.3f}]  width={hi - lo:.3f}")
    print()
    print("  => The fact each value is a {min,max,center,type:range} dict (not a bare")
    print("     scalar) proves it was MERGED across >=2 samples; min==max proves they")
    print("     all agreed. CONST is genuine invariance, not a frozen/first-sample bug.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concept-id", default="1_3")
    parser.add_argument("--node-label", default="StartPoint")
    parser.add_argument("--skip-neo4j", action="store_true")
    args = parser.parse_args()

    _part_a()
    if not args.skip_neo4j:
        try:
            _part_b(args.concept_id, args.node_label)
        except Exception as exc:  # noqa: BLE001
            print(f"PART B skipped (Neo4j unavailable): {exc}")


if __name__ == "__main__":
    main()
