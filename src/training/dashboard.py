"""
Streamlit dashboard for classification analysis and concept debugging.

Run: streamlit run src/training/dashboard.py
"""
import os
import json
import glob
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from neo4j import GraphDatabase
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import sys
from pathlib import Path

_VIZ = Path(__file__).resolve().parents[1] / "concept_creator" / "visualization"
if str(_VIZ) not in sys.path:
    sys.path.insert(0, str(_VIZ))

import plotting
import ged_breakdown

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "111122223333")
RESULTS_DIR = "training_results"


@st.cache_resource
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


def get_run_dirs():
    pattern = os.path.join(RESULTS_DIR, "run_*")
    return sorted(glob.glob(pattern), reverse=True)


def get_concept_positions(G: nx.Graph) -> dict:
    pos = {}
    for node_id, data in G.nodes(data=True):
        labels = data.get("labels", set())
        if isinstance(labels, list):
            labels = set(labels)

        if "Vector" in labels:
            x1 = data.get("x1", {})
            y1 = data.get("y1", {})
            x1 = x1["center"] if isinstance(x1, dict) and "center" in x1 else x1
            y1 = y1["center"] if isinstance(y1, dict) and "center" in y1 else y1
            if isinstance(x1, (int, float)) and isinstance(y1, (int, float)):
                pos[node_id] = (x1, y1)
        elif "x" in data and "y" in data:
            x = data["x"]
            y = data["y"]
            x = x["center"] if isinstance(x, dict) and "center" in x else x
            y = y["center"] if isinstance(y, dict) and "center" in y else y
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                pos[node_id] = (x, y)
    return pos


def render_graph(G: nx.Graph, height: str = "400px"):
    net = Network(height=height, width="100%", bgcolor="#0e1117", font_color="white")

    for node, data in G.nodes(data=True):
        labels = data.get("labels", set())
        if isinstance(labels, list):
            labels = set(labels)
        label_str = ", ".join(sorted(labels)) if isinstance(labels, set) else str(labels)

        title = f"{label_str}\n"
        for k, v in data.items():
            if k != "labels":
                title += f"{k}: {v}\n"

        if "StartPoint" in labels:
            color = "#4ecdc4"
        elif "EndPoint" in labels:
            color = "#ff6b6b"
        elif "IntersectionPoint" in labels:
            color = "#45b7d1"
        elif "CornerPoint" in labels:
            color = "#ffe66d"
        elif "Vector" in labels:
            color = "#96ceb4"
        else:
            color = "#95e1d3"

        net.add_node(str(node), label=label_str, title=title, color=color)

    for u, v, data in G.edges(data=True):
        net.add_edge(str(u), str(v))

    html = net.generate_html()
    components.html(html, height=int(height.replace("px", "")) + 20)


def parse_graph_properties(G: nx.Graph) -> nx.Graph:
    for node_id, data in G.nodes(data=True):
        parsed = {}
        for key, value in data.items():
            if isinstance(value, str):
                try:
                    parsed[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed[key] = value
            else:
                parsed[key] = value
        if "labels" in parsed and isinstance(parsed["labels"], list):
            parsed["labels"] = set(parsed["labels"])
        nx.set_node_attributes(G, {node_id: parsed})
    return G


@st.cache_data(ttl=300)
def load_concept_graph(concept_id: str) -> dict:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    G = nx.Graph()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (n {concept_id: $concept_id})
            WHERE n:Point OR n:Vector
            WITH n, labels(n) as lbls, properties(n) as props
            OPTIONAL MATCH (n)-[r]-(m {concept_id: $concept_id})
            WHERE m:Point OR m:Vector
            RETURN elementId(n) as nid, lbls, props, type(r) as rtype, elementId(m) as mid
            """,
            concept_id=concept_id,
        )
        nodes = {}
        edges = []
        for record in result:
            nid = record["nid"]
            if nid not in nodes:
                nodes[nid] = {"labels": set(record["lbls"]), **record["props"]}
            if record["mid"]:
                edges.append((record["nid"], record["mid"]))
        for nid, data in nodes.items():
            G.add_node(nid, **data)
        for u, v in edges:
            G.add_edge(u, v)
    driver.close()
    G = parse_graph_properties(G)
    return {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "graph": G}


@st.cache_data(ttl=300)
def cached_breakdown(run: str, image_id: str, concept_id: str) -> dict | None:
    graph = ged_breakdown.get_image_graph_if_present(get_driver(), image_id)
    if graph is None:
        return None
    concept_graph = load_concept_graph(concept_id)["graph"]
    return ged_breakdown.compute_breakdown(graph, concept_id, concept_graph)


@st.cache_data(ttl=300)
def get_all_concept_ids() -> list:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    with driver.session() as session:
        result = session.run(
            """
            MATCH (n)
            WHERE n.concept_id IS NOT NULL AND (n:Point OR n:Vector)
            RETURN DISTINCT n.concept_id AS cid
            ORDER BY cid
            """
        )
        ids = [r["cid"] for r in result]
    driver.close()
    return ids


# --- Streamlit App ---

st.set_page_config(page_title="NaturalAGI Classification Debugger", layout="wide")
st.title("Classification Analysis Dashboard")

# Sidebar: run selector
run_dirs = get_run_dirs()
if not run_dirs:
    st.warning("No training results found. Run a test first.")
    st.stop()

selected_run = st.sidebar.selectbox(
    "Select Run", run_dirs, format_func=lambda x: os.path.basename(x)
)

# Load run_config if available
config_path = os.path.join(selected_run, "run_config.json")
if os.path.exists(config_path):
    with open(config_path) as f:
        run_config = json.load(f)
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Git:** `{run_config.get('git', {}).get('commit', '?')[:8]}`")
    st.sidebar.markdown(f"**Branch:** `{run_config.get('git', {}).get('branch', '?')}`")
    st.sidebar.markdown(f"**Lib:** `{run_config.get('common_lib_version', '?')}`")

# File paths
incorrect_path = os.path.join(selected_run, "incorrect_results.csv")
metrics_path = os.path.join(selected_run, "metrics.csv")
per_class_path = os.path.join(selected_run, "per_class_metrics.csv")
cm_path = os.path.join(selected_run, "confusion_matrix.png")

# Tab layout
tab_overview, tab_incorrect, tab_concept, tab_config = st.tabs(
    ["Overview", "Misclassifications", "Concept Debugger", "Run Config"]
)

with tab_overview:
    col1, col2 = st.columns(2)
    with col1:
        if os.path.exists(metrics_path):
            metrics_df = pd.read_csv(metrics_path)
            st.dataframe(metrics_df, use_container_width=True)
    with col2:
        if os.path.exists(cm_path):
            st.image(cm_path, caption="Confusion Matrix")
    if os.path.exists(per_class_path):
        st.subheader("Per-Class Metrics")
        pc_df = pd.read_csv(per_class_path)
        st.dataframe(pc_df, use_container_width=True)

        # Bar chart
        fig, ax = plt.subplots(figsize=(12, 5))
        x = np.arange(len(pc_df))
        width = 0.25
        ax.bar(x - width, pc_df["precision"], width, label="Precision")
        ax.bar(x, pc_df["recall"], width, label="Recall")
        ax.bar(x + width, pc_df["f1_score"], width, label="F1")
        ax.set_xticks(x)
        ax.set_xticklabels(pc_df["class"])
        ax.legend()
        ax.set_ylabel("Score (%)")
        ax.set_title("Per-Class Metrics")
        st.pyplot(fig)
        plt.close()

with tab_incorrect:
    if os.path.exists(incorrect_path):
        df = pd.read_csv(incorrect_path)
        st.write(f"**{len(df)} misclassified images**")

        col1, col2 = st.columns(2)
        with col1:
            expected_opts = ["All"] + sorted(df["expected"].astype(str).unique().tolist())
            expected_filter = st.selectbox("Filter by expected class", expected_opts)
        with col2:
            predicted_opts = ["All"] + sorted(df["predicted"].astype(str).unique().tolist())
            predicted_filter = st.selectbox("Filter by predicted class", predicted_opts)

        filtered = df
        if expected_filter != "All":
            filtered = filtered[filtered["expected"].astype(str) == expected_filter]
        if predicted_filter != "All":
            filtered = filtered[filtered["predicted"].astype(str) == predicted_filter]

        st.write(f"Showing {len(filtered)} results")

        for idx, row in filtered.head(20).iterrows():
            img_name = os.path.basename(row.get("image_path", "N/A"))
            with st.expander(
                f"Image: {img_name} | Expected: {row['expected']}, Predicted: {row['predicted']}"
            ):
                try:
                    results = json.loads(row["classification_results"])
                    if results:
                        results_df = pd.DataFrame(results)
                        cols_order = ["concept_id", "is_minor", "similarity"]
                        extra = [c for c in results_df.columns if c not in cols_order]
                        results_df = results_df[
                            [c for c in cols_order if c in results_df.columns] + extra
                        ]
                        st.dataframe(results_df, use_container_width=True)
                    else:
                        st.info("No classification results")
                except (json.JSONDecodeError, TypeError):
                    st.warning(
                        "Cannot parse classification_results — run with JSON serialization fix first"
                    )
                st.markdown("---")
                st.caption("Image vs. expected concept — GED penalty breakdown")
                expected = str(row["expected"])
                try:
                    all_ids = get_all_concept_ids()
                except Exception:
                    all_ids = []
                try:
                    results_list = json.loads(row["classification_results"])
                except (json.JSONDecodeError, TypeError):
                    results_list = []
                cand = ged_breakdown.expected_concepts(all_ids, results_list, expected)
                if not cand:
                    st.info(f"No concept of class {expected} in Neo4j.")
                else:
                    labels = [
                        f"{c['concept_id']} "
                        + (f"(sim {c['similarity']:.3f})" if c["similarity"] is not None
                           else "(pre-filtered)")
                        for c in cand
                    ]
                    pick = st.selectbox("Expected concept", labels, key=f"exp_{idx}")
                    concept_id = cand[labels.index(pick)]["concept_id"]
                    try:
                        bd = cached_breakdown(selected_run, str(row["image_id"]), concept_id)
                    except Exception as e:
                        bd = None
                        st.warning(f"Breakdown unavailable: {e}")
                    if bd is None:
                        st.info(
                            "Image graph not in Neo4j (run cleaned / "
                            "delete_image_nodes=True). Re-run classification with "
                            "delete_image_nodes=False to enable the breakdown."
                        )
                    else:
                        st.caption(
                            f"GED cost {bd['cost']:.2f} · n1 {bd['n1']} · n2 {bd['n2']} "
                            f"· similarity {bd['similarity']:.3f}"
                        )
                        fig = plotting.comparison_figure(
                            bd["image_nodelink"], bd["concept_nodelink"], bd["edit_ops"]
                        )
                        components.html(
                            plotting.figure_html(fig),
                            height=int(fig.layout.height or 420) + 8,
                            scrolling=False,
                        )
                        ops_df = pd.DataFrame([
                            o for o in bd["edit_ops"] if o["op"] != "MATCH"
                        ])
                        if not ops_df.empty:
                            st.dataframe(ops_df, use_container_width=True)
    else:
        st.info("No incorrect_results.csv found for this run.")

with tab_concept:
    st.subheader("Concept Graph Viewer")

    try:
        concept_ids = get_all_concept_ids()
        if concept_ids:
            concept_id = st.selectbox("Select Concept", concept_ids)
        else:
            concept_id = st.text_input("Concept ID (e.g., 3_1, 7_1)")
    except Exception:
        concept_id = st.text_input("Concept ID (e.g., 3_1, 7_1)")

    if concept_id:
        try:
            data = load_concept_graph(concept_id)
            G = data["graph"]

            col1, col2, col3 = st.columns(3)
            col1.metric("Nodes", data["nodes"])
            col2.metric("Edges", data["edges"])
            col3.metric("Complexity", data["nodes"] + data["edges"])

            # Node type breakdown
            label_counts = {}
            for _, ndata in G.nodes(data=True):
                labels = ndata.get("labels", set())
                if isinstance(labels, list):
                    labels = set(labels)
                for lbl in labels:
                    if lbl in ("Point", "Vector"):
                        continue
                    label_counts[lbl] = label_counts.get(lbl, 0) + 1

            if label_counts:
                st.write("**Node types:**", label_counts)

            render_graph(G, height="500px")

        except Exception as e:
            st.error(f"Error loading concept: {e}")

with tab_config:
    if os.path.exists(config_path):
        st.json(run_config)
    else:
        st.info(
            "No run_config.json for this run. "
            "Run test_mnist_all() with the updated code to generate it."
        )
