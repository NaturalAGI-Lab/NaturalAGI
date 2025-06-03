import logging
import networkx as nx

from .cost_functions import (
    node_subst_cost,
    node_del_cost,
    node_ins_cost,
    edge_match,
    edge_del_cost,
    edge_ins_cost,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class GraphEditDistanceComparator:
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
            # Calculate GED with custom cost functions
            ged = nx.graph_edit_distance(
                image_graph,
                concept_graph,
                node_subst_cost=node_subst_cost,
                node_del_cost=node_del_cost,
                node_ins_cost=node_ins_cost,
                edge_match=edge_match,
                edge_del_cost=edge_del_cost,
                edge_ins_cost=edge_ins_cost,
                timeout=ged_timeout,
            )

            logger.info(f"GED: {ged}")

            if ged is None:  # Timeout occurred
                return 0.0

            # Convert GED to similarity score (inverse and normalize)
            max_possible_ged = max(len(image_graph) + len(concept_graph), 1)
            similarity = 1.0 - (ged / max_possible_ged)
            similarity = round(similarity, 2)
            logging.info(
                f"GED: {ged}, max_possible_ged: {max_possible_ged}, similarity: {similarity}"
            )
            return max(0.0, min(1.0, similarity))  # Ensure score is between 0 and 1

        except Exception as e:
            logging.error(f"Error calculating GED: {str(e)}", exc_info=True)
            return 0.0
