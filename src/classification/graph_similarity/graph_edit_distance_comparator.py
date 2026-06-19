import logging
import time

import networkx as nx

from .cost_functions import (
    node_subst_cost,
    node_del_cost,
    node_ins_cost,
    edge_match,
    edge_del_cost,
    edge_ins_cost,
    NodeCost,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _labels(node_data) -> list:
    return sorted(str(x) for x in node_data.get("labels", []))


def build_edit_operations(node_path, edge_path, image_graph, concept_graph) -> list:
    ops = []
    for n1, n2 in node_path:
        if n1 is None:
            ops.append({"kind": "node", "op": "INSERT", "image_ref": None,
                        "concept_ref": str(n2),
                        "cost": node_ins_cost(concept_graph.nodes[n2]),
                        "reason": "concept node unmatched"})
        elif n2 is None:
            ops.append({"kind": "node", "op": "DELETE", "image_ref": str(n1),
                        "concept_ref": None,
                        "cost": node_del_cost(image_graph.nodes[n1]),
                        "reason": "no slot in concept"})
        else:
            cost = node_subst_cost(image_graph.nodes[n1], concept_graph.nodes[n2])
            op = "MATCH" if cost == NodeCost.NO_COST else "SUBSTITUTE"
            ops.append({"kind": "node", "op": op, "image_ref": str(n1),
                        "concept_ref": str(n2), "cost": cost,
                        "reason": f"{_labels(image_graph.nodes[n1])} ↔ "
                                  f"{_labels(concept_graph.nodes[n2])}"})
    for e1, e2 in edge_path:
        if e1 is None:
            ops.append({"kind": "edge", "op": "INSERT", "image_ref": None,
                        "concept_ref": str(e2),
                        "cost": edge_ins_cost(concept_graph.edges[e2]), "reason": ""})
        elif e2 is None:
            ops.append({"kind": "edge", "op": "DELETE", "image_ref": str(e1),
                        "concept_ref": None,
                        "cost": edge_del_cost(image_graph.edges[e1]), "reason": ""})
        elif not edge_match(image_graph.edges[e1], concept_graph.edges[e2]):
            ops.append({"kind": "edge", "op": "SUBSTITUTE", "image_ref": str(e1),
                        "concept_ref": str(e2),
                        "cost": edge_del_cost(image_graph.edges[e1])
                        + edge_ins_cost(concept_graph.edges[e2]), "reason": ""})
        else:
            ops.append({"kind": "edge", "op": "MATCH", "image_ref": str(e1),
                        "concept_ref": str(e2), "cost": 0.0, "reason": ""})
    return ops


class GraphEditDistanceComparator:
    @staticmethod
    def log_edit_operations(paths, image_graph: nx.Graph, concept_graph: nx.Graph):
        if not paths:
            logger.info("No edit paths found")
            return
        node_path, edge_path = paths[0]
        ops = build_edit_operations(node_path, edge_path, image_graph, concept_graph)
        node_total = sum(o["cost"] for o in ops if o["kind"] == "node")
        edge_total = sum(o["cost"] for o in ops if o["kind"] == "edge")
        logger.info("=" * 60)
        logger.info("GRAPH EDIT DISTANCE OPERATIONS")
        for o in ops:
            logger.info(
                f"{o['op']:<12} {str(o['image_ref']):<16} "
                f"{str(o['concept_ref']):<16} {o['cost']:<8} {o['reason']}"
            )
        logger.info(f"TOTAL NODE COST: {node_total}")
        logger.info(f"TOTAL EDGE COST: {edge_total}")
        logger.info(f"TOTAL COST: {node_total + edge_total}")
        logger.info("=" * 60)

    @staticmethod
    def compare_graphs_ged(
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
        concept_name: str,
        ged_timeout: float,
    ) -> float:
        logging.info(
            f"Comparing graph with concept {concept_name} using Graph Edit Distance"
        )

        try:
            best_cost = None
            deadline = time.monotonic() + ged_timeout
            iterations = 0

            for cost in nx.optimize_graph_edit_distance(
                image_graph,
                concept_graph,
                node_subst_cost=node_subst_cost,
                node_del_cost=node_del_cost,
                node_ins_cost=node_ins_cost,
                edge_match=edge_match,
                edge_del_cost=edge_del_cost,
                edge_ins_cost=edge_ins_cost,
            ):
                best_cost = cost
                iterations += 1
                if time.monotonic() >= deadline:
                    logger.info(f"GED timeout after {iterations} iterations")
                    break

            if best_cost is None:
                return 0.0

            logger.info(f"GED: {best_cost} after {iterations} iterations")

            n1 = image_graph.number_of_nodes() + image_graph.number_of_edges()
            n2 = concept_graph.number_of_nodes() + concept_graph.number_of_edges()
            similarity = 1.0 - (best_cost / (best_cost + max(n1, n2, 1)))
            similarity = round(similarity, 4)
            logging.info(
                f"GED: {best_cost}, n1: {n1}, n2: {n2}, similarity: {similarity}"
            )
            return similarity

        except Exception as e:
            logging.error(f"Error calculating GED: {str(e)}", exc_info=True)
            return 0.0
