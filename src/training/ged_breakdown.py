import json
import sys
from contextlib import nullcontext
from pathlib import Path

import networkx as nx

_REPO = Path(__file__).resolve().parents[2]
_CLASSIFICATION = _REPO / "src" / "classification"
if str(_CLASSIFICATION) not in sys.path:
    sys.path.insert(0, str(_CLASSIFICATION))

# Makefile: NUCLIO_STORAGE=/opt/nuclio/shared_storage/ ↔ LOCAL_STORAGE=./datasets/
_NUCLIO_STORAGE_PREFIX = "/opt/nuclio/shared_storage/"
_DATASETS_DIR = _REPO / "datasets"

from repository.image_repository import ImageRepository
from repository.concept_repository import ConceptRepository
from concept_minor_classifier import ConceptMinorClassifier
from graph_similarity.graph_edit_distance_comparator import (
    GraphEditDistanceComparator,
    build_edit_operations,
)


def _class_of(concept_id: str) -> str:
    return concept_id.split("_")[0]


def _to_payload(g: nx.Graph) -> dict:
    return json.loads(json.dumps(
        nx.node_link_data(g, edges="links"),
        default=lambda o: float(o) if _is_number(o) else str(o),
    ))


def _is_number(o) -> bool:
    if isinstance(o, bool):
        return False
    try:
        float(o)
        return True
    except (TypeError, ValueError):
        return False


def get_image_graph_if_present(driver, image_id: str):
    graph = ImageRepository(driver).get_image_graph(image_id)
    if graph is None or graph.number_of_nodes() == 0:
        return None
    return graph


def get_concept_graph(driver, concept_id: str):
    return ConceptRepository(driver).get_concept_graph(concept_id)


def resolve_sample_path(image_path: str):
    """Map a stored (container) image_path to the host dataset file, or None."""
    if not image_path:
        return None
    p = str(image_path)
    if _NUCLIO_STORAGE_PREFIX in p:
        candidate = _DATASETS_DIR / p.split(_NUCLIO_STORAGE_PREFIX, 1)[1]
    else:
        candidate = Path(p)
    return candidate if candidate.exists() else None


def get_image_skeleton_payload(driver, image_id: str):
    """Raw (pre-preprocessing) image graph as a node-link dict, or None."""
    graph = get_image_graph_if_present(driver, image_id)
    if graph is None:
        return None
    return _to_payload(graph)


def expected_concepts(all_concept_ids, classification_results, expected_class) -> list:
    sims = {r["concept_id"]: r.get("similarity")
            for r in classification_results if "concept_id" in r}
    rows = [{"concept_id": cid, "similarity": sims.get(cid)}
            for cid in all_concept_ids if _class_of(cid) == str(expected_class)]
    rows.sort(key=lambda r: (r["similarity"] is None,
                             -(r["similarity"] or 0.0), r["concept_id"]))
    return rows


def _run_ged_breakdown(prep_image, prep_concept, concept_id, ged_timeout) -> dict:
    similarity, cost, node_path, edge_path = (
        GraphEditDistanceComparator.compare_graphs_ged_with_path(
            prep_image, prep_concept, concept_id, ged_timeout)
    )
    edit_ops = build_edit_operations(node_path, edge_path, prep_image, prep_concept)
    return {
        "image_nodelink": _to_payload(prep_image),
        "concept_nodelink": _to_payload(prep_concept),
        "edit_ops": edit_ops,
        "cost": cost,
        "n1": prep_image.number_of_nodes() + prep_image.number_of_edges(),
        "n2": prep_concept.number_of_nodes() + prep_concept.number_of_edges(),
        "similarity": similarity,
    }


def _cost_config_ctx(classification_params):
    """Restore the run's cost ladder for the breakdown.

    Without it, GED falls back to the source-default NodeCost ladder, which can flip
    the optimal node mapping (e.g. a spurious Point↔Vector match) and report a
    similarity that never entered the live decision. Mirrors nuclio_handler's
    production scoring context so the breakdown matches the per-concept scores.
    """
    if not classification_params:
        return nullcontext()
    from nuclio_handler import _cost_config_override

    return _cost_config_override(
        features=classification_params.get("features"),
        costs=classification_params.get("node_costs"),
        epsilon=classification_params.get("diagnostic_weight_epsilon"),
    )


def load_run_concepts(run_dir: str) -> dict:
    """Load the run's persisted concept snapshot ({concept_id: nx.Graph}).

    The drilldown must score against the topologies the run actually used, not the
    current Neo4j state (which changes on every retrain). Returns {} if the run
    predates concept-snapshot persistence.
    """
    snapshot = Path(run_dir) / "concept_graphs.json"
    if not snapshot.exists():
        return {}
    from evaluation import restore_concept_snapshot

    return restore_concept_snapshot(str(snapshot))


def _prime_feature_context(all_concepts: dict) -> None:
    """Replicate production's cache-load setup (range-width annotation + global
    feature spans) so D33 out-of-range softening and diagnostic weights match the
    live decision. Without it FEATURE_GLOBAL_SPANS stays empty and every
    out-of-range feature hits the hard NO_MATCH cliff — a similarity the run never
    produced.
    """
    from nuclio_handler import _annotate_range_widths
    from graph_similarity import cost_functions as _cf

    _annotate_range_widths(all_concepts)
    _cf.compute_feature_global_spans(all_concepts)


def compute_breakdown(
    image_graph,
    concept_id,
    concept_graph,
    all_concepts: dict | None = None,
    ged_timeout: float | None = None,
    classification_params: dict | None = None,
) -> dict:
    if ged_timeout is None:
        params_timeout = (classification_params or {}).get("ged_timeout")
        ged_timeout = float(params_timeout) if params_timeout is not None else 5.0
    with _cost_config_ctx(classification_params):
        if all_concepts:
            _prime_feature_context(all_concepts)
        prep_image, prep_concept = ConceptMinorClassifier().preprocess_pair(
            image_graph, concept_graph
        )
        return _run_ged_breakdown(prep_image, prep_concept, concept_id, ged_timeout)


def _coerce_results(results) -> list:
    if isinstance(results, str):
        try:
            return json.loads(results) or []
        except (json.JSONDecodeError, TypeError):
            return []
    return results or []


def _fmt_params(run_config: dict, row) -> str:
    params = run_config.get("classification_params")
    if params is None:
        raw = row.get("parameters")
        params = _coerce_results(raw) if isinstance(raw, str) else raw
    if isinstance(params, (dict, list)):
        return json.dumps(params, sort_keys=True, default=str)
    return str(params)


def build_debug_blob(row, run_config, breakdown, concept_id, host_path,
                     run_name, skeleton_present) -> str:
    """Comprehensive, copy-pasteable markdown for one misclassified case."""
    run_config = run_config if isinstance(run_config, dict) else {}
    image_path = str(row.get("image_path", ""))
    image_name = Path(image_path).name or "?"
    results = _coerce_results(row.get("classification_results"))
    scored = sorted(results, key=lambda r: (r.get("similarity") is None,
                                            -(r.get("similarity") or 0.0)))
    winner = scored[0]["concept_id"] if scored else "?"
    git = run_config.get("git", {}) if isinstance(run_config.get("git"), dict) else {}

    lines = [
        f"## Misclassification debug — {image_name}",
        "",
        "### Identity",
        f"- image_name: {image_name}",
        f"- image_id: {row.get('image_id', '?')}",
        f"- expected: {row.get('expected', '?')}  |  predicted: {row.get('predicted', '?')}",
        f"- host_path: {host_path if host_path else '(not found on host)'}",
        f"- container_path: {image_path}",
        "",
        "### Run context",
        f"- run: {run_name}",
        f"- git: {str(git.get('commit', '?'))[:8]} ({git.get('branch', '?')})",
        f"- common_lib: {run_config.get('common_lib_version', '?')}",
        f"- params: {_fmt_params(run_config, row)}",
        "",
        f"### Per-concept scores (winner: {winner})",
        "| concept_id | similarity | is_minor | concept_cx | image_cx | message |",
        "|---|---|---|---|---|---|",
    ]
    for r in scored:
        sim = r.get("similarity")
        sim_s = f"{sim:.4f}" if isinstance(sim, (int, float)) else str(sim)
        lines.append("| {} | {} | {} | {} | {} | {} |".format(
            r.get("concept_id", "?"), sim_s, r.get("is_minor", ""),
            r.get("concept_complexity", ""), r.get("image_complexity", ""),
            str(r.get("message", "")).replace("|", "/")))

    lines += ["", f"### GED breakdown — expected concept {concept_id}"]
    if breakdown is None:
        lines.append("- (image graph not in Neo4j — breakdown unavailable; "
                     "re-run classification with delete_image_nodes=False)")
    else:
        lines.append("- recomputed: cost {:.2f} · n1 {} · n2 {} · similarity {:.3f}".format(
            breakdown["cost"], breakdown["n1"], breakdown["n2"], breakdown["similarity"]))
        penalties = sorted(
            (o for o in breakdown.get("edit_ops", []) if o.get("op") != "MATCH"),
            key=lambda o: -(o.get("cost") or 0.0))
        for o in penalties[:10]:
            lines.append("  - {} {} img:{} <-> con:{} cost {:.2f} ({})".format(
                o.get("kind", ""), o.get("op", ""), o.get("image_ref"),
                o.get("concept_ref"), (o.get("cost") or 0.0), o.get("reason", "")))

    lines += ["", f"- skeleton in Neo4j: {'yes' if skeleton_present else 'no'}"]
    return "\n".join(lines)


def copy_button_html(text: str, label: str = "Copy debug info") -> str:
    """A single button that copies `text` to the clipboard without showing it.

    Runs inside the components.html iframe where navigator.clipboard is often
    blocked by permissions-policy, so it falls back to execCommand on the click
    gesture (same approach as plotting._CLICK_TO_COPY_JS)."""
    # Escape "</" so a "</script>" inside the text can't close the iframe tag.
    payload = json.dumps(text).replace("</", "<\\/")
    label_js = json.dumps(label).replace("</", "<\\/")
    return (
        "<!doctype html><html><head><style>"
        "html,body{margin:0;background:#0b1017;"
        "font:13px/1.3 'Avenir Next',Helvetica,Arial,sans-serif;}"
        "#copybtn{background:#172232;color:#e6edf3;border:1px solid #263241;"
        "border-radius:6px;padding:6px 12px;cursor:pointer;}"
        "#copybtn:hover{background:#1d2b3d;}"
        "#copymsg{color:#9aa7b7;margin-left:10px;}"
        "</style></head><body>"
        "<button id='copybtn'></button><span id='copymsg'></span>"
        "<script>(function(){"
        "var DATA=" + payload + ";"
        "var btn=document.getElementById('copybtn');"
        "btn.textContent='\\uD83D\\uDCCB '+" + label_js + ";"
        "var msg=document.getElementById('copymsg');"
        "function fb(t){try{var ta=document.createElement('textarea');ta.value=t;"
        "ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);"
        "ta.focus();ta.select();var ok=document.execCommand('copy');"
        "document.body.removeChild(ta);return ok;}catch(e){return false;}}"
        "function show(t){msg.textContent=t;clearTimeout(msg._t);"
        "msg._t=setTimeout(function(){msg.textContent='';},1800);}"
        "btn.addEventListener('click',function(){"
        "function ok(){show('Copied \\u2713');}"
        "function fail(){show(fb(DATA)?'Copied \\u2713':'Copy failed');}"
        "if(navigator.clipboard&&navigator.clipboard.writeText){"
        "navigator.clipboard.writeText(DATA).then(ok).catch(fail);}else{fail();}"
        "});})();</script></body></html>"
    )
