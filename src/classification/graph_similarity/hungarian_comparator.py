"""Optimal-assignment graph similarity via the Hungarian algorithm.

GED (the default comparator) uses a heuristic A*-style search that
approximates the minimum edit cost — fast but inexact and sensitive to
timeout. This comparator gives a deterministic optimal one-to-one
assignment between image and concept nodes using
`scipy.optimize.linear_sum_assignment`.

The cost matrix is the standard assignment formulation for GED:
- top-left  m × n: substitution cost(img_i, con_j)
- top-right m × m: only diagonal = deletion cost(img_i); off-diagonal INF
- bottom-left  n × n: only diagonal = insertion cost(con_j); off-diagonal INF
- bottom-right n × m: zeros (dummy↔dummy can match freely)

The optimal total cost is normalized into a [0,1] similarity exactly the
same way as the GED comparator so downstream ranking is comparable.
"""
from __future__ import annotations

import logging

import networkx as nx
import numpy as np
from scipy.optimize import linear_sum_assignment

from .cost_functions import (
    NodeCost,
    node_subst_cost,
    node_del_cost,
    node_ins_cost,
)


class HungarianComparator:

    def __init__(self, timeout: float = 15.0):
        # timeout is unused (Hungarian is exact and runs in O((m+n)^3))
        # but kept for protocol parity with GEDComparator.
        self.timeout = timeout

    def compare(
        self,
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
        concept_name: str,
    ) -> float:
        logging.info(
            f"Comparing graph with concept {concept_name} using Hungarian assignment"
        )
        try:
            img_nodes = list(image_graph.nodes(data=True))
            con_nodes = list(concept_graph.nodes(data=True))
            m, n = len(img_nodes), len(con_nodes)
            if m == 0 or n == 0:
                return 0.0

            size = m + n
            INF = NodeCost.IMPOSSIBLE * 100.0
            C = np.full((size, size), INF, dtype=float)

            for i in range(m):
                img_data = img_nodes[i][1]
                for j in range(n):
                    con_data = con_nodes[j][1]
                    C[i, j] = node_subst_cost(img_data, con_data)

            # Deletion slots: image_i → column n+i (and only that one).
            for i in range(m):
                C[i, n + i] = node_del_cost(img_nodes[i][1])

            # Insertion slots: row m+j → concept_j (and only that one).
            for j in range(n):
                C[m + j, j] = node_ins_cost(con_nodes[j][1])

            # Bottom-right block: dummies match each other freely.
            C[m:m + n, n:n + m] = 0.0

            row_ind, col_ind = linear_sum_assignment(C)
            total_cost = float(C[row_ind, col_ind].sum())

            n1 = image_graph.number_of_nodes() + image_graph.number_of_edges()
            n2 = concept_graph.number_of_nodes() + concept_graph.number_of_edges()
            similarity = 1.0 - (total_cost / (total_cost + max(n1, n2, 1)))
            similarity = round(similarity, 4)
            logging.info(
                f"Hungarian: cost={total_cost:.3f}, n1={n1}, n2={n2}, sim={similarity}"
            )
            return similarity

        except Exception as e:
            logging.error(f"Hungarian error: {e}", exc_info=True)
            return 0.0
