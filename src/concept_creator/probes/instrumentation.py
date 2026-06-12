"""
FormationRecorder + attach_instrumentation.

Monkey-patches bound instance methods on the live service objects to emit
structured events into an in-memory list that is also written to a JSONL file.
No production source files are modified.
"""
import json
import logging
import math
import types
from pathlib import Path
from typing import Any

from src.property_handlers.property_handlers import PropertyProcessor


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _coord_val(v: Any) -> float:
    """Return a representative float for a scalar or range dict."""
    if isinstance(v, dict):
        return float(v.get("center", v.get("min", 0.0)))
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _range_width(v: Any) -> float:
    if isinstance(v, dict) and "min" in v and "max" in v:
        return float(v["max"]) - float(v["min"])
    return 0.0


def _euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def _bucket(d: float) -> str:
    for upper in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        if d <= upper:
            return f"{upper - 0.1:.1f}-{upper:.1f}"
    return ">1.0"


# ---------------------------------------------------------------------------
# FormationRecorder
# ---------------------------------------------------------------------------

class FormationRecorder:
    def __init__(self, out_path: Path | None = None, mismatch_threshold: float = 0.35):
        self.mismatch_threshold = mismatch_threshold
        self.events: list[dict] = []
        self.out_path = out_path
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = out_path.open("w")
        else:
            self._fh = None

    # ------------------------------------------------------------------
    def emit(self, event: dict) -> None:
        self.events.append(event)
        if self._fh is not None:
            self._fh.write(json.dumps(event, default=str) + "\n")
            self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()

    # ------------------------------------------------------------------
    def summary(self) -> dict:
        merge_events = [e for e in self.events if e["type"] == "merge"]
        sync_events = [e for e in self.events if e["type"] == "sync_pair"]
        sync_summaries = [e for e in self.events if e["type"] == "sync_summary"]
        start_events = [e for e in self.events if e["type"] == "start_point"]
        collision_events = [e for e in self.events if e["type"] == "id_collision"]
        segment_events = [e for e in self.events if e["type"] == "segment_match"]

        total_merges = len(merge_events)
        mismatch_merges = sum(1 for e in merge_events if e.get("mismatch"))
        merge_rate = mismatch_merges / total_merges if total_merges else 0.0

        hist: dict[str, int] = {}
        for e in merge_events:
            b = _bucket(e.get("distance", 0.0))
            hist[b] = hist.get(b, 0) + 1

        sync_mismatches = sum(1 for e in sync_events if e.get("mismatch"))

        per_step_merges: dict[int, int] = {}
        per_step_mismatches: dict[int, int] = {}
        for e in merge_events:
            s = e.get("step", 0)
            per_step_merges[s] = per_step_merges.get(s, 0) + 1
            if e.get("mismatch"):
                per_step_mismatches[s] = per_step_mismatches.get(s, 0) + 1

        # crossings and many-to-one from segment events
        crossings = sum(1 for e in segment_events if e.get("crossing"))
        many_to_one = sum(1 for e in segment_events if e.get("many_to_one"))

        # per-property max range width
        prop_max_widths: dict[str, float] = {}
        for e in merge_events:
            for prop in ("normalized_x", "normalized_y"):
                w_key = f"merged_width_{prop}"
                w = e.get(w_key, 0.0)
                if w > prop_max_widths.get(prop, 0.0):
                    prop_max_widths[prop] = w

        return {
            "total_merges": total_merges,
            "mismatch_merges": mismatch_merges,
            "mismatch_rate": round(merge_rate, 4),
            "distance_histogram": hist,
            "crossing_count": crossings,
            "many_to_one_count": many_to_one,
            "id_collisions": len(collision_events),
            "sync_mismatches": sync_mismatches,
            "per_step_merges": per_step_merges,
            "per_step_mismatches": per_step_mismatches,
            "start_point_table": start_events,
            "per_property_max_width": prop_max_widths,
            "sync_summaries": sync_summaries,
        }


# ---------------------------------------------------------------------------
# Patching helpers
# ---------------------------------------------------------------------------

def _make_process_properties_wrapper(recorder: FormationRecorder, original, step_ref: list[int]):
    def _wrapper(mcm_props, g_props, h_props):
        result = original(mcm_props, g_props, h_props)

        gx = _coord_val(g_props.get("normalized_x"))
        gy = _coord_val(g_props.get("normalized_y"))
        hx = _coord_val(h_props.get("normalized_x"))
        hy = _coord_val(h_props.get("normalized_y"))
        dist = _euclidean(gx, gy, hx, hy)

        width_x = _range_width(result.get("normalized_x"))
        width_y = _range_width(result.get("normalized_y"))

        recorder.emit({
            "type": "merge",
            "step": step_ref[0],
            "g_labels": list(g_props.get("labels", [])),
            "h_labels": list(h_props.get("labels", [])),
            "g_x": round(gx, 4),
            "g_y": round(gy, 4),
            "h_x": round(hx, 4),
            "h_y": round(hy, 4),
            "distance": round(dist, 4),
            "merged_width_normalized_x": round(width_x, 4),
            "merged_width_normalized_y": round(width_y, 4),
            "mismatch": dist > recorder.mismatch_threshold,
        })
        return result
    return _wrapper


def _make_synced_traversal_wrapper(recorder: FormationRecorder, original, step_ref: list[int]):
    def _wrapper(G_c, G_i):
        sync_list = original(G_c, G_i)
        total_pairs = 0
        total_mismatches = 0
        for path in sync_list:
            for node_c, node_i in path:
                data_c = G_c.nodes[node_c]
                data_i = G_i.nodes[node_i]
                cx = _coord_val(data_c.get("normalized_x"))
                cy = _coord_val(data_c.get("normalized_y"))
                ix = _coord_val(data_i.get("normalized_x"))
                iy = _coord_val(data_i.get("normalized_y"))
                dist = _euclidean(cx, cy, ix, iy)
                mismatch = dist > recorder.mismatch_threshold
                if mismatch:
                    total_mismatches += 1
                total_pairs += 1
                recorder.emit({
                    "type": "sync_pair",
                    "step": step_ref[0],
                    "node_c": node_c,
                    "node_i": node_i,
                    "c_x": round(cx, 4),
                    "c_y": round(cy, 4),
                    "i_x": round(ix, 4),
                    "i_y": round(iy, 4),
                    "c_labels": list(data_c.get("labels", [])),
                    "i_labels": list(data_i.get("labels", [])),
                    "distance": round(dist, 4),
                    "mismatch": mismatch,
                })
        recorder.emit({
            "type": "sync_summary",
            "step": step_ref[0],
            "num_paths": len(sync_list),
            "num_pairs": total_pairs,
            "num_mismatches": total_mismatches,
        })
        return sync_list
    return _wrapper


def _make_best_match_wrapper(recorder: FormationRecorder, original, step_ref: list[int]):
    # Baseline picks one match per template row (argmax in _find_best_matching_node);
    # accumulate rows of the same segment to flag crossings / many-to-one as they appear.
    state = {"matrix_id": None, "matches": []}

    def _wrapper(similarity_matrix, current_idx):
        best_idx = original(similarity_matrix, current_idx)
        if state["matrix_id"] != id(similarity_matrix) or current_idx == 0:
            state["matrix_id"] = id(similarity_matrix)
            state["matches"] = []
        state["matches"].append(best_idx)
        used = [j for j in state["matches"] if j is not None]
        crossing = used != sorted(used)
        many_to_one = len(used) != len(set(used))
        scores = list(similarity_matrix[current_idx]) if similarity_matrix else []
        best_score = scores[best_idx] if scores and best_idx is not None else 0.0
        recorder.emit({
            "type": "segment_match",
            "step": step_ref[0],
            "row_idx": current_idx,
            "best_idx": best_idx,
            "best_score": round(best_score, 4),
            "row_scores": [round(sc, 4) for sc in scores],
            "crossing": crossing,
            "many_to_one": many_to_one,
        })
        return best_idx
    return _wrapper


class _CollisionLogHandler(logging.Handler):
    def __init__(self, recorder: FormationRecorder, step_ref: list[int]):
        super().__init__()
        self.recorder = recorder
        self.step_ref = step_ref

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if "already exists in result graph" in msg:
            self.recorder.emit({
                "type": "id_collision",
                "step": self.step_ref[0],
                "message": msg,
            })


# ---------------------------------------------------------------------------
# attach_instrumentation
# ---------------------------------------------------------------------------

def attach_instrumentation(service, recorder: FormationRecorder) -> list[int]:
    """
    Monkey-patch bound instance methods on *service* so every pairing/merging
    decision is observable through *recorder*.

    Returns a mutable step_ref list [current_step] so callers can advance the
    step counter between images (step_ref[0] += 1 after each iteration).

    Production files are never touched.
    """
    step_ref: list[int] = [1]

    # 1. Wrap PropertyProcessor.process_properties on the service's prop_manager
    original_pp = service.prop_manager.process_properties
    service.prop_manager.process_properties = _make_process_properties_wrapper(
        recorder, original_pp, step_ref
    )

    # 2. Wrap SyncedTraversalGenerator.generate_synced_traversal on finder's instance
    stg = service.graph_minor_finder.synced_traversal_generator
    original_stg = stg.generate_synced_traversal
    stg.generate_synced_traversal = _make_synced_traversal_wrapper(
        recorder, original_stg, step_ref
    )

    # 3. Wrap SyncedGraphMinorFinder._find_best_matching_node (baseline per-row argmax)
    finder = service.graph_minor_finder
    original_match = finder._find_best_matching_node
    finder._find_best_matching_node = _make_best_match_wrapper(
        recorder, original_match, step_ref
    )

    # 4. Wrap StartPointModifier.change_start_point at class level
    from src.logic.start_point_modifier import StartPointModifier

    original_csp = StartPointModifier.change_start_point

    def _patched_change_start_point(self_mod, graph, new_start_point):
        node_data = graph.nodes[new_start_point]
        labels_before = list(node_data.get("labels", []))
        nx_val = node_data.get("normalized_x")
        ny_val = node_data.get("normalized_y")
        recorder.emit({
            "type": "start_point",
            "step": step_ref[0],
            "graph_id": graph.graph.get("graph_id"),
            "node_id": new_start_point,
            "normalized_x": _coord_val(nx_val),
            "normalized_y": _coord_val(ny_val),
            "original_labels": labels_before,
            "degree": graph.degree(new_start_point),
        })
        return original_csp(self_mod, graph, new_start_point)

    StartPointModifier.change_start_point = _patched_change_start_point

    # 5. Capture id_collision log messages from the finder's logger
    collision_handler = _CollisionLogHandler(recorder, step_ref)
    service.logger.addHandler(collision_handler)

    return step_ref
