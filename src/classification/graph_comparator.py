import logging
import numpy as np
from neo4j import GraphDatabase
from typing import List, Dict, Any
from graph_similarity.structural_comparator_gde import StructuralComparator
from graph_similarity.features.feature_comparison_service import (
    FeatureComparisonService,
)
from graph_similarity.score_combiner import ScoreCombiner

logging.basicConfig(level=logging.INFO)


class GraphComparator:
    def __init__(self, neo4j_dsn: str, neo4j_user: str, neo4j_pass: str, feature_weight: float, structural_weight: float, ged_timeout: float):
        self.driver = GraphDatabase.driver(neo4j_dsn, auth=(neo4j_user, neo4j_pass))
        self.feature_weight = feature_weight
        self.structural_weight = structural_weight
        self.ged_timeout = ged_timeout

    def compare_graphs(self, image_id: str) -> List[Dict[str, Any]]:
        logging.info(f"Comparing image {image_id} with all concepts")
        with self.driver.session() as session:
            return session.read_transaction(self._compare_with_all_concepts, image_id)

    def _compare_with_all_concepts(self, tx, image_id: str) -> List[Dict[str, Any]]:
        # First, get all concept IDs
        concept_query = """
        MATCH (c:Concept)
        RETURN c.id AS concept_id, c.name AS concept_name, c.session_id AS session_id
        """
        concepts = list(tx.run(concept_query))

        # Collect raw similarity scores
        results = []
        raw_structural_scores = []
        raw_feature_scores = []

        for concept in concepts:
            # structural_score = StructuralComparator.compare_graphs_wl(
            #     tx, image_id, concept["concept_id"], concept["concept_name"]
            # )
            structural_score = StructuralComparator.compare_graphs_ged(
                tx, image_id, concept["concept_id"], concept["concept_name"], self.ged_timeout
            )
            feature_score = FeatureComparisonService().compare_features(
                tx, image_id, concept["concept_id"]
            )

            results.append(
                {
                    "concept_id": concept["concept_id"],
                    "concept_name": concept["concept_name"],
                    "raw_structural_score": structural_score,
                    "raw_feature_score": feature_score,
                    "session_id": concept["session_id"],
                }
            )
            raw_structural_scores.append(structural_score)
            raw_feature_scores.append(feature_score)

        # Apply softmax normalization to structural scores
        # normalized_structural_scores = ScoreCombiner.combine(raw_structural_scores)
        # normalized_feature_scores = ScoreCombiner.combine(raw_feature_scores)

        # logging.info(f"Normalized structural scores: {normalized_structural_scores}")
        # logging.info(f"Normalized feature scores: {normalized_feature_scores}")

        # First, calculate preliminary combined scores
        preliminary_combined_scores = []

        for result, norm_structural, norm_feature in zip(
            results, raw_structural_scores, raw_feature_scores
        ):
            # Calculate preliminary combined score (weighted average)
            preliminary_score = self.structural_weight * norm_structural + self.feature_weight * norm_feature
            preliminary_combined_scores.append(preliminary_score)

        # Apply final softmax normalization to all combined scores
        final_combined_scores = ScoreCombiner.combine(preliminary_combined_scores)

        # Update results with final normalized scores
        for result, final_score in zip(results, final_combined_scores):
            result["combined_score"] = float(final_score)

            logging.info(
                f"Scores for concept {result['concept_name']} and image {image_id}:\n"
                f"Structural: raw={result['raw_structural_score']:.4f}, "
                f"Feature: raw={result['raw_feature_score']:.4f}, "
                f"Combined score: {result['combined_score']:.4f}"
            )

        # Sort results by combined score in descending order
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results

    def remove_image_nodes(self, image_id: str) -> None:
        with self.driver.session() as session:
            session.write_transaction(self._remove_image_nodes, image_id)

    def _remove_image_nodes(self, tx, image_id: str) -> None:
        query = """
            MATCH (n)
            WHERE n.image_id = $image_id OR $image_id IN n.samples
            DETACH DELETE n
        """
        tx.run(query, image_id=image_id)
        logging.info(f"Removed all nodes for image_id: {image_id}")
