"""Section 1: 2→7 post-mortem against run_20260630_235356.

Reproduces the production decision path in-process (same modules the deployed
classification uses), never re-implementing scoring. Bucket semantics:

  A_prefiltered_all — no expected-class concept survived the complexity
    pre-filter (classification_orchestrator._classify_sequentially): the WTA
    competition never contained the expected class.
  B_similarity — an expected-class concept competed but lost on raw similarity.
  C_ranking — an expected-class concept won raw similarity yet lost the
    λ-adjusted ranking (complexity prior / minor flag flipped it).
"""
import csv
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from PIL import Image

from . import REPO, RUN_DIR, RUN_ID
from .infra import driver, timer

import ged_breakdown
import classification_orchestrator as orch
import concept_visualization as cviz
from graph_similarity import cost_functions as cf
from nuclio_handler import _annotate_range_widths, _cost_config_override
from services.graph_complexity_service import GraphComplexityService

PRIMARY_EXEMPLAR = "01233b59-f1a4-4cf6-8eb3-6b7d5bf95dbd"   # mnist_test_2_00766: канонічна «2»
CONTRAST_EXEMPLAR = "7e888443-f097-41e3-984e-75cc46344d5b"  # mnist_test_2_00984: курсивна «2»

_SKILL = REPO / ".claude/skills/debug-classification/explain_misclassification.py"


def load_params() -> dict:
    import json
    cfg = json.load(open(RUN_DIR / "run_config.json"))
    params = dict(cfg.get("classification_params", {}))
    resolved = cfg.get("features", {})
    params.setdefault("features", resolved.get("features") or params.get("features"))
    params.setdefault("node_costs", resolved.get("node_costs") or params.get("node_costs"))
    if params.get("diagnostic_weight_epsilon") is None:
        params["diagnostic_weight_epsilon"] = resolved.get("diagnostic_weight_epsilon")
    params.setdefault("ged_timeout", 5.0)
    return params


def load_confusion(expected: str = "2", predicted: str = "7") -> pd.DataFrame:
    rows = list(csv.DictReader(open(RUN_DIR / "incorrect_results.csv")))
    df = pd.DataFrame(rows)
    return df[(df["expected"] == expected) & (df["predicted"] == predicted)].reset_index(drop=True)


def load_run_concepts() -> dict:
    concepts = ged_breakdown.load_run_concepts(str(RUN_DIR))
    if not concepts:
        raise FileNotFoundError(f"No concept snapshot in {RUN_DIR}")
    return concepts


def rank_image(image_id: str, concepts: dict, params: dict):
    """Production ranking for one image; returns (image_cx, predicted, per-concept df)."""
    img = ged_breakdown.get_image_graph_if_present(driver(), image_id)
    if img is None:
        return None, None, None
    gcs = GraphComplexityService()
    image_cx = gcs.get_default_graph_complexity(img)
    with _cost_config_override(
        features=params["features"], costs=params["node_costs"],
        epsilon=params["diagnostic_weight_epsilon"],
    ):
        _annotate_range_widths(concepts)
        cf.compute_feature_global_spans(concepts)
        o = orch.ClassificationOrchestrator(driver(), ged_timeout=params["ged_timeout"])
        results = o._process_and_sort_results(
            o._classify_sequentially(img, concepts), image_id
        )
    by_id = {r.concept_id: r for r in results}
    rows = []
    for cid, g in sorted(concepts.items()):
        r = by_id.get(cid)
        rows.append({
            "concept_id": cid,
            "concept_cx": gcs.get_default_graph_complexity(g),
            "eligible": cid in by_id,
            "raw_sim": r.similarity if r else None,
            "adjusted": orch.complexity_adjusted_score(r) if r else None,
            "is_minor": r.is_minor if r else None,
        })
    predicted = results[0].concept_id if results else None
    return image_cx, predicted, pd.DataFrame(rows)


def _bucket(image_cx, predicted, ranking: pd.DataFrame, expected: str) -> dict:
    exp = ranking[ranking.concept_id.str.split("_").str[0] == expected]
    win = ranking[ranking.concept_id == predicted]
    row = {
        "image_cx": image_cx,
        "predicted_tool": predicted,
        "expected_eligible": [c for c in exp[exp.eligible].concept_id],
        "expected_prefiltered": [c for c in exp[~exp.eligible].concept_id],
    }
    if not exp.eligible.any():
        row["bucket"] = "A_prefiltered_all"
        return row
    elig = exp[exp.eligible].dropna(subset=["adjusted"])
    if elig.empty or win.empty or win.raw_sim.isna().all():
        row["bucket"] = "B_similarity"
        return row
    best = elig.loc[elig["adjusted"].idxmax()]
    win_raw = float(win.raw_sim.iloc[0])
    win_adj = float(win.adjusted.iloc[0])
    row["best_expected"] = best.concept_id
    row["best_expected_raw"] = float(best.raw_sim)
    row["best_expected_adj"] = float(best.adjusted)
    row["winner_raw"] = win_raw
    row["winner_adj"] = win_adj
    if best.raw_sim >= win_raw and best.adjusted < win_adj:
        row["bucket"] = "C_ranking"
    else:
        row["bucket"] = "B_similarity"
    return row


def bucket_all(image_ids: list[str], concepts: dict, params: dict,
               expected: str = "2") -> pd.DataFrame:
    records = []
    with timer(f"bucket_all over {len(image_ids)} images"):
        for i, image_id in enumerate(image_ids, 1):
            image_cx, predicted, ranking = rank_image(image_id, concepts, params)
            if ranking is None:
                records.append({"image_id": image_id, "bucket": "missing_in_neo4j"})
                continue
            row = _bucket(image_cx, predicted, ranking, expected)
            row["image_id"] = image_id
            records.append(row)
            if i % 10 == 0:
                print(f"  {i}/{len(image_ids)}")
    df = pd.DataFrame(records)
    df["c22_prefiltered"] = df["expected_prefiltered"].apply(
        lambda v: isinstance(v, list) and f"{expected}_2" in v
    )
    return df


def bucket_summary(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    out = df.groupby("bucket").size().rename("images").to_frame()
    out["share"] = (out["images"] / total * 100).round(1)
    out.loc["TOTAL"] = [total, 100.0]
    return out


def plot_buckets(df: pd.DataFrame):
    counts = df.groupby("bucket").size().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(7, 4))
    counts.plot.bar(ax=ax, color=["#c0392b", "#e67e22", "#2980b9", "#7f8c8d"][:len(counts)])
    ax.set_ylabel("зображень")
    ax.set_title("2→7: причини промаху (WTA так і не бачила концепт «2»?)")
    for i, v in enumerate(counts):
        ax.text(i, v + 0.5, str(v), ha="center")
    fig.tight_layout()
    return fig


def explain_cli(image_id: str, expected: str = "2", concept: str | None = None) -> str:
    cmd = [sys.executable, str(_SKILL), "--image-id", image_id,
           "--run", RUN_ID, "--expected", expected]
    if concept:
        cmd += ["--concept", concept]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    out = proc.stdout
    if proc.returncode != 0:
        out += f"\n[exit {proc.returncode}]\n{proc.stderr[-2000:]}"
    return out


def resolve_image_path(row: pd.Series) -> Path | None:
    return ged_breakdown.resolve_sample_path(row["image_path"])


def show_images(df: pd.DataFrame, n: int = 12):
    sample = df.head(n)
    cols = 6
    rows = (len(sample) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(2.2 * cols, 2.5 * rows))
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]
    for ax in axes[len(sample):]:
        ax.axis("off")
    for ax, (_, row) in zip(axes, sample.iterrows()):
        path = resolve_image_path(row)
        if path:
            ax.imshow(Image.open(path).convert("L"), cmap="gray")
        ax.set_title(Path(str(row["image_path"])).stem[-9:], fontsize=8)
        ax.axis("off")
    fig.suptitle("Приклади «2», класифіковані як «7»", fontweight="bold")
    fig.tight_layout()
    return fig


def _draw_graph(ax, g: nx.Graph, title: str) -> None:
    pos = cviz._compute_positions(g)
    points = [n for n in g.nodes if "Vector" not in g.nodes[n].get("labels", set())]
    vectors = [n for n in g.nodes if "Vector" in g.nodes[n].get("labels", set())]
    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#7f8c8d", width=2, alpha=0.6)
    if points:
        nx.draw_networkx_nodes(
            g, pos, nodelist=points, ax=ax, node_shape="o", node_size=420,
            node_color=[cviz._node_color(g.nodes[n].get("labels", set())) for n in points])
    if vectors:
        nx.draw_networkx_nodes(
            g, pos, nodelist=vectors, ax=ax, node_shape="s", node_size=170,
            node_color=[cviz._node_color(g.nodes[n].get("labels", set())) for n in vectors])
    labels = {n: cviz._label_abbrev(g.nodes[n].get("labels", set())) for n in g.nodes}
    nx.draw_networkx_labels(g, pos, labels=labels, ax=ax, font_size=6,
                            font_color="white", font_weight="bold")
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.axis("off")


def triptych(image_id: str, row: pd.Series, concepts: dict, params: dict,
             concept_ids: tuple[str, str] = ("2_2", "7_1")):
    """Original image | pre-reduction image graph | expected vs winning concepts."""
    gcs = GraphComplexityService()
    img_graph = ged_breakdown.get_image_graph_if_present(driver(), image_id)
    image_cx = gcs.get_default_graph_complexity(img_graph)
    fig, axes = plt.subplots(1, 2 + len(concept_ids), figsize=(5 * (2 + len(concept_ids)), 5))

    path = resolve_image_path(row)
    if path:
        axes[0].imshow(Image.open(path).convert("L"), cmap="gray")
    axes[0].set_title(f"Зображення\n{Path(str(row['image_path'])).name}",
                      fontsize=10, fontweight="bold")
    axes[0].axis("off")

    _draw_graph(axes[1], img_graph,
                f"Граф зображення (до редукції)\n{img_graph.number_of_nodes()} вузлів, "
                f"{img_graph.number_of_edges()} ребер → складність {image_cx}")

    for ax, cid in zip(axes[2:], concept_ids):
        g = concepts[cid]
        cx = gcs.get_default_graph_complexity(g)
        verdict = (f"складність {cx} > {image_cx} → ВІДФІЛЬТРОВАНО"
                   if cx > image_cx else f"складність {cx} ≤ {image_cx} → конкурує")
        _draw_graph(ax, g, f"Концепт {cid}\n{verdict}")

    fig.suptitle("Чому «2» впала у «7»: концепт 2_2 не пройшов пре-фільтр складності",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig


def construction_figure(row: pd.Series, params: dict):
    """Production skeletonization stages for one image — where anchor points get lost."""
    skel_dir = str(REPO / "src" / "skeletonization")
    if skel_dir not in sys.path:
        sys.path.insert(0, skel_dir)
    import cv2
    from settings import Settings
    from skeleton_gng_mapper import SkeletonGNGMapper

    path = resolve_image_path(row)
    if path is None:
        raise FileNotFoundError(f"Image not on host: {row['image_path']}")
    image = cv2.imread(str(path), 0)
    settings = Settings(
        kafka_topic="offline", dlq_topic="offline", kafka_bootstrap_servers="offline",
        skeletonization_threshold=params.get("skeletonization_threshold", 110),
        simplification_epsilon=params.get("simplification_epsilon", 4.55),
    )
    mapper = SkeletonGNGMapper(settings)

    stages = None
    threshold = mapper.skeletonization_threshold
    while threshold >= mapper.min_threshold and stages is None:
        try:
            binary = mapper.binary_image(image, threshold)
            skeleton = mapper.skeletonize(image, threshold)
            points = mapper.skeleton_to_points(skeleton)
            net = mapper.fit_gng(points)
            simplified = mapper._simplify_network(net)
            raw_graph = mapper._convert_to_networkx(simplified)
            merged = mapper._merge_junction_bridges(raw_graph, image, threshold, skeleton)
            if nx.is_connected(merged):
                stages = (threshold, binary, skeleton, points, raw_graph, merged)
        except Exception:
            pass
        if stages is None:
            threshold -= mapper.threshold_step
    if stages is None:
        raise RuntimeError("No threshold produced a connected graph")
    threshold, binary, skeleton, points, raw_graph, merged = stages

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    axes[0].imshow(image, cmap="gray")
    axes[0].set_title(f"1. Оригінал {path.name}", fontweight="bold")
    axes[1].imshow(binary, cmap="gray")
    axes[1].set_title(f"2. Бінаризація (поріг {threshold})", fontweight="bold")
    axes[2].imshow(skeleton, cmap="gray")
    axes[2].set_title("3. Скелет 1px + pruning", fontweight="bold")
    for ax in axes[:3]:
        ax.axis("off")

    axes[3].scatter(points[:, 0], points[:, 1], s=2, c="lightblue")
    for a, b in raw_graph.edges:
        axes[3].plot([raw_graph.nodes[a]["x"], raw_graph.nodes[b]["x"]],
                     [raw_graph.nodes[a]["y"], raw_graph.nodes[b]["y"]], "r-", lw=1.5)
    axes[3].set_title(f"4. GNG + RDP: {raw_graph.number_of_nodes()} вузлів", fontweight="bold")
    axes[3].invert_yaxis()
    axes[3].axis("equal")

    for ax, (g, label) in zip(
        axes[4:6],
        [(raw_graph, "5. Граф до junction-merge"), (merged, "6. Після junction-merge")],
    ):
        pos = {n: (g.nodes[n]["x"], g.nodes[n]["y"]) for n in g.nodes}
        endpoints = [n for n in g.nodes if g.degree(n) == 1]
        junctions = [n for n in g.nodes if g.degree(n) >= 3]
        nx.draw_networkx_edges(g, pos, ax=ax, edge_color="red", width=2)
        nx.draw_networkx_nodes(g, pos, ax=ax, node_size=50, node_color="yellow",
                               edgecolors="red")
        nx.draw_networkx_nodes(g, pos, nodelist=endpoints, ax=ax, node_size=110,
                               node_color="green", edgecolors="darkgreen")
        nx.draw_networkx_nodes(g, pos, nodelist=junctions, ax=ax, node_size=110,
                               node_color="blue", edgecolors="darkblue")
        cycles = len(nx.cycle_basis(g))
        ax.set_title(f"{label}\n{g.number_of_nodes()} вузлів, {len(endpoints)} endpoints, "
                     f"{len(junctions)} junctions, {cycles} циклів", fontweight="bold")
        ax.invert_yaxis()
        ax.axis("equal")

    fig.suptitle("Стадії побудови графа: де губляться якірні точки",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig
