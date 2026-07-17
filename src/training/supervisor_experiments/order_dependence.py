"""Section 4 (S2): does the concept depend on sample presentation order?

Code-level answer is already YES: the first sample seeds the concept
(critical_point_concept_service.py:87-88) and the historical Neo4j order was
non-deterministic (no ORDER BY until 2026-07). Here we quantify the variance.
"""
import json
from pathlib import Path

import networkx as nx
import pandas as pd

from .formation_lab import PROBE_OUT_ROOT, SAMPLES_ROOT, export_session_graphs, run_probe
from .infra import timer

OUT = PROBE_OUT_ROOT / "order"
DEFAULT_CONCEPTS = ["2_2", "7_1", "8_1"]
DEFAULT_SEEDS = list(range(10))


def probe_dir(concept_id: str, seed: int) -> Path:
    return OUT / f"{concept_id}_seed{seed}"


def run_order_probes(concepts: list[str] = DEFAULT_CONCEPTS,
                     seeds: list[int] = DEFAULT_SEEDS,
                     force: bool = False) -> pd.DataFrame:
    rows = []
    for cid in concepts:
        samples = SAMPLES_ROOT / cid
        if not samples.exists():
            export_session_graphs(cid, samples)
        for seed in seeds:
            out_dir = probe_dir(cid, seed)
            if force or not (out_dir / "summary.json").exists():
                with timer(f"probe {cid} seed={seed}"):
                    run_probe(samples, out_dir, concept_id=cid, order_seed=seed)
            summ = json.loads((out_dir / "summary.json").read_text())
            final = summ["step_node_edge_counts"][-1]
            rows.append({
                "concept_id": cid, "seed": seed,
                "final_nodes": final["nodes"], "final_edges": final["edges"],
                "mean_xy_width": summ.get("mean_xy_width"),
                "failed": final["nodes"] == 0,
            })
    return pd.DataFrame(rows)


def load_final_concept(concept_id: str, seed: int) -> nx.Graph:
    data = json.loads((probe_dir(concept_id, seed) / "concept.json").read_text())
    return nx.node_link_graph(data, edges="edges")


def _labels_match(a: dict, b: dict) -> bool:
    return set(map(str, a.get("labels", []))) == set(map(str, b.get("labels", [])))


def pairwise_ged(concept_id: str, seeds: list[int] = DEFAULT_SEEDS,
                 timeout: float = 20.0) -> pd.DataFrame:
    """Exact structural GED (label-only costs) between per-seed final concepts."""
    graphs = {}
    for s in seeds:
        path = probe_dir(concept_id, s) / "concept.json"
        if path.exists():
            g = load_final_concept(concept_id, s)
            if g.number_of_nodes() > 0:
                graphs[s] = g
    seeds_ok = sorted(graphs)
    matrix = pd.DataFrame(index=seeds_ok, columns=seeds_ok, dtype=float)
    for i, a in enumerate(seeds_ok):
        matrix.loc[a, a] = 0.0
        for b in seeds_ok[i + 1:]:
            d = nx.graph_edit_distance(graphs[a], graphs[b],
                                       node_match=_labels_match, timeout=timeout)
            matrix.loc[a, b] = matrix.loc[b, a] = d
    return matrix


def summarize(df: pd.DataFrame, ged_matrices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for cid, grp in df.groupby("concept_id"):
        m = ged_matrices.get(cid)
        upper = []
        if m is not None and len(m) > 1:
            upper = [m.iloc[i, j] for i in range(len(m)) for j in range(i + 1, len(m))
                     if pd.notna(m.iloc[i, j])]
        rows.append({
            "concept_id": cid,
            "seeds": len(grp),
            "failures": int(grp.failed.sum()),
            "node_counts": sorted(grp.final_nodes.unique().tolist()),
            "identical_topology_share": round(
                float((pd.Series(upper) == 0).mean()) if upper else float("nan"), 2),
            "mean_pairwise_ged": round(float(pd.Series(upper).mean()), 2) if upper else None,
            "max_pairwise_ged": round(float(pd.Series(upper).max()), 2) if upper else None,
            "width_min": round(float(grp.mean_xy_width.min()), 3),
            "width_max": round(float(grp.mean_xy_width.max()), 3),
        })
    return pd.DataFrame(rows)
