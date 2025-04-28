# import logging
# import numpy as np
# from neo4j import GraphDatabase
# from typing import List, Dict, Any, Tuple
# from concurrent.futures import ThreadPoolExecutor
# import networkx as nx

# from common.params import ClassificationParams
# from graph_similarity.structural_comparator_gde import StructuralComparator
# from graph_similarity.features.feature_comparison_service import (
#     FeatureComparisonService,
# )
# from graph_similarity.neo4j_to_networkx import Neo4jToNetworkX
# from concept_creator.maximum_common_subgraph import MaximumCommonMinorGraph

# logging.basicConfig(level=logging.INFO)


# class GraphComparator:
#     def __init__(
#         self,
#         neo4j_dsn: str,
#         neo4j_user: str,
#         neo4j_pass: str,
#         max_workers: int = 4,
#         use_multithreading: bool = False,
#     ):
#         self.neo4j_dsn = neo4j_dsn
#         self.neo4j_user = neo4j_user
#         self.neo4j_pass = neo4j_pass
#         self.driver = GraphDatabase.driver(
#             neo4j_dsn, auth=(neo4j_user, neo4j_pass), max_connection_lifetime=200
#         )
#         self.max_workers = max_workers
#         self.use_multithreading = use_multithreading
#         self.mcm_finder = MaximumCommonMinorGraph()

#     def close(self):
#         self.driver.close()

#     def _get_all_concepts(self, tx: Any) -> List[str]:
#         concept_query = """
#         MATCH (c)
#         WITH DISTINCT c.concept_id AS concept_id
#         RETURN concept_id
#         """
#         return [record["concept_id"] for record in tx.run(concept_query) if record["concept_id"] is not None]

#     def _compare_single_concept_tx(
#         self,
#         tx: Any,
#         image_graph: nx.Graph,
#         concept_id: str,
#     ) -> Dict[str, Any]:
#         concept_graph = Neo4jToNetworkX.extract_concept_graph(tx, concept_id)

#         # Calculate complexity metrics
#         concept_complexity = len(concept_graph.nodes) + len(concept_graph.edges)

#         # Instead of just checking if the concept is a minor of the image graph,
#         # use the Maximum Common Minor Graph approach to get a more detailed comparison
#         mcm_results = self.mcm_finder.find_max_common_minor_with_start_points(
#             concept_graph, image_graph
#         )

#         mcm, concept_to_mcm, image_to_mcm, applied_contractions = mcm_results

#         # Calculate structural score based on the size of the common minor graph
#         if len(concept_graph.nodes()) == 0:
#             structural_similarity = 0.0
#         else:
#             # Calculate how much of the concept graph is found in the maximum common minor
#             structural_similarity = len(concept_to_mcm) / len(concept_graph.nodes())

#         # If less than a minimum threshold of the concept is found, consider it not a match
#         min_structural_similarity = 0.5

#         if structural_similarity < min_structural_similarity:
#             message = f"Concept {concept_id} has insufficient structural similarity ({structural_similarity:.2f}) with the image graph"
#             logging.info(message)
#             return {
#                 "concept_id": concept_id,
#                 "concept_name": concept_id,
#                 "session_id": concept_id,
#                 "raw_structural_score": structural_similarity,
#                 "raw_feature_score": 0.0,
#                 "comparison_message": message,
#                 "concept_complexity": concept_complexity,
#             }

#         return {
#             "concept_id": concept_id,
#             "concept_name": concept_id,
#             "session_id": concept_id,
#             "raw_structural_score": structural_similarity,
#             "mcm_size": len(mcm.nodes()),
#             "concept_size": len(concept_graph.nodes()),
#             "image_size": len(image_graph.nodes()),
#             "applied_contractions": len(applied_contractions),
#             "comparison_message": f"Maximum Common Minor Graph found with {len(concept_to_mcm)}/{len(concept_graph.nodes())} concept nodes matched ({structural_similarity:.2%}) and {len(applied_contractions)} contractions applied",
#             "concept_complexity": concept_complexity,
#         }

#     def _compare_single_concept(
#         self,
#         image_graph: nx.Graph,
#         concept_id: str,
#     ) -> Dict[str, Any]:
#         with self.driver.session() as session:
#             return session.execute_read(
#                 self._compare_single_concept_tx,
#                 image_graph,
#                 concept_id,
#             )

#     def compare_graphs(
#         self, image_id: str, classification_params: ClassificationParams
#     ) -> List[Dict[str, Any]]:
#         logging.info(f"Comparing image {image_id} with all concepts")

#         with self.driver.session() as session:
#             concepts = session.execute_read(self._get_all_concepts)
#             image_graph = session.execute_read(
#                 Neo4jToNetworkX.extract_image_graph, image_id
#             )

#         results = []
#         raw_structural_scores = []

#         if self.use_multithreading:
#             with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
#                 future_to_concept = {
#                     executor.submit(
#                         self._compare_single_concept,
#                         image_graph,
#                         concept_id,
#                     ): concept_id
#                     for concept_id in concepts
#                 }

#                 for future in future_to_concept:
#                     try:
#                         result = future.result(timeout=30)
#                         if not (
#                             result["raw_structural_score"] > 0.0
#                             or result["raw_feature_score"] > 0.0
#                         ):
#                             continue
#                         results.append(result)
#                         raw_structural_scores.append(result["raw_structural_score"])
#                     except Exception as e:
#                         logging.error(f"Error comparing graphs: {str(e)}")
#         else:
#             # Sequential processing
#             for concept in concepts:
#                 try:
#                     result = self._compare_single_concept(image_graph, concept)
#                     results.append(result)
#                     raw_structural_scores.append(result["raw_structural_score"])
#                 except Exception as e:
#                     logging.error(f"Error comparing graphs: {str(e)}")

#         preliminary_combined_scores = []
#         for result in results:
#             norm_structural = result["raw_structural_score"]
#             preliminary_combined_scores.append(norm_structural)

#         for result in results:
#             result["combined_score"] = float(result["raw_structural_score"])
#             logging.info(
#                 f"Scores for concept {result['concept_id']} and image {image_id}:\n"
#                 f"Structural: raw={result['raw_structural_score']:.4f}, "
#                 f"Combined score: {result['combined_score']:.4f}, "
#                 f"Complexity: {result.get('concept_complexity', 0)}"
#             )

#         # Sort by combined score first, then by complexity if scores are equal
#         results.sort(
#             key=lambda x: (x["combined_score"], x.get("concept_complexity", 0)),
#             reverse=True,
#         )
#         return results

#     def remove_image_nodes(self, image_id: str) -> None:
#         with self.driver.session() as session:
#             session.write_transaction(self._remove_image_nodes, image_id)

#     def _remove_image_nodes(self, tx: Any, image_id: str) -> None:
#         query = """
#             MATCH (n)
#             WHERE n.image_id = $image_id OR $image_id IN n.samples
#             DETACH DELETE n
#         """
#         tx.run(query, image_id=image_id)
#         logging.info(f"Removed all nodes for image_id: {image_id}")
