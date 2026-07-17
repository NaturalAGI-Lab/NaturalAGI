"""Section 2 (S6): which parameters concepts store and how much the initial
parameter count shrinks during formation.

Counting convention (documented for the report):
- range property {min, max, center} = 2 stored numbers (center is derived);
- scalar number / string = 1; list = len(list); labels = len(labels);
- bookkeeping props (ids/sessions) are excluded on both sides.
"""
import json

import networkx as nx
import pandas as pd

from .formation_lab import ALL_CONCEPTS, SAMPLES_ROOT

BOOKKEEPING = {"id", "uuid", "image_id", "session_id", "concept_id", "graph_id",
               "concept_name", "name"}


def _is_range(v) -> bool:
    return isinstance(v, dict) and "min" in v and "max" in v


def _param_count(props: dict) -> dict:
    counts = {"range": 0, "scalar": 0, "string": 0, "list": 0, "labels": 0}
    for key, value in props.items():
        if key in BOOKKEEPING:
            continue
        if key == "labels":
            counts["labels"] += len(value)
        elif _is_range(value):
            counts["range"] += 1
        elif isinstance(value, (int, float, bool)):
            counts["scalar"] += 1
        elif isinstance(value, str):
            counts["string"] += 1
        elif isinstance(value, (list, tuple, set)):
            counts["list"] += len(value)
    counts["stored_values"] = (2 * counts["range"] + counts["scalar"]
                               + counts["string"] + counts["list"] + counts["labels"])
    return counts


def _graph_params(g: nx.Graph) -> dict:
    total = {"range": 0, "scalar": 0, "string": 0, "list": 0, "labels": 0,
             "stored_values": 0}
    for _, props in g.nodes(data=True):
        c = _param_count(props)
        for k in total:
            total[k] += c[k]
    graph_level = _param_count(dict(g.graph))
    for k in total:
        total[k] += graph_level[k]
    return total


def _load_sample_graphs(concept_id: str) -> list[nx.Graph]:
    samples_dir = SAMPLES_ROOT / concept_id
    if not samples_dir.exists():
        raise FileNotFoundError(
            f"{samples_dir} відсутній — виконайте export_session_graphs('{concept_id}') "
            f"(після ре-інгесту навчальних вибірок)."
        )
    graphs = []
    for f in sorted(samples_dir.glob("*.json")):
        graphs.append(nx.node_link_graph(json.loads(f.read_text()), edges="edges"))
    return graphs


def compression_table(snapshot: dict[str, nx.Graph],
                      concepts: list[str] = ALL_CONCEPTS) -> pd.DataFrame:
    rows = []
    for cid in concepts:
        concept = snapshot[cid]
        samples = _load_sample_graphs(cid)
        input_nodes = sum(g.number_of_nodes() for g in samples)
        input_edges = sum(g.number_of_edges() for g in samples)
        input_values = sum(_graph_params(g)["stored_values"] for g in samples)
        cp = _graph_params(concept)
        rows.append({
            "concept_id": cid,
            "samples": len(samples),
            "input_nodes": input_nodes,
            "input_edges": input_edges,
            "input_values": input_values,
            "concept_nodes": concept.number_of_nodes(),
            "concept_edges": concept.number_of_edges(),
            "concept_values": cp["stored_values"],
            "concept_ranges": cp["range"],
            "topology_compression_x": round(input_nodes / max(concept.number_of_nodes(), 1), 1),
            "value_compression_x": round(input_values / max(cp["stored_values"], 1), 1),
        })
    df = pd.DataFrame(rows)
    total = df.select_dtypes("number").sum()
    total["concept_id"] = "TOTAL"
    total["topology_compression_x"] = round(total.input_nodes / total.concept_nodes, 1)
    total["value_compression_x"] = round(total.input_values / total.concept_values, 1)
    return pd.concat([df, total.to_frame().T], ignore_index=True)


def property_survival(snapshot: dict[str, nx.Graph],
                      concepts: list[str] = ALL_CONCEPTS) -> pd.DataFrame:
    """Which properties image nodes carry vs which survive on concept nodes."""
    def prop_presence(graphs: list[nx.Graph]) -> pd.Series:
        counts: dict[str, int] = {}
        nodes = 0
        for g in graphs:
            for _, props in g.nodes(data=True):
                nodes += 1
                for key, value in props.items():
                    if key in BOOKKEEPING or value is None:
                        continue
                    counts[key] = counts.get(key, 0) + 1
        return pd.Series(counts) / max(nodes, 1)

    image_side = prop_presence(
        [g for cid in concepts for g in _load_sample_graphs(cid)])
    concept_side = prop_presence([snapshot[cid] for cid in concepts])
    df = pd.DataFrame({
        "image_nodes_share": image_side.round(3),
        "concept_nodes_share": concept_side.round(3),
    }).fillna(0.0)
    df["survives"] = df["concept_nodes_share"] > 0
    return df.sort_values("concept_nodes_share", ascending=False)


def property_kinds(snapshot: dict[str, nx.Graph]) -> pd.DataFrame:
    """Per node label kind: how many properties of each type a concept stores."""
    rows = []
    for cid, g in sorted(snapshot.items()):
        for _, props in g.nodes(data=True):
            kind = "Vector" if "Vector" in set(map(str, props.get("labels", []))) else "Point"
            c = _param_count(props)
            rows.append({"concept_id": cid, "node_kind": kind, **c})
    return (pd.DataFrame(rows)
            .groupby(["concept_id", "node_kind"])
            .agg(nodes=("stored_values", "count"),
                 ranges_mean=("range", "mean"),
                 scalars_mean=("scalar", "mean"),
                 strings_mean=("string", "mean"),
                 values_mean=("stored_values", "mean"))
            .round(2))
