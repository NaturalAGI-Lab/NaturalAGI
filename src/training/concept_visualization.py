"""Concept graph visualization and restore utilities."""

import json
import os

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
from neo4j import GraphDatabase


# ── Neo4j defaults ──────────────────────────────────────────
_NEO4J_URI = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
_NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
_NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "111122223333")

LABEL_COLORS = {
    "StartPoint": "#2ecc71",
    "EndPoint": "#e74c3c",
    "IntersectionPoint": "#f39c12",
    "CornerPoint": "#9b59b6",
    "Point": "#3498db",
    "Vector": "#95a5a6",
}

_COLOR_PRIORITY = [
    "StartPoint", "EndPoint", "IntersectionPoint",
    "CornerPoint", "Point", "Vector",
]

_LABEL_ABBREVS = [
    ("StartPoint", "StP"), ("EndPoint", "EnP"),
    ("IntersectionPoint", "IntP"), ("CornerPoint", "CrP"),
    ("HorizontalVector", "H"), ("VerticalVector", "V"),
    ("Vector", "Vec"),
]


# ── Helpers ─────────────────────────────────────────────────

def _node_color(labels):
    for l in _COLOR_PRIORITY:
        if l in labels:
            return LABEL_COLORS[l]
    return "#bdc3c7"


def _label_abbrev(labels):
    for l, abbr in _LABEL_ABBREVS:
        if l in labels:
            return abbr
    return "P"


def _parse_coord(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict) and "center" in val:
        return float(val["center"])
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            pass
        try:
            d = json.loads(val)
            if isinstance(d, dict) and "center" in d:
                return float(d["center"])
        except Exception:
            pass
    return None


def _compute_positions(G):
    pos = {}
    for node, data in G.nodes(data=True):
        nx_val = _parse_coord(data.get("normalized_x"))
        ny_val = _parse_coord(data.get("normalized_y"))
        if nx_val is not None and ny_val is not None:
            pos[node] = (nx_val, -ny_val)

    for node in G.nodes:
        if node in pos:
            continue
        neighbors = [n for n in G.neighbors(node) if n in pos]
        if neighbors:
            ax = sum(pos[n][0] for n in neighbors) / len(neighbors)
            ay = sum(pos[n][1] for n in neighbors) / len(neighbors)
            pos[node] = (
                ax + 0.03 * (hash(str(node)) % 5 - 2),
                ay + 0.03 * (hash(str(node)) % 7 - 3),
            )
        else:
            pos[node] = (0.0, 0.0)
    return pos


# ── Loaders ─────────────────────────────────────────────────

def load_concepts_from_neo4j(uri=None, user=None, password=None):
    """Fetch all concept graphs from Neo4j. Returns {concept_id: nx.Graph}."""
    uri = uri or _NEO4J_URI
    user = user or _NEO4J_USER
    password = password or _NEO4J_PASS

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        cids = [
            r["cid"]
            for r in session.run(
                "MATCH (n) WHERE n.concept_id IS NOT NULL "
                "RETURN DISTINCT n.concept_id AS cid ORDER BY cid"
            )
        ]

    graphs = {}
    for cid in cids:
        with driver.session() as session:
            # Fetch all nodes with their properties
            node_records = list(session.run(
                "MATCH (n) WHERE n.concept_id = $cid "
                "RETURN elementId(n) AS node_id, labels(n) AS labels, "
                "       properties(n) AS props",
                cid=cid,
            ))
            # Fetch all edges
            edge_records = list(session.run(
                "MATCH (n {concept_id: $cid})-[r]-(m {concept_id: $cid}) "
                "WHERE elementId(n) < elementId(m) "
                "RETURN elementId(n) AS src, elementId(m) AS tgt",
                cid=cid,
            ))
        G = nx.Graph()
        for rec in node_records:
            nid = rec["node_id"]
            G.add_node(nid, labels=set(rec["labels"]), **rec["props"])
        for rec in edge_records:
            G.add_edge(rec["src"], rec["tgt"])
        graphs[cid] = G
    driver.close()
    return graphs


def load_concepts_from_json(path):
    """Load concept graphs from a JSON snapshot file. Returns {concept_id: nx.Graph}."""
    with open(path) as f:
        data = json.load(f)

    graphs = {}
    for cid, gdata in data.items():
        G = nx.Graph()
        for n in gdata.get("nodes", []):
            nid = n.get("id", n.get("uuid", str(id(n))))
            labels = set(n.get("labels", []))
            props = {k: v for k, v in n.items() if k not in ("id", "labels")}
            G.add_node(nid, labels=labels, **props)
        for e in gdata.get("edges", gdata.get("links", [])):
            G.add_edge(e["source"], e["target"])
        graphs[cid] = G
    return graphs


def load_concepts(source="neo4j"):
    """Load concepts from Neo4j (source="neo4j") or from a JSON file path."""
    if source == "neo4j":
        graphs = load_concepts_from_neo4j()
        print(f"Loaded {len(graphs)} concepts from Neo4j")
    else:
        graphs = load_concepts_from_json(source)
        print(f"Loaded {len(graphs)} concepts from {source}")
    for cid, G in sorted(graphs.items()):
        print(f"  {cid}: {len(G.nodes)} nodes, {len(G.edges)} edges")
    return graphs


# ── Visualization ───────────────────────────────────────────

def plot_concepts(concept_graphs, title=None):
    """Plot all concept graphs in a grid."""
    concept_ids = sorted(concept_graphs.keys())
    n = len(concept_ids)
    if n == 0:
        print("No concepts to plot.")
        return

    cols = min(4, n)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 5 * rows))
    if rows == 1 and cols == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]
    elif cols == 1:
        axes = [[a] for a in axes]

    for idx, cid in enumerate(concept_ids):
        ax = axes[idx // cols][idx % cols]
        G = concept_graphs[cid]
        if not G.nodes:
            ax.set_title(f"Concept {cid}\n(empty)")
            ax.axis("off")
            continue

        pos = _compute_positions(G)

        points = [n for n in G.nodes if "Vector" not in G.nodes[n].get("labels", set())]
        vectors = [n for n in G.nodes if "Vector" in G.nodes[n].get("labels", set())]

        nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#7f8c8d", width=2, alpha=0.6)
        if points:
            nx.draw_networkx_nodes(
                G, pos, nodelist=points, ax=ax, node_shape="o", node_size=500,
                node_color=[_node_color(G.nodes[n].get("labels", set())) for n in points],
            )
        if vectors:
            nx.draw_networkx_nodes(
                G, pos, nodelist=vectors, ax=ax, node_shape="s", node_size=200,
                node_color=[_node_color(G.nodes[n].get("labels", set())) for n in vectors],
            )

        labels = {n: _label_abbrev(G.nodes[n].get("labels", set())) for n in G.nodes}
        nx.draw_networkx_labels(
            G, pos, labels=labels, ax=ax,
            font_size=7, font_color="white", font_weight="bold",
        )

        ax.set_title(
            f"Concept {cid}\n({len(points)}P + {len(vectors)}V, {len(G.edges)}E)",
            fontsize=11, fontweight="bold",
        )
        ax.axis("off")

    for idx in range(n, rows * cols):
        axes[idx // cols][idx % cols].axis("off")

    legend_patches = [mpatches.Patch(color=c, label=l) for l, c in LABEL_COLORS.items()]
    fig.legend(handles=legend_patches, loc="lower center", ncol=len(legend_patches), fontsize=10)
    plt.suptitle(title or "Concept Graphs", fontsize=16, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.show()


# ── Restore snapshot to Neo4j ───────────────────────────────

def restore_concepts_to_neo4j(snapshot_path, uri=None, user=None, password=None):
    """Load a JSON concept snapshot and write all concepts into Neo4j.

    Clears existing concepts before writing.
    """
    uri = uri or _NEO4J_URI
    user = user or _NEO4J_USER
    password = password or _NEO4J_PASS

    with open(snapshot_path) as f:
        snapshot = json.load(f)

    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        session.run("MATCH (n) WHERE n.concept_id IS NOT NULL DETACH DELETE n")
        print("Cleared existing concepts from Neo4j.")

    for cid, gdata in snapshot.items():
        nodes = gdata.get("nodes", [])
        edges = gdata.get("edges", gdata.get("links", []))

        id_map = {}
        with driver.session() as session:
            for node in nodes:
                labels = node.get("labels", [])
                label_str = ":".join(labels)
                props = {}
                for k, v in node.items():
                    if k == "labels":
                        continue
                    if isinstance(v, (dict, list)):
                        props[k] = json.dumps(v)
                    else:
                        props[k] = v
                old_id = node.get("id", node.get("uuid"))
                result = session.run(
                    f"CREATE (n:{label_str} $props) RETURN elementId(n) AS nid",
                    props=props,
                )
                id_map[old_id] = result.single()["nid"]

            for edge in edges:
                src = id_map.get(edge["source"])
                tgt = id_map.get(edge["target"])
                rel_type = edge.get("type", "CONNECTED_TO")
                if src and tgt:
                    session.run(
                        f"MATCH (a), (b) WHERE elementId(a) = $src AND elementId(b) = $tgt "
                        f"CREATE (a)-[:{rel_type}]->(b)",
                        src=src, tgt=tgt,
                    )

        print(f"  Restored concept {cid}: {len(nodes)} nodes, {len(edges)} edges")

    driver.close()
    print(f"\nDone. Restored {len(snapshot)} concepts from {snapshot_path}")
