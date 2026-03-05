import logging
from typing import List

import numpy as np
import networkx as nx
import ot

from . import node_pair_cost_kernel as kernel

logger = logging.getLogger(__name__)


def _structure_matrix(graph: nx.Graph, node_order: List) -> np.ndarray:
    n = len(node_order)
    if n == 0:
        return np.zeros((0, 0), dtype=np.float64)

    raw = nx.floyd_warshall_numpy(graph, nodelist=node_order)
    finite_mask = np.isfinite(raw)
    max_finite = raw[finite_mask].max() if finite_mask.any() else 1.0
    raw[~finite_mask] = 2.0 * max_finite

    denom = max_finite if max_finite > 0 else 1.0
    raw = raw / denom

    return raw.astype(np.float64)


class FGWComparator:

    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha

    def compare(
        self,
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
        concept_name: str,
    ) -> float:
        try:
            M, concept_nodes, image_nodes = kernel.build_cost_matrix(
                image_graph, concept_graph
            )
            n_con = len(concept_nodes)
            n_img = len(image_nodes)

            if n_con == 0 or n_img == 0:
                logger.warning("Empty graph for concept %s", concept_name)
                return 0.0

            # Source = concept (fixed marginal), target = image (relaxed)
            C1 = _structure_matrix(concept_graph, concept_nodes)
            C2 = _structure_matrix(image_graph, image_nodes)
            p = np.ones(n_con, dtype=np.float64) / n_con

            _, log = ot.gromov.semirelaxed_fused_gromov_wasserstein(
                M, C1, C2, p,
                loss_fun="square_loss",
                alpha=self.alpha,
                log=True,
            )

            fgw_dist = float(log["srfgw_dist"])
            similarity = round(1.0 / (1.0 + fgw_dist), 4)

            logger.info(
                "FGW: concept=%s n_con=%d n_img=%d fgw_dist=%.4f similarity=%.4f alpha=%.2f",
                concept_name, n_con, n_img, fgw_dist, similarity, self.alpha,
            )
            return similarity

        except Exception as e:
            logger.error("FGW failed for concept %s: %s", concept_name, e, exc_info=True)
            return 0.0
