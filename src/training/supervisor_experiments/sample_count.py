"""Section 5 (S3, offline): concept formation quality vs number of samples."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .formation_lab import (ALL_CONCEPTS, PROBE_OUT_ROOT, SAMPLES_ROOT,
                            export_session_graphs, run_probe)
from .infra import timer

OUT = PROBE_OUT_ROOT / "sample_count"
DEFAULT_NS = (2, 5, 10, 20)
DEFAULT_SEEDS = (0, 1, 2)


def probe_dir(concept_id: str, n: int, seed: int) -> Path:
    return OUT / f"{concept_id}_N{n}_seed{seed}"


def run_sample_count_grid(concepts: list[str] = ALL_CONCEPTS,
                          ns: tuple[int, ...] = DEFAULT_NS,
                          seeds: tuple[int, ...] = DEFAULT_SEEDS,
                          force: bool = False) -> pd.DataFrame:
    rows = []
    for cid in concepts:
        samples = SAMPLES_ROOT / cid
        if not samples.exists():
            export_session_graphs(cid, samples)
        available = len(list(samples.glob("*.json")))
        for n in ns:
            if n > available:
                continue
            for seed in seeds:
                out_dir = probe_dir(cid, n, seed)
                if force or not (out_dir / "summary.json").exists():
                    with timer(f"probe {cid} N={n} seed={seed}"):
                        run_probe(samples, out_dir, concept_id=cid,
                                  order_seed=seed, steps=n)
                summ = json.loads((out_dir / "summary.json").read_text())
                final = summ["step_node_edge_counts"][-1]
                rows.append({
                    "concept_id": cid, "n_samples": n, "seed": seed,
                    "final_nodes": final["nodes"], "final_edges": final["edges"],
                    "mean_xy_width": summ.get("mean_xy_width"),
                    "failed": final["nodes"] == 0,
                })
    return pd.DataFrame(rows)


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    return (df[~df.failed]
            .groupby(["concept_id", "n_samples"])
            .agg(nodes_mean=("final_nodes", "mean"),
                 nodes_std=("final_nodes", "std"),
                 width_mean=("mean_xy_width", "mean"),
                 runs=("seed", "count"))
            .round(3)
            .reset_index())


CURVE_LABELS = {
    "uk": {"xlabel": "кількість зразків N", "nodes": "вузлів у концепті",
           "topo_title": "Топологія концепту vs N",
           "width": "середня ширина діапазону (x,y)",
           "env_title": "Ширина конвертів vs N (ризик catch-all)"},
    "en": {"xlabel": "number of training samples N", "nodes": "nodes in concept",
           "topo_title": "Concept topology vs N",
           "width": "mean parameter-range width (x,y)",
           "env_title": "Envelope width vs N (catch-all risk)"},
}


def plot_curves(df: pd.DataFrame, full_reference: pd.DataFrame | None = None,
                lang: str = "uk"):
    """full_reference: convergence-run df (all samples) to extend the curves."""
    labels = CURVE_LABELS[lang]
    agg = aggregate(df)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    for cid, grp in agg.groupby("concept_id"):
        xs = list(grp.n_samples)
        nodes = list(grp.nodes_mean)
        widths = list(grp.width_mean)
        if full_reference is not None:
            ref = full_reference[(full_reference.concept_id == cid)
                                 & (full_reference.final_nodes > 0)]
            if len(ref):
                xs.append(int(ref.iloc[0]["samples"]))
                nodes.append(float(ref.iloc[0]["final_nodes"]))
                widths.append(float(ref.iloc[0]["mean_xy_width"]))
        ax1.plot(xs, nodes, marker="o", label=cid)
        ax2.plot(xs, widths, marker="o", label=cid)
    ax1.set_xlabel(labels["xlabel"]); ax1.set_ylabel(labels["nodes"])
    ax1.set_title(labels["topo_title"])
    ax2.set_xlabel(labels["xlabel"]); ax2.set_ylabel(labels["width"])
    ax2.set_title(labels["env_title"])
    ax1.legend(fontsize=7, ncol=2); ax2.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    return fig


def failure_table(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby(["concept_id", "n_samples"])["failed"]
            .mean().mul(100).round(0).unstack(fill_value=0))
