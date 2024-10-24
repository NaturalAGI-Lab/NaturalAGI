import logging
import numpy as np
from neo4j import GraphDatabase
from typing import List, Dict, Any
from graph_similarity.structural_comparator import StructuralComparator
from graph_similarity.features.feature_comparison_service import FeatureComparisonService
from graph_similarity.score_combiner import ScoreCombiner

logging.basicConfig(level=logging.INFO)


class GraphComparator:
    def __init__(self, neo4j_dsn: str, neo4j_user: str, neo4j_pass: str):
        self.driver = GraphDatabase.driver(neo4j_dsn, auth=(neo4j_user, neo4j_pass))

    def compare_graphs(self, image_id: str) -> List[Dict[str, Any]]:
        logging.info(f"Comparing image {image_id} with all concepts")
        with self.driver.session() as session:
            return session.read_transaction(self._compare_with_all_concepts, image_id)

    @staticmethod
    def _compare_with_all_concepts(tx, image_id: str) -> List[Dict[str, Any]]:
        # First, get all concept IDs
        concept_query = """
        MATCH (c:Concept)
        RETURN c.id AS concept_id, c.name AS concept_name
        """
        concepts = list(tx.run(concept_query))

        # Collect raw similarity scores
        results = []
        raw_structural_scores = []
        raw_feature_scores = []
        
        for concept in concepts:
            structural_score = StructuralComparator.compare_graphs(
                tx, image_id, concept["concept_id"]
            )
            feature_score = FeatureComparisonService().compare_features(
                tx, image_id, concept["concept_id"]
            )
            
            results.append({
                "concept_id": concept["concept_id"],
                "concept_name": concept["concept_name"],
                "raw_structural_score": structural_score,
                "raw_feature_score": feature_score
            })
            raw_structural_scores.append(structural_score)
            raw_feature_scores.append(feature_score)

        # First, calculate preliminary combined scores
        preliminary_combined_scores = []
        
        for result, norm_structural, norm_feature in zip(
            results, raw_structural_scores, raw_feature_scores
        ):  
            # Calculate preliminary combined score (weighted average)
            preliminary_score = norm_structural + norm_feature
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

    @staticmethod
    def _remove_image_nodes(tx, image_id: str) -> None:
        query = """
            MATCH (n)
            WHERE n.image_id = $image_id OR $image_id IN n.samples
            DETACH DELETE n
        """
        tx.run(query, image_id=image_id)
        logging.info(f"Removed all nodes for image_id: {image_id}")
