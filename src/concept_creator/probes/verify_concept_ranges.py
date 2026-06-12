"""
verify_concept_ranges.py — print per-node range widths and exit 1 if mean_xy_width > threshold.

Usage:
    # Load concept from Neo4j:
    python probes/verify_concept_ranges.py --concept-id 7_1

    # Load from a probe run summary:
    python probes/verify_concept_ranges.py --summary probes/output/probe/summary.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_SRC_DIR))


def _range_width(v) -> float:
    if isinstance(v, dict) and "min" in v and "max" in v:
        return float(v["max"]) - float(v["min"])
    return 0.0


def _from_neo4j(concept_id: str):
    from neo4j import GraphDatabase
    from src.neo4j_to_networkx import Neo4jToNetworkx

    neo4j_uri = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_pwd = os.environ.get("NEO4J_PASSWORD", "111122223333")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pwd))
    with driver.session() as session:
        graph = Neo4jToNetworkx.extract_concept_graph(session, concept_id)
    driver.close()

    rows = []
    for nid, data in graph.nodes(data=True):
        wx = _range_width(data.get("normalized_x"))
        wy = _range_width(data.get("normalized_y"))
        rows.append({
            "node_id": nid,
            "labels": "|".join(data.get("labels", [])),
            "width_x": round(wx, 4),
            "width_y": round(wy, 4),
        })
    return rows


def _from_summary(summary_path: Path):
    with summary_path.open() as fh:
        data = json.load(fh)
    # summary has per_property_max_width but not per-node breakdown
    # fall back to the range_evolution.csv in the same directory
    csv_path = summary_path.parent / "range_evolution.csv"
    if not csv_path.exists():
        # construct rows from summary only
        max_widths = data.get("per_property_max_width", {})
        return [{"node_id": "all", "labels": "", "width_x": max_widths.get("normalized_x", 0.0),
                 "width_y": max_widths.get("normalized_y", 0.0)}]

    import csv
    rows = []
    with csv_path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Only final step rows
            rows.append(row)
    # Filter to last step
    if rows:
        last_step = max(int(r["step"]) for r in rows)
        rows = [r for r in rows if int(r["step"]) == last_step]
        rows = [{"node_id": r["node_id"], "labels": r["labels"],
                 "width_x": float(r["width_x"]), "width_y": float(r["width_y"])} for r in rows]
    return rows


def main():
    parser = argparse.ArgumentParser(description="Verify concept range widths")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--concept-id", help="Concept ID to load from Neo4j")
    src.add_argument("--summary", help="Path to summary.json from a probe run")
    parser.add_argument("--max-width", type=float, default=0.6,
                        help="Exit 1 if mean_xy_width > this (default 0.6)")
    args = parser.parse_args()

    if args.concept_id:
        rows = _from_neo4j(args.concept_id)
    else:
        rows = _from_summary(Path(args.summary))

    if not rows:
        print("No nodes found.")
        sys.exit(1)

    print(f"{'node_id':<20} {'labels':<40} {'width_x':>8} {'width_y':>8}")
    print("-" * 80)
    widths_xy = []
    for r in rows:
        wx = float(r["width_x"])
        wy = float(r["width_y"])
        widths_xy.append((wx + wy) / 2)
        print(f"{str(r['node_id']):<20} {str(r['labels']):<40} {wx:>8.4f} {wy:>8.4f}")

    mean_xy = sum(widths_xy) / len(widths_xy) if widths_xy else 0.0
    print("-" * 80)
    print(f"mean_xy_width = {mean_xy:.4f}  (threshold = {args.max_width})")

    if mean_xy > args.max_width:
        print(f"FAIL: mean_xy_width {mean_xy:.4f} > {args.max_width}")
        sys.exit(1)
    else:
        print("PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
