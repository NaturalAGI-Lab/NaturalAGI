"""Section 3 (S5): reduction convergence — how many steps until a stable concept.

Two levels: inner critical-point reduction iterations per merge (cap 6) and the
outer per-sample trajectory (after how many samples the concept stops changing).
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .formation_lab import (ALL_CONCEPTS, PROBE_OUT_ROOT, SAMPLES_ROOT,
                            export_session_graphs, load_events, run_probe)
from .infra import timer

OUT = PROBE_OUT_ROOT / "convergence"


def probe_dir(concept_id: str) -> Path:
    return OUT / concept_id


def run_convergence_probes(concepts: list[str] = ALL_CONCEPTS,
                           force: bool = False) -> pd.DataFrame:
    rows = []
    for cid in concepts:
        out_dir = probe_dir(cid)
        if force or not (out_dir / "summary.json").exists():
            samples = SAMPLES_ROOT / cid
            if not samples.exists():
                export_session_graphs(cid, samples)
            with timer(f"probe {cid}"):
                run_probe(samples, out_dir, concept_id=cid)
        summ = json.loads((out_dir / "summary.json").read_text())
        counts = summ["step_node_edge_counts"]
        final = counts[-1]
        rows.append({
            "concept_id": cid,
            "samples": len(counts),
            "final_nodes": final["nodes"],
            "final_edges": final["edges"],
            "mean_xy_width": summ.get("mean_xy_width"),
            "failed": final["nodes"] == 0,
        })
    return pd.DataFrame(rows)


def step_trajectory(concept_id: str) -> pd.DataFrame:
    summ = json.loads((probe_dir(concept_id) / "summary.json").read_text())
    return pd.DataFrame(summ["step_node_edge_counts"])


def envelope_trajectory(concept_id: str) -> pd.DataFrame:
    df = pd.read_csv(probe_dir(concept_id) / "range_evolution.csv")
    df["width_xy"] = (df["width_x"] + df["width_y"]) / 2
    return df.groupby("step")["width_xy"].mean().reset_index()


def cpp_iterations(concept_id: str) -> list[int]:
    return [e["iterations"] for e in load_events(probe_dir(concept_id))
            if e.get("type") == "cpp_iterations" and e.get("iterations") is not None]


def stability_step(concept_id: str, width_tol: float = 0.02, k: int = 5) -> dict:
    """Smallest sample index m after which the concept is stable.

    Topology: node+edge counts unchanged for every later step. Envelopes:
    mean width grows < width_tol per step for k consecutive steps.
    """
    traj = step_trajectory(concept_id)
    final = (traj.iloc[-1]["nodes"], traj.iloc[-1]["edges"])
    m_topology = int(traj.iloc[0]["step"])
    for _, r in traj.iterrows():
        if (r["nodes"], r["edges"]) != final:
            m_topology = int(r["step"]) + 1

    env = envelope_trajectory(concept_id)
    growth = env["width_xy"].diff().abs()
    m_env = int(env.iloc[-1]["step"])
    stable_run = 0
    for step, g in zip(env["step"].iloc[1:], growth.iloc[1:]):
        stable_run = stable_run + 1 if g < width_tol else 0
        if stable_run >= k:
            m_env = int(step) - k + 1
            break
    return {"concept_id": concept_id, "m_topology": m_topology,
            "m_envelope": m_env, "total_samples": int(traj.iloc[-1]["step"])}


def stability_table(concepts: list[str] = ALL_CONCEPTS) -> pd.DataFrame:
    return pd.DataFrame([stability_step(c) for c in concepts
                         if (probe_dir(c) / "summary.json").exists()])


def plot_trajectories(concepts: list[str] = ALL_CONCEPTS):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    for cid in concepts:
        if not (probe_dir(cid) / "summary.json").exists():
            continue
        traj = step_trajectory(cid)
        ax1.plot(traj["step"], traj["nodes"], marker=".", label=cid)
        env = envelope_trajectory(cid)
        ax2.plot(env["step"], env["width_xy"], marker=".", label=cid)
    ax1.set_xlabel("зразок №"); ax1.set_ylabel("вузлів у концепті")
    ax1.set_title("Топологія: вузли vs номер зразка")
    ax2.set_xlabel("зразок №"); ax2.set_ylabel("середня ширина діапазону (x,y)")
    ax2.set_title("Конверти: насичення діапазонів")
    ax1.legend(fontsize=7, ncol=2); ax2.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    return fig


def plot_cpp_histogram(concepts: list[str] = ALL_CONCEPTS):
    all_iters = []
    for cid in concepts:
        if (probe_dir(cid) / "events.jsonl").exists():
            all_iters += cpp_iterations(cid)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(all_iters, bins=range(0, 8), align="left", color="#2980b9", rwidth=0.8)
    ax.set_xlabel("ітерацій критично-точкової редукції на злиття (ліміт 6)")
    ax.set_ylabel("злиттів")
    ax.set_title(f"Внутрішній цикл редукції ({len(all_iters)} злиттів)")
    fig.tight_layout()
    return fig
