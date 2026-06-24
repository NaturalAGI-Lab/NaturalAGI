import networkx as nx
import logging
from typing import Tuple, List, Any, Optional
from src.property_handlers import PropertyProcessor
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.critical_point_preprocessor import CriticalPointPreprocessor
from src.logic.synced_traversal_generator import SyncedTraversalGenerator
from src.logic.sequence_aligner import align_monotone_one_to_one
from common.critical_point import CriticalPointType
from common.graph_utils import GraphUtils


class SyncedGraphMinorFinder:
    def __init__(
        self,
        prop_manager: PropertyProcessor,
        similarity_calculator: NodeSimilarityCalculator,
        critical_point_preprocessor: CriticalPointPreprocessor,
        logger=None,
    ):
        self.prop_manager = prop_manager
        self.similarity_calculator = similarity_calculator
        self.logger = logger or logging.getLogger(__name__)
        self.critical_point_preprocessor = critical_point_preprocessor
        self.synced_traversal_generator = SyncedTraversalGenerator(
            critical_point_types={
                CriticalPointType.START_POINT,
                CriticalPointType.END_POINT,
                CriticalPointType.INTERSECTION_POINT,
                CriticalPointType.CORNER_POINT,
            }
        )

    def find_max_common_minor(self, G_c: nx.Graph, G_i: nx.Graph) -> nx.Graph:
        """Finding the maximum common minor of two graphs by traversing through critical points first, generating the skeleton graph

        Args:
            G_c (nx.Graph): concept graph
            G_i (nx.Graph): image graph

        Returns:
            nx.Graph: maximum common minor of the two graphs
        """
        # Preprocess the graphs to align critical points
        # This now returns the modified original graphs, not just critical point graphs
        G_c_processed, G_i_processed = (
            self.critical_point_preprocessor.preprocess_graphs(G_c, G_i)
        )

        self.logger.info(f"Processed concept graph nodes: {len(G_c_processed.nodes)}")
        self.logger.info(f"Processed image graph nodes: {len(G_i_processed.nodes)}")

        # Matrix of the subpaths between intersection points
        # Inside each subpath we have the traversal sequence of two graphs
        # Each inner list represents a continuous path between critical points
        sync_list: List[List[Tuple[Any, Any]]] = (
            self.synced_traversal_generator.generate_synced_traversal(
                G_c_processed, G_i_processed
            )
        )

        self.logger.info(
            "Sync list: \n" + "\n".join([str(subpath) for subpath in sync_list])
        )

        result_graph = nx.Graph()
        for subpath in sync_list:
            self.logger.info(f"Subpath: {subpath}")
            self._reduce_subpath(G_c_processed, G_i_processed, subpath, result_graph)
            self.logger.info("Result graph:")
            for node in result_graph.nodes:
                self.logger.info(f"Node {node}: {result_graph.nodes[node]['labels']}")

        # Return the result graph which is the maximum common minor
        return result_graph

    def _reduce_subpath(
        self,
        G_c: nx.Graph,
        G_i: nx.Graph,
        subpath: List[Tuple[Any, Any]],
        result_graph: nx.Graph,
    ) -> List[Tuple[Any, Any]]:
        """Reducing the subpath to the maximum common minor"""
        processed_paths_c = list()
        processed_paths_i = list()
        for i in range(len(subpath) - 1):
            start_c, end_c = subpath[i][0], subpath[i + 1][0]
            start_i, end_i = subpath[i][1], subpath[i + 1][1]

            # Get all simple paths between the critical points
            paths_c = list(nx.all_simple_paths(G_c, start_c, end_c))
            paths_i = list(nx.all_simple_paths(G_i, start_i, end_i))

            # Remove paths that contain critical points in the middle
            paths_c = [
                path
                for path in paths_c
                if not any(
                    GraphUtils.is_critical_point(G_c.nodes[node]) for node in path[1:-1]
                )
            ]
            paths_i = [
                path
                for path in paths_i
                if not any(
                    GraphUtils.is_critical_point(G_i.nodes[node]) for node in path[1:-1]
                )
            ]

            # Remove already processed paths to avoid reprocessing
            if processed_paths_c and processed_paths_i:
                # Filter out paths that have been processed before
                # Expand to regular loops for better debugging
                filtered_paths_c = []
                for path in paths_c:
                    if (
                        path not in processed_paths_c
                        and path[::-1] not in processed_paths_c
                    ):
                        filtered_paths_c.append(path)
                    else:
                        self.logger.debug(
                            f"Skipping already processed concept path: {path}"
                        )
                paths_c = filtered_paths_c

                filtered_paths_i = []
                for path in paths_i:
                    if (
                        path not in processed_paths_i
                        and path[::-1] not in processed_paths_i
                    ):
                        filtered_paths_i.append(path)
                    else:
                        self.logger.debug(
                            f"Skipping already processed image path: {path}"
                        )
                paths_i = filtered_paths_i
                self.logger.debug(
                    f"After filtering processed paths: {len(paths_c)} concept paths, {len(paths_i)} image paths remain"
                )

            if not paths_c or not paths_i:
                self.logger.warning(
                    f"No path found between critical points: ({start_c},{end_c}) or ({start_i},{end_i})"
                )
                continue

            # Find the best matching paths using similarity calculation
            best_path_c, best_path_i = self._find_best_matching_paths(
                G_c, G_i, paths_c, paths_i
            )

            self.logger.info(
                f"Selected best matching paths: {best_path_c} and {best_path_i}"
            )

            # Add to processed paths to avoid reprocessing
            processed_paths_c.append(best_path_c)
            processed_paths_i.append(best_path_i)

            # Create the reduced path in the result graph
            self._create_reduced_path_in_result(
                result_graph,
                G_c,
                G_i,
                start_c,
                end_c,
                best_path_c,
                start_i,
                end_i,
                best_path_i,
            )

    def _find_best_matching_paths(
        self,
        G_c: nx.Graph,
        G_i: nx.Graph,
        paths_c: List[List[Any]],
        paths_i: List[List[Any]],
    ) -> Tuple[List[Any], List[Any]]:
        """
        Find the best matching paths between two sets of paths using node similarity.

        Args:
            G_c: Concept graph
            G_i: Image graph
            paths_c: List of paths in concept graph
            paths_i: List of paths in image graph

        Returns:
            Tuple of (best_path_c, best_path_i)
        """
        best_score = -1
        best_pair = (paths_c[0], paths_i[0])  # Default to first paths

        self.logger.info(
            f"Finding best matching paths from {len(paths_c)} concept paths and {len(paths_i)} image paths"
        )
        self.logger.info(
            f"Concept paths: " + "\n".join([str(path) for path in paths_c])
        )
        self.logger.info(f"Image paths: " + "\n".join([str(path) for path in paths_i]))

        # Compare each path pair and find the one with highest similarity
        for path_c in paths_c:
            for path_i in paths_i:
                # Calculate similarity matrix between the paths
                similarity_matrix = (
                    self.similarity_calculator.calculate_similarity_matrix(
                        G_c, G_i, path_c, path_i
                    )
                )

                # Calculate overall path similarity score (average of maximum similarities per row)
                path_score = self._calculate_path_similarity_score(similarity_matrix)

                if path_score > best_score:
                    best_score = path_score
                    best_pair = (path_c, path_i)
                    self.logger.debug(
                        f"New best path pair found with score {best_score:.3f}"
                    )

        self.logger.info(f"Best path pair found with score {best_score:.3f}")
        return best_pair

    def _calculate_path_similarity_score(
        self, similarity_matrix: List[List[float]]
    ) -> float:
        """
        Calculate a similarity score between two paths based on their node similarity matrix.
        Uses average of maximum similarities for each node in the first path.

        Args:
            similarity_matrix: Matrix of node similarity scores

        Returns:
            Overall path similarity score
        """
        if not similarity_matrix:
            return 0.0

        # For each node in the first path, find its best match in the second path
        max_similarities = [max(row) if row else 0.0 for row in similarity_matrix]

        # Average the maximum similarities
        if max_similarities:
            return sum(max_similarities) / len(max_similarities)
        return 0.0

    def _create_reduced_path_in_result(
        self,
        result_graph: nx.Graph,
        graph1: nx.Graph,
        graph2: nx.Graph,
        start1: Any,
        end1: Any,
        path1: List[Any],
        start2: Any,
        end2: Any,
        path2: List[Any],
    ) -> None:
        """Merge one segment between two matched critical points into the result.

        Intermediate nodes are aligned by an order-preserving (monotone) 1:1
        matching over the feature-similarity matrix. The shorter sub-path is
        saturated; only the longer sub-path's surplus nodes are dropped. Every
        result node — anchors and intermediates — is keyed by the concept-side
        (graph1) node id so concept identity is stable across incremental merges.
        """
        self.logger.debug(
            f"Creating reduced path in result between ({start1}, {start2}) and ({end1}, {end2})"
        )

        if start1 not in result_graph:
            merged_start_props = self.prop_manager.process_properties(
                {}, graph1.nodes[start1], graph2.nodes[start2]
            )
            result_graph.add_node(start1, **merged_start_props)

        sub_path1 = path1[1:-1]
        sub_path2 = path2[1:-1]

        pairs: List[Tuple[int, int]] = []
        if sub_path1 and sub_path2:
            similarity = self.similarity_calculator.calculate_similarity_matrix(
                graph1, graph2, sub_path1, sub_path2
            )
            types_c = [graph1.nodes[node].get("labels", []) for node in sub_path1]
            types_i = [graph2.nodes[node].get("labels", []) for node in sub_path2]
            pairs = align_monotone_one_to_one(similarity, types_c, types_i)
            self.logger.debug(
                f"Aligned {len(pairs)} intra-segment pairs over a "
                f"{len(sub_path1)}x{len(sub_path2)} matrix"
            )

        prev_node = start1
        for concept_idx, image_idx in pairs:
            concept_node = sub_path1[concept_idx]
            image_node = sub_path2[image_idx]
            if concept_node not in result_graph:
                node_props = self.prop_manager.process_properties(
                    {}, graph1.nodes[concept_node], graph2.nodes[image_node]
                )
                result_graph.add_node(concept_node, **node_props)
                self.logger.debug(f"Added node {concept_node} to result graph")
            else:
                self.logger.warning(
                    f"Node {concept_node} already exists in result graph. Properties not updated."
                )
            if prev_node != concept_node:
                result_graph.add_edge(prev_node, concept_node)
                prev_node = concept_node

        if end1 not in result_graph:
            merged_end_props = self.prop_manager.process_properties(
                {}, graph1.nodes[end1], graph2.nodes[end2]
            )
            result_graph.add_node(end1, **merged_end_props)

        if prev_node != end1:
            result_graph.add_edge(prev_node, end1)
