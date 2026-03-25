import logging
from typing import Any, List, Tuple

import numpy as np
import networkx as nx

from . import cost_functions as _cf

logger = logging.getLogger(__name__)


def labels_compatible(
    image_node: dict[str, Any],
    concept_node: dict[str, Any],
) -> bool:
    image_labels = set(image_node.get("labels", []))
    concept_labels = set(concept_node.get("labels", []))
    if not image_labels or not concept_labels:
        return False
    return concept_labels.issubset(image_labels)


def node_property_cost(
    image_node: dict[str, Any],
    concept_node: dict[str, Any],
) -> float:
    common = (
        set(concept_node.keys())
        & set(image_node.keys())
        & set(_cf.features)
    )
    if not common:
        return _cf.NodeCost.NO_MATCH

    raw_weights = {p: _cf.FEATURE_WEIGHTS.get(p, 1.0) for p in common}
    total_weight = sum(raw_weights.values())
    if total_weight < 1e-9:
        return _cf.NodeCost.NO_MATCH

    total = 0.0
    checked = 0

    for feat in _cf.features:
        c_val = concept_node.get(feat)
        i_val = image_node.get(feat)

        if c_val is None and i_val is None:
            continue
        if i_val is None and c_val is not None:
            continue

        w = raw_weights.get(feat)
        if w is None:
            continue
        nw = w / total_weight

        if c_val is None and i_val is not None:
            total += nw
            checked += 1
            continue

        cost = _cf._calculate_property_similarity_cost(
            c_val, i_val, feat, nw
        )
        total += min(cost, nw)
        checked += 1

    return total if checked > 0 else _cf.NodeCost.NO_COST


def build_cost_matrix(
    image_graph: nx.Graph,
    concept_graph: nx.Graph,
) -> Tuple[np.ndarray, List, List]:
    concept_nodes = list(concept_graph.nodes())
    image_nodes = list(image_graph.nodes())
    n_con = len(concept_nodes)
    n_img = len(image_nodes)

    M = np.full((n_con, n_img), _cf.NodeCost.IMPOSSIBLE, dtype=np.float64)

    for i, con_n in enumerate(concept_nodes):
        con_data = concept_graph.nodes[con_n]
        for j, img_n in enumerate(image_nodes):
            img_data = image_graph.nodes[img_n]
            if labels_compatible(img_data, con_data):
                M[i, j] = node_property_cost(img_data, con_data)

    logger.debug(
        "Cost matrix shape: %s, compatible_pairs: %d/%d",
        M.shape, int((M < _cf.NodeCost.IMPOSSIBLE).sum()), n_con * n_img,
    )
    return M, concept_nodes, image_nodes
