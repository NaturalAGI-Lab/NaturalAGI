"""
probe_concept_formation.py — CLI instrument for concept formation.

Neo4j mode:
    python visualization/probe_concept_formation.py --session <id> [--concept-id foo] [--steps N]

Offline mode (no Neo4j):
    python visualization/probe_concept_formation.py --samples-dir /path/to/graph/json/dir
"""
import argparse
import copy
import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import networkx as nx

# ------------------------------------------------------------------ paths --
_PROBE_DIR = Path(__file__).parent
_SRC_DIR = _PROBE_DIR.parent
sys.path.insert(0, str(_SRC_DIR))
# common is also found via PYTHONPATH set by the caller

from src.critical_point_preprocessor import CriticalPointPreprocessor
from src.logic.graph_analyzer import GraphAnalyzer
from src.logic.start_point_modifier import StartPointModifier
from src.logic.start_point_picker import StartPointPicker
from src.model.concept_result import ConceptFormationStep, ConceptResult
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.property_handlers import PropertyProcessor
from src.synced_graph_algorithm import SyncedGraphMinorFinder

from instrumentation import FormationRecorder, attach_instrumentation

# -----------------------------------------------------------------------

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("probe_concept_formation")


# ---------------------------------------------------------------------------
# helper: range width on a node property
# ---------------------------------------------------------------------------

def _range_width(v) -> float:
    if isinstance(v, dict) and "min" in v and "max" in v:
        return float(v["max"]) - float(v["min"])
    return 0.0


def _json_default(o):
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    try:
        return float(o)
    except (TypeError, ValueError):
        return str(o)


# ---------------------------------------------------------------------------
# helper: load node-link JSON graphs from a directory
# ---------------------------------------------------------------------------

def _load_graphs_from_dir(samples_dir: Path) -> dict[str, nx.Graph]:
    graphs = {}
    for f in sorted(samples_dir.glob("*.json")):
        with f.open() as fh:
            data = json.load(fh)
        G = nx.node_link_graph(data)
        G.graph.setdefault("graph_id", f.stem)
        # node-link serialization moves the "id" attribute into the node key;
        # formation code (Point.from_node_data) requires it as an attribute
        for n, d in G.nodes(data=True):
            d.setdefault("id", n)
        graphs[f.stem] = G
    return graphs


# ---------------------------------------------------------------------------
# helper: build an offline service (no Neo4j)
# ---------------------------------------------------------------------------

def _build_offline_service():
    """Build a CriticalPointConceptService without connecting to Neo4j."""
    from src.critical_point_concept_service import CriticalPointConceptService

    svc = object.__new__(CriticalPointConceptService)
    svc.prop_manager = PropertyProcessor()
    svc.similarity_calculator = NodeSimilarityCalculator()
    svc.critical_point_preprocessor = CriticalPointPreprocessor()
    svc.logger = logging.getLogger("probe_service")
    svc.logger.setLevel(logging.DEBUG)
    svc.graph_minor_finder = SyncedGraphMinorFinder(
        prop_manager=svc.prop_manager,
        similarity_calculator=svc.similarity_calculator,
        critical_point_preprocessor=svc.critical_point_preprocessor,
        logger=svc.logger,
    )
    svc.repository = None
    return svc


# ---------------------------------------------------------------------------
# helper: _determine_start_point (replicates service method, offline-safe)
# ---------------------------------------------------------------------------

def _determine_start_point(image_graphs: dict[str, nx.Graph], log) -> dict[str, nx.Graph]:
    import numpy as np

    MAX_ITERATIONS = 15
    start_clustering_eps = 0.01
    eps_step = 0.05
    min_samples_coefficients = np.arange(0.4, 0.8)
    clustering_algorithm = "optics"
    start_point_characteristic = None

    picker = StartPointPicker(list(image_graphs.values()), clustering_algorithm=clustering_algorithm)

    for coeff in min_samples_coefficients:
        start_clustering_min_samples = int(len(image_graphs) * coeff)
        for _ in range(MAX_ITERATIONS):
            start_point_characteristic = picker.get_start_point_characteristic()
            if start_point_characteristic is not None:
                break
            picker.determine_start_point_characteristic(
                clustering_eps=start_clustering_eps,
                clustering_min_samples=start_clustering_min_samples,
            )
            start_clustering_eps += eps_step
            start_clustering_min_samples += 1
        if start_point_characteristic is not None:
            break

    if start_point_characteristic is None:
        log.error("Could not determine start point characteristic")
        raise ValueError("Could not determine start point characteristic")

    modifier = StartPointModifier(
        start_point_characteristic,
        expected_start_degree=picker.expected_start_degree,
    )
    for img_id, graph in image_graphs.items():
        sp = picker.get_start_point_for_graph(graph)
        if sp is None:
            raise ValueError(f"No start point found for graph {img_id}")
        image_graphs[img_id] = modifier.change_start_point(graph, sp)
    return image_graphs


# ---------------------------------------------------------------------------
# helper: _analyze_graph (replicates service method)
# ---------------------------------------------------------------------------

def _analyze_graph(graph: nx.Graph) -> nx.Graph:
    from common.traversal.visitors import AngleVisitor, DirectionVisitor, QuadrantVisitor

    visitors = [AngleVisitor(graph), QuadrantVisitor(graph), DirectionVisitor(graph)]
    analyzer = GraphAnalyzer(graph, visitors)
    analyzer.analyze()
    return graph


# ---------------------------------------------------------------------------
# helper: run incremental concept formation (offline replication)
# ---------------------------------------------------------------------------

def _run_offline(
    service,
    image_graphs: dict[str, nx.Graph],
    steps: Optional[int],
    step_ref: list[int],
    capture_failure: bool = False,
    recorder: Optional[FormationRecorder] = None,
) -> ConceptResult:
    image_ids = list(image_graphs.keys())
    steps_debug = []
    is_error = False
    error_message = None

    # _determine_start_point already called before attaching instrumentation;
    # _analyze_graph runs per image
    for img_id, g in image_graphs.items():
        image_graphs[img_id] = _analyze_graph(g)

    first_id = image_ids[0]
    concept_graph = image_graphs[first_id]
    steps_debug.append(ConceptFormationStep(
        current_concept=concept_graph,
        current_image=concept_graph,
        current_image_id=first_id,
        current_step=1,
        current_step_description="Initial concept",
        resulted_concept=concept_graph,
    ))

    for i, img_id in enumerate(image_ids[1:], 2):
        if steps and i > steps:
            break
        step_ref[0] = i
        concept_old = copy.deepcopy(concept_graph)
        try:
            result_graph = service.graph_minor_finder.find_max_common_minor(
                copy.deepcopy(concept_old), copy.deepcopy(image_graphs[img_id])
            )
            if len(result_graph.nodes) == 0:
                raise ValueError(
                    f"Common minor with image {img_id} is empty; "
                    "every training image must contribute to the concept"
                )
        except Exception as exc:
            if not capture_failure:
                raise
            is_error = True
            error_message = str(exc)
            steps_debug.append(ConceptFormationStep(
                current_concept=concept_old,
                current_image=image_graphs[img_id],
                current_image_id=img_id,
                current_step=i,
                current_step_description=(
                    f"EXCEPTION at image {i}/{len(image_ids)} ({img_id}): {exc}"
                ),
                resulted_concept=nx.Graph(),
            ))
            break

        concept_graph = result_graph

        if recorder is not None:
            recorder.emit({
                "type": "cpp_iterations",
                "step": i,
                "image_id": img_id,
                "iterations": getattr(
                    service.critical_point_preprocessor, "last_iteration_count", None
                ),
            })

        steps_debug.append(ConceptFormationStep(
            current_concept=concept_old,
            current_image=image_graphs[img_id],
            current_image_id=img_id,
            current_step=i,
            current_step_description=f"Image {i}/{len(image_ids)}: {img_id}",
            resulted_concept=concept_graph,
        ))

    return ConceptResult(
        concept_id="offline",
        concept_graph=concept_graph,
        image_graphs=image_graphs,
        steps_debug=steps_debug,
        is_error=is_error,
        error_message=error_message,
    )


# ---------------------------------------------------------------------------
# post-processing: range_evolution CSV + summary JSON + report MD
# ---------------------------------------------------------------------------

def _write_range_evolution(
    result: ConceptResult, out_dir: Path
) -> tuple[float, list[dict]]:
    rows = []
    for step in result.steps_debug:
        graph = step.resulted_concept
        for nid, data in graph.nodes(data=True):
            wx = _range_width(data.get("normalized_x"))
            wy = _range_width(data.get("normalized_y"))
            rows.append({
                "step": step.current_step,
                "node_id": nid,
                "labels": "|".join(data.get("labels", [])),
                "width_x": round(wx, 4),
                "width_y": round(wy, 4),
            })

    csv_path = out_dir / "range_evolution.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["step", "node_id", "labels", "width_x", "width_y"])
        writer.writeheader()
        writer.writerows(rows)

    # Final concept node widths for mean_xy_width
    final_graph = result.concept_graph
    widths_xy = []
    for nid, data in final_graph.nodes(data=True):
        wx = _range_width(data.get("normalized_x"))
        wy = _range_width(data.get("normalized_y"))
        widths_xy.append((wx + wy) / 2)

    mean_xy = sum(widths_xy) / len(widths_xy) if widths_xy else 0.0
    return round(mean_xy, 4), rows


def _write_summary(
    recorder: FormationRecorder,
    result: ConceptResult,
    mean_xy_width: float,
    out_dir: Path,
) -> dict:
    summ = recorder.summary()
    summ["mean_xy_width"] = mean_xy_width

    # Per-step node/edge counts
    step_counts = []
    for step in result.steps_debug:
        g = step.resulted_concept
        step_counts.append({
            "step": step.current_step,
            "nodes": len(g.nodes),
            "edges": len(g.edges),
        })
    summ["step_node_edge_counts"] = step_counts

    with (out_dir / "summary.json").open("w") as fh:
        json.dump(summ, fh, indent=2, default=str)
    return summ


def _write_report(
    summ: dict,
    recorder: FormationRecorder,
    mean_xy_width: float,
    out_dir: Path,
    threshold: float = 0.6,
) -> None:
    merge_events = [e for e in recorder.events if e["type"] == "merge"]
    top_wide = sorted(merge_events, key=lambda e: e.get("merged_width_normalized_y", 0), reverse=True)[:10]

    verdict = "CLEAN" if mean_xy_width < threshold else "SUSPECT"

    lines = [
        "# Concept Formation Probe Report\n",
        f"**Verdict:** {verdict}\n",
        f"- Total merges: {summ['total_merges']}",
        f"- ID collisions: {summ['id_collisions']}",
        f"- Crossings: {summ['crossing_count']}",
        f"- Many-to-one: {summ['many_to_one_count']}",
        f"- Mean XY width (final concept): {mean_xy_width:.4f}\n",
        "## Start Point Table\n",
    ]
    for sp in summ.get("start_point_table", []):
        lines.append(
            f"- step={sp.get('step')} node={sp.get('node_id')} "
            f"x={sp.get('normalized_x'):.3f} y={sp.get('normalized_y'):.3f} "
            f"labels={sp.get('original_labels')} degree={sp.get('degree')}"
        )

    lines += ["\n## Top-10 Widest Merges (by width_y)\n"]
    for ev in top_wide:
        lines.append(
            f"- step={ev.get('step')} g=({ev.get('g_x'):.3f},{ev.get('g_y'):.3f}) "
            f"h=({ev.get('h_x'):.3f},{ev.get('h_y'):.3f}) "
            f"dist={ev.get('distance'):.3f} width_y={ev.get('merged_width_normalized_y'):.3f}"
        )

    (out_dir / "report.md").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Concept formation probe")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--session", help="Neo4j session ID (Neo4j mode)")
    mode.add_argument("--samples-dir", help="Directory of node-link JSON graphs (offline mode)")
    parser.add_argument("--concept-id", default="probe")
    parser.add_argument("--steps", type=int, default=None,
                        help="Use only the first N samples (after ordering)")
    parser.add_argument("--order-seed", type=int, default=None,
                        help="Shuffle sample order with this seed (offline mode only)")
    parser.add_argument("--capture-failure", action="store_true",
                        help="Record a failed merge as a terminal step instead of raising")
    parser.add_argument("--out", default=None, help="Output directory")
    args = parser.parse_args()

    if args.session and args.order_seed is not None:
        parser.error("--order-seed is offline-only: the Neo4j-mode sample order "
                     "comes from the repository (ORDER BY image_id)")

    concept_id = args.concept_id
    out_dir = Path(args.out) if args.out else (_PROBE_DIR / "output" / concept_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = out_dir / "events.jsonl"
    recorder = FormationRecorder(out_path=jsonl_path)

    if args.session:
        # Neo4j mode
        from src.critical_point_concept_service import CriticalPointConceptService

        neo4j_uri = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
        neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        neo4j_pwd = os.environ.get("NEO4J_PASSWORD", "111122223333")

        service = CriticalPointConceptService(neo4j_uri, neo4j_user, neo4j_pwd)
        step_ref = attach_instrumentation(service, recorder)

        result = service.create_concept_incrementally(
            args.session, concept_id=concept_id, steps=args.steps, debug_mode=True
        )
    else:
        # Offline mode
        samples_path = Path(args.samples_dir)
        image_graphs = _load_graphs_from_dir(samples_path)
        if not image_graphs:
            print(f"No JSON graphs found in {samples_path}", file=sys.stderr)
            sys.exit(1)

        if args.order_seed is not None:
            import random
            ids = list(image_graphs)
            random.Random(args.order_seed).shuffle(ids)
            image_graphs = {i: image_graphs[i] for i in ids}

        service = _build_offline_service()

        # Attach instrumentation FIRST so StartPointModifier.change_start_point
        # is already patched when _determine_start_point calls it.
        step_ref = attach_instrumentation(service, recorder)
        step_ref[0] = 0  # step 0 = start-point determination phase

        image_graphs = _determine_start_point(image_graphs, logger)
        step_ref[0] = 1  # reset to formation step counter

        result = _run_offline(
            service, image_graphs, args.steps, step_ref,
            capture_failure=args.capture_failure, recorder=recorder,
        )

    recorder.close()

    # Post-processing
    mean_xy, _ = _write_range_evolution(result, out_dir)
    summ = _write_summary(recorder, result, mean_xy, out_dir)
    _write_report(summ, recorder, mean_xy, out_dir)

    (out_dir / "concept.json").write_text(json.dumps(
        nx.node_link_data(result.concept_graph, edges="edges"),
        default=_json_default,
    ))

    print(f"\nResults written to {out_dir}/")
    print(f"  summary.json  — {summ['total_merges']} merges, "
          f"mean_xy_width={mean_xy:.4f}")
    verdict = "CLEAN" if mean_xy < 0.6 else "SUSPECT"
    print(f"  Verdict: {verdict}")


if __name__ == "__main__":
    main()
