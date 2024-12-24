import logging
import numpy as np
from neo4j import GraphDatabase
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
import networkx as nx

from common import ClassificationParams
from graph_similarity.structural_comparator_gde import StructuralComparator
from graph_similarity.features.feature_comparison_service import (
    FeatureComparisonService,
)
from graph_similarity.neo4j_to_networkx import Neo4jToNetworkX
from attention.graph_minors import is_minor

logging.basicConfig(level=logging.INFO)


class GraphComparator:
    def __init__(
        self, neo4j_dsn: str, neo4j_user: str, neo4j_pass: str, max_workers: int = 4
    ):
        self.driver = GraphDatabase.driver(neo4j_dsn, auth=(neo4j_user, neo4j_pass))
        self.max_workers = max_workers

    def _get_all_concepts(self, tx: Any) -> List[Dict[str, Any]]:
        concept_query = """
        MATCH (c:Concept)
        RETURN c.id AS concept_id, c.name AS concept_name, c.session_id AS session_id
        """
        return list(tx.run(concept_query))

    def _compare_single_concept_tx(
        self,
        tx: Any,
        image_graph: nx.Graph,
        image_id: str,
        concept: Dict[str, Any],
        classification_params: ClassificationParams,
    ) -> Dict[str, Any]:
        concept_graph = Neo4jToNetworkX.extract_concept_graph(tx, concept["concept_id"])

        # Check if concept_graph is a minor of image_graph using our custom implementation
        if not is_minor(image_graph, concept_graph):
            message = (
                f"Concept {concept['concept_name']} is not a minor of the image graph"
            )
            logging.info(message)
            return {
                "concept_id": concept["concept_id"],
                "concept_name": concept["concept_name"],
                "raw_structural_score": 0.0,
                "raw_feature_score": 0.0,
                "session_id": concept["session_id"],
                "comparison_message": message,
            }

        structural_score = StructuralComparator.compare_graphs_ged(
            image_graph,
            concept_graph,
            concept["concept_name"],
            classification_params.ged_timeout,
        )
        feature_score = FeatureComparisonService().compare_features(
            tx, image_id, concept["concept_id"]
        )

        return {
            "concept_id": concept["concept_id"],
            "concept_name": concept["concept_name"],
            "raw_structural_score": structural_score,
            "raw_feature_score": feature_score,
            "session_id": concept["session_id"],
            "comparison_message": "Graph edit distance calculated successfully",
        }

    def _compare_single_concept(
        self,
        image_graph: nx.Graph,
        image_id: str,
        concept: Dict[str, Any],
        classification_params: ClassificationParams,
    ) -> Dict[str, Any]:
        with self.driver.session() as session:
            return session.execute_read(
                self._compare_single_concept_tx,
                image_graph,
                image_id,
                concept,
                classification_params,
            )

    def compare_graphs(
        self, image_id: str, classification_params: ClassificationParams
    ) -> List[Dict[str, Any]]:
        logging.info(f"Comparing image {image_id} with all concepts")

        with self.driver.session() as session:
            concepts = session.execute_read(self._get_all_concepts)
            image_graph = session.execute_read(
                Neo4jToNetworkX.extract_image_graph, image_id
            )

        results = []
        raw_structural_scores = []
        raw_feature_scores = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_concept = {
                executor.submit(
                    self._compare_single_concept,
                    image_graph,
                    image_id,
                    concept,
                    classification_params,
                ): concept
                for concept in concepts
            }

            for future in future_to_concept:
                try:
                    result = future.result()
                    results.append(result)
                    raw_structural_scores.append(result["raw_structural_score"])
                    raw_feature_scores.append(result["raw_feature_score"])
                except Exception as e:
                    logging.error(f"Error processing concept comparison: {str(e)}")

        preliminary_combined_scores = []
        for result, norm_structural, norm_feature in zip(
            results, raw_structural_scores, raw_feature_scores
        ):
            preliminary_score = (
                classification_params.structural_weight * norm_structural
                + classification_params.feature_weight * norm_feature
            )
            preliminary_combined_scores.append(preliminary_score)

        for result, final_score in zip(results, preliminary_combined_scores):
            result["combined_score"] = float(final_score)
            logging.info(
                f"Scores for concept {result['concept_name']} and image {image_id}:\n"
                f"Structural: raw={result['raw_structural_score']:.4f}, "
                f"Feature: raw={result['raw_feature_score']:.4f}, "
                f"Combined score: {result['combined_score']:.4f}"
            )

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results

    def remove_image_nodes(self, image_id: str) -> None:
        with self.driver.session() as session:
            session.write_transaction(self._remove_image_nodes, image_id)

    def _remove_image_nodes(self, tx: Any, image_id: str) -> None:
        query = """
            MATCH (n)
            WHERE n.image_id = $image_id OR $image_id IN n.samples
            DETACH DELETE n
        """
        tx.run(query, image_id=image_id)
        logging.info(f"Removed all nodes for image_id: {image_id}")
