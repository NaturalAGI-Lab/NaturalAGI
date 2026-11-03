"""Maximum-common-subgraph similarity (no edit costs).

GED asks "how expensive is it to turn the image into the concept" and needs a
cost for every edit operation. A concept in this project *is* a common minor of
its training graphs, so the more direct question is "how much of the concept's
structure is literally present in the image". That is the maximum common
induced subgraph (MCS) of the two graphs:

- a pair (image node i, concept node j) is *compatible* when the labels match
  and the image node's features sit inside the concept node's bands closely
  enough (`node_subst_cost < compat_cost`, default: anything that is not a
  NO_MATCH);
- the modular product keeps two compatible pairs adjacent when adjacency
  agrees in both graphs (edge in both, or edge in neither);
- a maximum clique of the product is an MCS (Levi 1973).

Similarity is the size of the MCS (nodes + edges) over the size of the larger
graph (Bunke & Shearer 1998), so a tiny concept cannot score 1.0 against a rich
image just by being contained in it. The result is also the explanation: the
matched pairs are exactly the structure the image shares with the concept.
"""
from __future__ import annotations

import logging
import time

import networkx as nx

from .cost_functions import NodeCost, node_subst_cost


class MCSComparator:

    def __init__(
        self,
        timeout: float = 0.5,
        compat_cost: float = NodeCost.NO_MATCH,
        norm: str = "max",
    ):
        # timeout bounds the clique enumeration per graph pair; the best clique
        # found so far is used when it expires.
        self.timeout = timeout
        self.compat_cost = compat_cost
        self.norm = norm
        self.last_matching: list = []

    def compare(
        self,
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
        concept_name: str,
    ) -> float:
        try:
            img_nodes = list(image_graph.nodes(data=True))
            con_nodes = list(concept_graph.nodes(data=True))
            if not img_nodes or not con_nodes:
                return 0.0

            pairs = []
            costs = {}
            for i, (_, img_data) in enumerate(img_nodes):
                for j, (_, con_data) in enumerate(con_nodes):
                    cost = node_subst_cost(img_data, con_data)
                    if cost < self.compat_cost:
                        costs[(i, j)] = cost
                        pairs.append((i, j))
            if not pairs:
                self.last_matching = []
                return 0.0

            img_ids = [n for n, _ in img_nodes]
            con_ids = [n for n, _ in con_nodes]
            product = nx.Graph()
            product.add_nodes_from(range(len(pairs)))
            for a in range(len(pairs)):
                i, j = pairs[a]
                for b in range(a + 1, len(pairs)):
                    k, l = pairs[b]
                    if i == k or j == l:
                        continue
                    if image_graph.has_edge(img_ids[i], img_ids[k]) == concept_graph.has_edge(
                        con_ids[j], con_ids[l]
                    ):
                        product.add_edge(a, b)

            deadline = time.monotonic() + self.timeout
            best_size, best_cost, best_clique = 0, float("inf"), []
            for clique in nx.find_cliques(product):
                edges = sum(
                    1
                    for x in range(len(clique))
                    for y in range(x + 1, len(clique))
                    if concept_graph.has_edge(
                        con_ids[pairs[clique[x]][1]], con_ids[pairs[clique[y]][1]]
                    )
                )
                size = len(clique) + edges
                cost = sum(costs[pairs[c]] for c in clique)
                if size > best_size or (size == best_size and cost < best_cost):
                    best_size, best_cost, best_clique = size, cost, clique
                if time.monotonic() > deadline:
                    logging.info(f"MCS: clique enumeration timed out for {concept_name}")
                    break

            self.last_matching = [
                (img_ids[pairs[c][0]], con_ids[pairs[c][1]]) for c in best_clique
            ]
            img_size = image_graph.number_of_nodes() + image_graph.number_of_edges()
            con_size = concept_graph.number_of_nodes() + concept_graph.number_of_edges()
            denom = con_size if self.norm == "concept" else max(img_size, con_size)
            similarity = best_size / max(denom, 1)
            # Residual band violation only breaks ties between equally large matches.
            if best_clique:
                similarity -= 0.01 * (best_cost / len(best_clique)) / NodeCost.NO_MATCH
            similarity = round(max(similarity, 0.0), 4)
            logging.info(
                f"MCS: {concept_name} matched {len(best_clique)} nodes, "
                f"size={best_size}, img={img_size}, con={con_size}, sim={similarity}"
            )
            return similarity

        except Exception as e:
            logging.error(f"MCS error: {e}", exc_info=True)
            return 0.0
