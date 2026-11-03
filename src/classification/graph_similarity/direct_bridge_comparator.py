"""Direct-bridge gap closing — connect all close endpoint pairs with a
plain Point→Point edge, no synthetic Vector node, no k cap.

v1 had three bugs:
  1. Bridges were synthetic `Vector` nodes with only {x, y, dx, dy, length}
     features. Concept Vectors have many richer trained features
     (eccentricity, length_ratio_to_max, junction_angle_min, …). Substituting
     a featureless bridge against a rich concept Vector incurred a *higher*
     subst penalty than the bridge saved.
  2. DISTANCE_FRAC = 0.20 (~8 px on a 28×28 digit) — most broken pairs were
     filtered out before they were considered.
  3. MAX_BRIDGES = 3 — broken `8` typically has 4 dangling endpoint pairs
     (two loops × two breaks each); the cap stopped the search early.

This version:
  • No Vector node — we attach a plain edge `Point ↔ Point` between the
    two endpoints. The only feature that changes is `is_endpoint` on both
    Points (True → False).
  • DISTANCE_FRAC = 0.30 (~12 px).
  • Greedy maximum matching by distance — every endpoint can be in at
    most one bridge, but otherwise no k cap.

Energy is still definitional:

    E(bridges B) = Hungarian_cost(image + B, concept) + |B| · BRIDGE_TAX

We return the similarity at the chosen B*; the choice itself is implicit
in the matching (greedy by distance), so the comparator runs Hungarian
exactly once instead of enumerating subsets — much faster.
"""
from __future__ import annotations

import copy
import logging
import math
from typing import List, Tuple

import networkx as nx
import numpy as np
from scipy.optimize import linear_sum_assignment

from .cost_functions import (
    NodeCost,
    node_subst_cost,
    node_del_cost,
    node_ins_cost,
)


DISTANCE_FRAC = 0.30
BRIDGE_TAX = 1.0


class DirectBridgeComparator:
    requires_graph_preprocessing = True

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def compare(
        self,
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
        concept_name: str,
    ) -> float:
        try:
            bridged, num_bridges = self._apply_bridges(image_graph)
            hu_cost, sim = self._hungarian(bridged, concept_graph)
            total_cost = hu_cost + BRIDGE_TAX * num_bridges

            n1 = bridged.number_of_nodes() + bridged.number_of_edges()
            n2 = concept_graph.number_of_nodes() + concept_graph.number_of_edges()
            similarity = 1.0 - (total_cost / (total_cost + max(n1, n2, 1)))
            similarity = round(float(similarity), 4)
            logging.info(
                f"DirectBridge[{concept_name}]: bridges={num_bridges}, "
                f"hu_cost={hu_cost:.3f}, total={total_cost:.3f}, sim={similarity}"
            )
            return similarity
        except Exception as e:
            logging.error(
                f"DirectBridge error for {concept_name}: {e}", exc_info=True
            )
            return 0.0

    @staticmethod
    def _apply_bridges(graph: nx.Graph) -> Tuple[nx.Graph, int]:
        """Greedy max matching: pair closest endpoint Points until none left
        within DISTANCE_FRAC * graph diagonal."""
        endpoints = []
        xs, ys = [], []
        for node_id, data in graph.nodes(data=True):
            if "Point" not in data.get("labels", []):
                continue
            x = data.get("x")
            y = data.get("y")
            if x is None or y is None:
                continue
            xs.append(float(x))
            ys.append(float(y))
            ep = data.get("is_endpoint")
            if ep is True or ep == 1 or ep == 1.0:
                endpoints.append((node_id, float(x), float(y)))

        if len(endpoints) < 2 or not xs:
            return graph, 0

        diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
        if diag < 1e-9:
            return graph, 0
        max_dist = DISTANCE_FRAC * diag

        pairs = []
        for i in range(len(endpoints)):
            id_i, xi, yi = endpoints[i]
            for j in range(i + 1, len(endpoints)):
                id_j, xj, yj = endpoints[j]
                d = math.hypot(xj - xi, yj - yi)
                if d <= max_dist:
                    pairs.append((d, id_i, id_j))
        pairs.sort(key=lambda p: p[0])

        g = copy.deepcopy(graph)
        used = set()
        bridges = 0
        for d, id_i, id_j in pairs:
            if id_i in used or id_j in used:
                continue
            if id_i not in g or id_j not in g:
                continue
            if g.has_edge(id_i, id_j):
                continue
            g.add_edge(id_i, id_j, bridged=True)
            g.nodes[id_i]["is_endpoint"] = False
            g.nodes[id_j]["is_endpoint"] = False
            used.add(id_i)
            used.add(id_j)
            bridges += 1
        return g, bridges

    @staticmethod
    def _hungarian(image_graph: nx.Graph, concept_graph: nx.Graph) -> Tuple[float, float]:
        img_nodes = list(image_graph.nodes(data=True))
        con_nodes = list(concept_graph.nodes(data=True))
        m, n = len(img_nodes), len(con_nodes)
        if m == 0 or n == 0:
            return float("inf"), 0.0

        size = m + n
        INF = NodeCost.IMPOSSIBLE * 100.0
        C = np.full((size, size), INF, dtype=float)
        for i in range(m):
            img_data = img_nodes[i][1]
            for j in range(n):
                con_data = con_nodes[j][1]
                C[i, j] = node_subst_cost(img_data, con_data)
        for i in range(m):
            C[i, n + i] = node_del_cost(img_nodes[i][1])
        for j in range(n):
            C[m + j, j] = node_ins_cost(con_nodes[j][1])
        C[m:m + n, n:n + m] = 0.0

        row_ind, col_ind = linear_sum_assignment(C)
        total_cost = float(C[row_ind, col_ind].sum())

        n1 = image_graph.number_of_nodes() + image_graph.number_of_edges()
        n2 = concept_graph.number_of_nodes() + concept_graph.number_of_edges()
        similarity = 1.0 - (total_cost / (total_cost + max(n1, n2, 1)))
        return total_cost, similarity
