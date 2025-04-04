import logging
import networkx as nx
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor

from graph_similarity.neo4j_to_networkx import Neo4jToNetworkX
from property_handlers import PropertyMatcherManager
from critical_point_preprocessor import CriticalPointPreprocessor
from node_similarity_calculator import NodeSimilarityCalculator

logging.basicConfig(level=logging.DEBUG)


class ConceptMinorClassifier:
    """
    Specialized classifier that checks if a concept is a minor of an image graph
    without removing properties from concept nodes during matching.

    This classifier starts from StartPoint nodes and tries to find the graph minor
    for the image. If the image can be presented as a concept graph without removing
    properties from the nodes of the concept, it's considered a minor and a match.
    """

    def __init__(
        self,
        neo4j_dsn: str,
        neo4j_user: str,
        neo4j_pass: str,
        max_workers: int = 4,
        use_multithreading: bool = False,
        min_structural_score: float = 0.1,
        activation_weights: Dict[str, float] = None,
        complexity_factor: float = 0.9,
        early_stopping_threshold: float = 0.85,
    ):
        self.neo4j_dsn = neo4j_dsn
        self.neo4j_user = neo4j_user
        self.neo4j_pass = neo4j_pass
        self.driver = GraphDatabase.driver(
            neo4j_dsn, auth=(neo4j_user, neo4j_pass), max_connection_lifetime=200
        )
        self.max_workers = max_workers
        self.use_multithreading = use_multithreading
        self.min_structural_score = min_structural_score
        self.activation_weights = activation_weights or {
            "complexity": 0.6,
            "structural": 0.3,
            "specificity": 0.1,
        }
        self.complexity_factor = complexity_factor
        self.early_stopping_threshold = early_stopping_threshold
        self.property_matcher = PropertyMatcherManager()

        # Add preprocessor and similarity calculator for alignment with GraphMinorFinder
        self.preprocessor = CriticalPointPreprocessor()
        self.similarity_calculator = NodeSimilarityCalculator()

    def close(self):
        self.driver.close()

    def _get_all_concepts(self, tx: Any) -> List[str]:
        concept_query = """
        MATCH (c)
        WITH DISTINCT c.concept_id AS concept_id
        RETURN concept_id
        """
        return [
            record["concept_id"]
            for record in tx.run(concept_query)
            if record["concept_id"] is not None
        ]

    def _check_concept_minor_tx(
        self,
        tx: Any,
        image_graph: nx.Graph,
        concept_id: str,
    ) -> Dict[str, Any]:
        logging.info(f"Checking concept {concept_id} for minor of image")
        # Get concept graph
        concept_graph = Neo4jToNetworkX.extract_concept_graph(tx, concept_id)

        # Quick size-based early rejection
        if len(concept_graph.nodes) > len(image_graph.nodes):
            logging.info(
                f"Concept {concept_id} is too large to be a minor of the image"
            )
            return self._create_no_match_result(
                concept_id, len(concept_graph.nodes) + len(concept_graph.edges)
            )

        concept_complexity = len(concept_graph.nodes) + len(concept_graph.edges)

        # Apply asymmetric preprocessing - concept is treated as template, image can be reduced
        try:
            logging.info(
                f"Asymmetrically preprocessing concept and image graphs (only image can be reduced)"
            )
            preprocessed_concept, preprocessed_image = (
                self.preprocessor.preprocess_graphs_asymmetric(
                    concept_graph, image_graph
                )
            )

            # Check if preprocessing failed (asymmetric constraint violated)
            if preprocessed_concept is None or preprocessed_image is None:
                logging.warning(
                    f"Asymmetric preprocessing failed - concept requires more critical points than image provides"
                )
                return self._create_no_match_result(
                    concept_id,
                    concept_complexity,
                    comparison_message=f"Concept requires more critical points of higher types than image provides",
                )

            logging.info(
                f"Asymmetric preprocessing complete. Concept: {len(preprocessed_concept.nodes)} nodes, Image: {len(preprocessed_image.nodes)} nodes"
            )
        except Exception as e:
            logging.warning(f"Preprocessing failed for concept {concept_id}: {str(e)}")
            return self._create_no_match_result(
                concept_id,
                concept_complexity,
                comparison_message=f"Preprocessing failed: {str(e)}",
            )

        # Continue with the preprocessed graphs for all subsequent operations
        concept_graph = preprocessed_concept
        image_graph = preprocessed_image

        # Calculate similarity using critical point-based approach
        similarity_results = self._calculate_critical_point_similarity(
            concept_graph, image_graph
        )

        # Create appropriate result based on similarity calculation
        match_type = similarity_results["match_type"]
        overall_similarity = similarity_results["overall_similarity"]

        # Create appropriate result based on match type
        if match_type == "complete_match":
            return self._create_complete_match_result(
                concept_id,
                concept_complexity,
                similarity_results[
                    "mapped_cps"
                ],  # Use mapped critical points as mapping size
                len(concept_graph.nodes),
                len(image_graph.nodes),
                0,  # No contractions in this approach
                comparison_message=(
                    f"Complete match for concept {concept_id} with similarity {overall_similarity:.2f}. "
                    f"Matched {similarity_results['mapped_cps']}/{similarity_results['total_cps']} critical points and "
                    f"{similarity_results['mapped_paths']}/{similarity_results['total_paths']} paths. "
                    f"Quality score: {similarity_results['quality_score']:.2f}"
                ),
                similarity_details=similarity_results,
            )
        elif match_type == "good_match":
            return self._create_good_match_result(
                concept_id,
                concept_complexity,
                similarity_results["overall_similarity"],
                similarity_results["mapped_cps"],
                len(concept_graph.nodes),
                len(image_graph.nodes),
                comparison_message=(
                    f"Good match for concept {concept_id} with similarity {overall_similarity:.2f}. "
                    f"Matched {similarity_results['mapped_cps']}/{similarity_results['total_cps']} critical points and "
                    f"{similarity_results['mapped_paths']}/{similarity_results['total_paths']} paths. "
                    f"Quality score: {similarity_results['quality_score']:.2f}"
                ),
                similarity_details=similarity_results,
            )
        elif match_type == "partial_match":
            return self._create_partial_match_result(
                concept_id,
                concept_complexity,
                overall_similarity,
                similarity_results["mapped_cps"],
                len(concept_graph.nodes),
                len(image_graph.nodes),
                0,  # No contractions in this approach
                comparison_message=(
                    f"Partial match for concept {concept_id} with similarity {overall_similarity:.2f}. "
                    f"Matched {similarity_results['mapped_cps']}/{similarity_results['total_cps']} critical points and "
                    f"{similarity_results['mapped_paths']}/{similarity_results['total_paths']} paths. "
                    f"Quality score: {similarity_results['quality_score']:.2f}"
                ),
                similarity_details=similarity_results,
            )
        else:
            return self._create_no_match_result(
                concept_id,
                concept_complexity,
                comparison_message=(
                    f"No significant match for concept {concept_id}. Similarity score: {overall_similarity:.2f}, "
                    f"Quality score: {similarity_results.get('quality_score', 0):.2f}"
                ),
            )

    def _create_no_match_result(
        self, concept_id: str, concept_complexity: int, comparison_message: str = None
    ) -> Dict[str, Any]:
        return {
            "concept_id": concept_id,
            "concept_name": concept_id,
            "session_id": concept_id,
            "raw_structural_score": 0.0,
            "is_minor": False,
            "concept_complexity": concept_complexity,
            "comparison_message": comparison_message
            or f"No match found for concept {concept_id}",
        }

    def _create_complete_match_result(
        self,
        concept_id: str,
        concept_complexity: int,
        mapping_size: int,
        concept_size: int,
        image_size: int,
        contractions_count: int = 0,
        comparison_message: str = None,
        similarity_details: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        return {
            "concept_id": concept_id,
            "concept_name": concept_id,
            "session_id": concept_id,
            "raw_structural_score": 1.0,
            "is_minor": True,
            "mapping_size": mapping_size,
            "concept_size": concept_size,
            "image_size": image_size,
            "contractions_count": contractions_count,
            "comparison_message": comparison_message,
            "concept_complexity": concept_complexity,
            "similarity_details": similarity_details,
        }

    def _create_partial_match_result(
        self,
        concept_id: str,
        concept_complexity: int,
        partial_similarity: float,
        mapping_size: int,
        concept_size: int,
        image_size: int,
        contractions_count: int = 0,
        comparison_message: str = None,
        similarity_details: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        return {
            "concept_id": concept_id,
            "concept_name": concept_id,
            "session_id": concept_id,
            "raw_structural_score": partial_similarity,
            "is_minor": False,
            "mapping_size": mapping_size,
            "concept_size": concept_size,
            "image_size": image_size,
            "contractions_count": contractions_count,
            "comparison_message": comparison_message,
            "concept_complexity": concept_complexity,
            "similarity_details": similarity_details,
        }

    def _create_good_match_result(
        self,
        concept_id: str,
        concept_complexity: int,
        overall_similarity: float,
        mapping_size: int,
        concept_size: int,
        image_size: int,
        comparison_message: str = None,
        similarity_details: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        return {
            "concept_id": concept_id,
            "concept_name": concept_id,
            "session_id": concept_id,
            "raw_structural_score": 0.75,
            "is_minor": False,
            "mapping_size": mapping_size,
            "concept_size": concept_size,
            "image_size": image_size,
            "contractions_count": 0,
            "comparison_message": comparison_message,
            "concept_complexity": concept_complexity,
            "similarity_details": similarity_details,
        }

    def _check_single_concept(
        self,
        image_graph: nx.Graph,
        concept_id: str,
    ) -> Dict[str, Any]:
        with self.driver.session() as session:
            return session.execute_read(
                self._check_concept_minor_tx,
                image_graph,
                concept_id,
            )

    def classify(
        self,
        image_id: str,
    ) -> List[Dict[str, Any]]:
        logging.info(f"Classifying image {image_id} using concept minor approach")

        with self.driver.session() as session:
            concepts = session.execute_read(self._get_all_concepts)
            image_graph = session.execute_read(
                Neo4jToNetworkX.extract_image_graph, image_id
            )

        results = []

        if self.use_multithreading:
            results = self._classify_with_multithreading(image_graph, concepts)
        else:
            results = self._classify_sequentially(image_graph, concepts)

        # Process and sort results
        return self._process_and_sort_results(results, image_id)

    def _classify_with_multithreading(
        self,
        image_graph: nx.Graph,
        concepts: List[str],
    ) -> List[Dict[str, Any]]:
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._check_single_concept,
                    image_graph,
                    concept_id,
                ): concept_id
                for concept_id in concepts
            }

            for future in futures:
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    logging.error(f"Error checking concept minor: {str(e)}")

        return results

    def _classify_sequentially(
        self,
        image_graph: nx.Graph,
        concepts: List[str],
    ) -> List[Dict[str, Any]]:
        results = []
        for concept in concepts:
            try:
                result = self._check_single_concept(
                    image_graph,
                    concept,
                )
                results.append(result)
            except Exception as e:
                logging.error(f"Error checking concept minor: {str(e)}")

        return results

    def _process_and_sort_results(
        self, results: List[Dict[str, Any]], image_id: str
    ) -> List[Dict[str, Any]]:
        if not results:
            return []

        # Pre-filter results that don't meet our structural threshold
        filtered_results = []
        for result in results:
            # Complete matches are always included
            if result.get("is_minor", False):
                filtered_results.append(result)
            # Good matches are similar to complete matches but not exact minors
            elif result.get("similarity_details", {}).get("match_type") == "good_match":
                filtered_results.append(result)
            # For partial matches, apply structural score threshold
            elif (
                result.get("raw_structural_score", 0) >= self.min_structural_score
                or result.get("similarity_details", {}).get("overall_similarity", 0)
                >= self.min_structural_score
            ):
                filtered_results.append(result)

        if not filtered_results:
            return []

        # Calculate complexity metrics for normalization
        max_complexity = max(r.get("concept_complexity", 0) for r in filtered_results)
        min_complexity = min(r.get("concept_complexity", 0) for r in filtered_results)
        complexity_range = max(1, max_complexity - min_complexity)

        # Calculate specificity (inverse of how many nodes are in the image graph compared to concept)
        for result in filtered_results:
            concept_size = result.get("concept_size", 1)
            image_size = result.get("image_size", 1)
            result["specificity"] = concept_size / image_size

        # Find range for specificity normalization
        max_specificity = max(r.get("specificity", 0) for r in filtered_results)
        min_specificity = min(r.get("specificity", 0) for r in filtered_results)
        specificity_range = max(0.01, max_specificity - min_specificity)

        # Calculate combined scores based on the refined similarity metrics
        for result in filtered_results:
            # Normalize complexity
            normalized_complexity = (
                result.get("concept_complexity", 0) - min_complexity
            ) / complexity_range

            # Specificity score - higher when concept is more specific to the image
            normalized_specificity = (
                result.get("specificity", 0) - min_specificity
            ) / specificity_range

            # Store normalized values for debugging
            result["normalized_complexity"] = normalized_complexity
            result["normalized_specificity"] = normalized_specificity

            # Use the detailed similarity metrics if available
            similarity_details = result.get("similarity_details", {})

            if similarity_details:
                # Get key metrics from similarity details
                match_type = similarity_details.get("match_type", "no_match")
                overall_similarity = similarity_details.get("overall_similarity", 0.0)
                quality_score = similarity_details.get("quality_score", 0.0)
                coverage_score = similarity_details.get("coverage_score", 0.0)

                # Create a more sophisticated combined score that balances:
                # - overall_similarity (coverage + quality weighted)
                # - complexity (as a tiebreaker)
                # - specificity (to prioritize more specific concepts)

                # Adjust match type multiplier - boost complete matches
                match_type_multiplier = 1.0
                if match_type == "complete_match":
                    match_type_multiplier = 1.1  # 10% boost
                elif match_type == "good_match":
                    match_type_multiplier = 1.05  # 5% boost

                # Build combined score from multiple factors
                base_score = overall_similarity
                specificity_boost = (
                    0.02 * normalized_specificity
                )  # Small specificity boost
                complexity_boost = (
                    0.01 * normalized_complexity
                )  # Tiny complexity tiebreaker

                # Calculate final combined score
                result["combined_score"] = match_type_multiplier * (
                    base_score + specificity_boost + complexity_boost
                )

                # Also store individual components for reference
                result["match_quality"] = quality_score
                result["match_coverage"] = coverage_score

            else:
                # Fallback to the basic scoring approach
                structural_score = result.get("raw_structural_score", 0)
                result["combined_score"] = structural_score + (
                    0.0001 * normalized_complexity
                )
                result["match_quality"] = structural_score
                result["match_coverage"] = structural_score

            # Set activation level equal to combined score
            result["activation_level"] = result["combined_score"]

            # Add match type for sorting/filtering
            result["match_type"] = similarity_details.get(
                "match_type",
                (
                    "partial_match"
                    if result.get("raw_structural_score", 0) > 0
                    else "no_match"
                ),
            )

            # Log scores for debugging
            logging.info(
                f"Scores for concept {result['concept_id']} and image {image_id}:\n"
                f"Match type: {result.get('match_type', 'unknown')}, "
                f"Raw structural: {result.get('raw_structural_score', 0):.4f}, "
                f"Quality: {result.get('match_quality', 0):.4f}, "
                f"Coverage: {result.get('match_coverage', 0):.4f}, "
                f"Combined: {result['combined_score']:.4f}"
            )

        # Sort by combined score (which now includes quality, coverage, match type)
        filtered_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

        return filtered_results

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

    def _find_paths_to_next_critical(
        self,
        graph: nx.Graph,
        start_node: Any,
        critical_points: Dict[str, List[Any]],
    ) -> List[Tuple[Any, List[Any]]]:
        """
        Finds all simple paths from start_node to any other critical point,
        such that the path does not contain any *other* critical points as intermediate nodes.

        Args:
            graph: The graph to search within
            start_node: The critical point node ID to start from
            critical_points: Dictionary mapping critical point types to lists of node IDs

        Returns:
            A list of tuples, where each tuple contains (next_critical_point_id, path_nodes_list).
            Returns all such valid paths found.
        """
        logging.debug(f"Finding paths from critical node {start_node}")
        all_critical = {node for points in critical_points.values() for node in points}
        target_critical = all_critical - {start_node}

        found_paths = []

        # Use BFS approach to find all paths
        import collections

        stack = collections.deque(
            [(start_node, [start_node])]
        )  # (current_node, path_list)

        while stack:
            current_node, path = stack.pop()  # DFS uses pop()

            # Explore neighbors
            for neighbor in graph.neighbors(current_node):
                # Avoid cycles by checking if neighbor is already in the current path
                if neighbor not in path:
                    new_path = path + [neighbor]

                    # Check if neighbor is a target critical point
                    if neighbor in target_critical:
                        # Found a valid path ending at a critical point
                        logging.debug(
                            f"Found path to critical point {neighbor}: {new_path}"
                        )
                        found_paths.append((neighbor, new_path))
                        # Do not continue exploring further along this path branch from the target
                    else:
                        # Neighbor is not a critical point, continue DFS
                        stack.append((neighbor, new_path))

        # Post-processing: Filter paths that contain intermediate critical points
        valid_paths = []
        for end_node, path in found_paths:
            is_valid = True
            # Check intermediate nodes (excluding start and end)
            for node in path[1:-1]:
                if node in all_critical:  # Found an intermediate critical point
                    is_valid = False
                    logging.debug(
                        f"Filtering out path {path} due to intermediate critical point {node}"
                    )
                    break
            if is_valid:
                valid_paths.append((end_node, path))

        logging.debug(
            f"Found {len(valid_paths)} valid simple paths from {start_node} to other critical points"
        )
        return valid_paths

    def _calculate_path_similarity(
        self, graph1: nx.Graph, graph2: nx.Graph, path1: List[Any], path2: List[Any]
    ) -> float:
        """
        Calculates similarity between two paths based on:
        1. Relative length (closer is better)
        2. Node type compatibility

        Args:
            graph1: First graph (concept graph)
            graph2: Second graph (image graph)
            path1: Path in first graph (concept path)
            path2: Path in second graph (image path)

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Check if concept path is longer than image path
        len1, len2 = len(path1), len(path2)
        if len1 > len2:
            return (
                0.0  # Fail classification when concept path is longer than image path
            )

        # Length similarity component (1.0 if equal length, decreasing as difference increases)
        length_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 1.0

        # Node compatibility component
        # Sample key positions in each path and check compatibility
        # Take start, end, and up to 3 intermediate points
        compatible_nodes = 0
        comparisons = 0

        # Always compare start and end
        positions = [0, -1]

        # Add middle point if paths are long enough
        if len1 > 2 and len2 > 2:
            positions.append(len1 // 2)

        # Add quarter and three-quarter points for longer paths
        if len1 > 4 and len2 > 4:
            positions.extend([len1 // 4, 3 * len1 // 4])

        for pos in positions:
            if pos >= len1 or (pos < 0 and abs(pos) > len1):
                continue

            idx1 = pos
            # Map position proportionally to path2
            if pos >= 0:
                idx2 = min(int(pos * len2 / len1), len2 - 1)
            else:
                idx2 = -min(abs(pos), len2)

            node1 = path1[idx1]
            node2 = path2[idx2]

            # Use the similarity calculator for more accurate node comparison
            similarity = self.similarity_calculator.calculate_node_similarity(
                graph1, graph2, node1, node2
            )
            if similarity > 0.3:  # Threshold for considering nodes compatible
                compatible_nodes += 1
            comparisons += 1

        node_compatibility = compatible_nodes / comparisons if comparisons > 0 else 0.0

        # Combine scores (weight length similarity less than node compatibility)
        similarity = 0.3 * length_ratio + 0.7 * node_compatibility

        return similarity

    def _find_alternative_image_path(
        self,
        image_graph: nx.Graph,
        start_node: Any,
        end_node: Any,
        max_length: int,
        current_path: List[Any] = None,
    ) -> List[Any]:
        """
        Finds an alternative path in the image graph between the start and end nodes,
        with length less than or equal to max_length.

        Args:
            image_graph: The image graph
            start_node: Starting node
            end_node: Ending node
            max_length: Maximum allowed path length
            current_path: Currently considered path (for validation)

        Returns:
            A path with length <= max_length, or None if no such path exists
        """
        # Try to find alternative paths using networkx all_simple_paths
        # but limit the path length to max_length
        try:
            # We add 1 to max_length since we're counting nodes, not edges
            # And capping the cutoff to avoid excessive computation
            cutoff = min(max_length, 20)

            # Find all paths from start to end with length <= max_length
            all_paths = list(
                nx.all_simple_paths(
                    image_graph, source=start_node, target=end_node, cutoff=cutoff
                )
            )

            # Filter paths by length and take the shortest one
            valid_paths = [p for p in all_paths if len(p) <= max_length]

            if valid_paths:
                # Sort by length (ascending)
                valid_paths.sort(key=len)
                logging.debug(
                    f"Found alternative path with length {len(valid_paths[0])} (vs max {max_length})"
                )
                return valid_paths[0]

            logging.debug(f"No alternative path found with length <= {max_length}")
            return None
        except Exception as e:
            logging.warning(f"Error finding alternative path: {str(e)}")
            return None

    def _normalize_path_tuple(self, path_tuple: Tuple[Any, ...]) -> Tuple[Any, ...]:
        """
        Normalizes a path tuple to a canonical form that is the same regardless of direction.
        This ensures that paths like (A->B->C) and (C->B->A) are treated as the same connection.

        Args:
            path_tuple: Original path tuple

        Returns:
            Normalized path tuple
        """
        # If the first node has a smaller ID than the last node, keep as is
        # Otherwise, reverse the path
        if not path_tuple:
            return path_tuple

        first_node, last_node = path_tuple[0], path_tuple[-1]
        # Convert to strings for consistent comparison if nodes are different types
        first_str = str(first_node)
        last_str = str(last_node)

        if first_str <= last_str:
            return path_tuple
        else:
            return tuple(reversed(path_tuple))

    def _find_optimal_path_matches(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        paths_c: List[Tuple[Any, List[Any]]],
        paths_i: List[Tuple[Any, List[Any]]],
        critical_point_mapping: Dict[Any, Any],
    ) -> List[Tuple[Tuple[Any, List[Any]], Tuple[Any, List[Any]]]]:
        """
        Finds optimal matches between paths using pre-computed critical point mapping.
        Prioritizes paths connecting mapped critical points.

        Args:
            concept_graph: The concept graph
            image_graph: The image graph
            paths_c: List of (end_point, path) tuples from concept graph
            paths_i: List of (end_point, path) tuples from image graph
            critical_point_mapping: Mapping of concept critical points to image critical points

        Returns:
            List of ((end_c, path_c), (end_i, path_i)) pairs representing matched paths
        """
        matched_pairs = []
        # Keep track of used paths (represented as tuples)
        used_paths_c = set()  # Set of normalized tuples (path_c)
        used_paths_i = set()  # Set of normalized tuples (path_i)

        # Priority 1: Match paths where endpoints are mapped
        potential_mapped_matches = []
        for idx_c, (end_c, path_c) in enumerate(paths_c):
            if end_c in critical_point_mapping:
                mapped_end_i = critical_point_mapping[end_c]
                for idx_i, (end_i, path_i) in enumerate(paths_i):
                    # Check if the end points match according to the mapping
                    if end_i == mapped_end_i:
                        # If concept path is longer than image path, try to find an alternative path
                        if len(path_c) > len(path_i):
                            # Find start node in image_graph corresponding to start of path_c
                            # The start node should be the mapped critical point of the first node in path_c
                            start_node_c = path_c[0]
                            if start_node_c in critical_point_mapping:
                                start_node_i = critical_point_mapping[start_node_c]

                                # Try to find an alternative path in image_graph
                                alt_path_i = self._find_alternative_image_path(
                                    image_graph, start_node_i, end_i, len(path_c)
                                )

                                if alt_path_i:
                                    # Use the alternative path instead
                                    path_i = alt_path_i
                                    logging.debug(
                                        f"Using alternative path for match {start_node_c}-{end_c}"
                                    )

                        # Calculate similarity score
                        path_similarity = self._calculate_path_similarity(
                            concept_graph, image_graph, path_c, path_i
                        )

                        # Store potential match with score, using path tuples as identifiers
                        if path_similarity > 0.2:  # Threshold for mapped paths
                            potential_mapped_matches.append(
                                (tuple(path_c), tuple(path_i), path_similarity)
                            )

        # Sort potential mapped matches by score (descending)
        potential_mapped_matches.sort(key=lambda x: x[2], reverse=True)

        # Greedily select best mapped matches, ensuring paths aren't reused
        path_dict_c = {
            tuple(p[1]): p for p in paths_c
        }  # Map path tuple back to original (end, path)
        path_dict_i = {tuple(p[1]): p for p in paths_i}

        for path_c_tuple, path_i_tuple, score in potential_mapped_matches:
            # Normalize path tuples to handle both directions
            norm_path_c = self._normalize_path_tuple(path_c_tuple)
            norm_path_i = self._normalize_path_tuple(path_i_tuple)

            if norm_path_c not in used_paths_c and norm_path_i not in used_paths_i:
                end_c, path_c = path_dict_c[path_c_tuple]
                end_i, path_i = path_dict_i[path_i_tuple]
                matched_pairs.append(((end_c, path_c), (end_i, path_i)))
                # Add normalized paths to used sets
                used_paths_c.add(norm_path_c)
                used_paths_i.add(norm_path_i)
                logging.debug(
                    f"Matched path (Mapped Endpoints) {end_c}-{end_i} with score {score:.2f}"
                )

        # Priority 2: Match remaining paths based on similarity
        remaining_paths_c_tuples = set(path_dict_c.keys()) - {
            self._normalize_path_tuple(p) for p in used_paths_c
        }
        remaining_paths_i_tuples = set(path_dict_i.keys()) - {
            self._normalize_path_tuple(p) for p in used_paths_i
        }

        compatible_ends = []
        for path_c_tuple in remaining_paths_c_tuples:
            for path_i_tuple in remaining_paths_i_tuples:
                end_c, path_c = path_dict_c[path_c_tuple]
                end_i, path_i = path_dict_i[path_i_tuple]

                # If concept path is longer than image path, try to find an alternative path
                if len(path_c) > len(path_i):
                    # Get start nodes
                    start_node_c = path_c[0]
                    start_node_i = path_i[
                        0
                    ]  # Assuming this is close to where we want to start

                    # Try to find a better path in the image graph
                    alt_path_i = self._find_alternative_image_path(
                        image_graph, start_node_i, end_i, len(path_c)
                    )

                    if alt_path_i:
                        # Use the alternative path
                        path_i = alt_path_i
                        # Update the path_i_tuple for later use
                        path_i_tuple = tuple(path_i)
                        logging.debug(
                            f"Using alternative path for non-mapped match to {end_c}"
                        )

                # Check if endpoints are type compatible using similarity calculator
                endpoint_similarity = (
                    self.similarity_calculator.calculate_node_similarity(
                        concept_graph, image_graph, end_c, end_i
                    )
                )

                if endpoint_similarity > 0.3:  # Threshold for endpoint compatibility
                    path_similarity = self._calculate_path_similarity(
                        concept_graph, image_graph, path_c, path_i
                    )
                    # Combined similarity considers both endpoint and path
                    adjusted_similarity = (
                        0.4 * endpoint_similarity + 0.6 * path_similarity
                    )

                    if (
                        adjusted_similarity > 0.3
                    ):  # Threshold for non-mapped/similarity match
                        compatible_ends.append(
                            (path_c_tuple, path_i_tuple, adjusted_similarity)
                        )

        compatible_ends.sort(key=lambda x: x[2], reverse=True)

        # Greedy selection for remaining paths
        for path_c_tuple, path_i_tuple, score in compatible_ends:
            # Normalize path tuples to handle both directions
            norm_path_c = self._normalize_path_tuple(path_c_tuple)
            norm_path_i = self._normalize_path_tuple(path_i_tuple)

            if norm_path_c not in used_paths_c and norm_path_i not in used_paths_i:
                end_c, path_c = path_dict_c[path_c_tuple]
                end_i, path_i = path_dict_i[path_i_tuple]
                matched_pairs.append(((end_c, path_c), (end_i, path_i)))
                # Add normalized paths to used sets
                used_paths_c.add(norm_path_c)
                used_paths_i.add(norm_path_i)
                logging.debug(
                    f"Matched remaining path {end_c}-{end_i} with similarity score {score:.2f}"
                )

        return matched_pairs

    def _calculate_critical_point_similarity(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
    ) -> Dict[str, Any]:
        """
        Calculate similarity between concept and image graphs based on critical points and path matching.
        This is the core algorithm that replaces _find_concept_minor_mapping with an approach
        more similar to GraphMinorFinder.

        Args:
            concept_graph: The concept graph
            image_graph: The image graph

        Returns:
            Dictionary containing similarity metrics and matches
        """
        # 1. Identify critical points in both graphs
        concept_critical_points = self._identify_critical_points(concept_graph)
        image_critical_points = self._identify_critical_points(image_graph)

        # Log statistics about critical points
        concept_critical_count = sum(len(p) for p in concept_critical_points.values())
        image_critical_count = sum(len(p) for p in image_critical_points.values())

        # Critical point type counts for detailed metrics
        concept_cp_counts = {k: len(v) for k, v in concept_critical_points.items()}
        image_cp_counts = {k: len(v) for k, v in image_critical_points.items()}

        logging.info(
            f"Concept has {concept_critical_count} critical points, Image has {image_critical_count} critical points"
        )
        logging.info(f"Concept critical point breakdown: {concept_cp_counts}")
        logging.info(f"Image critical point breakdown: {image_cp_counts}")

        # 2. Perform critical point matching
        critical_point_mapping = self._match_critical_points(
            concept_graph,
            image_graph,
            concept_critical_points,
            image_critical_points,
        )

        # If no critical points were matched, return early with zero similarity
        if not critical_point_mapping:
            logging.info(
                "No critical points could be matched between concept and image"
            )
            return {
                "match_type": "no_match",
                "cp_similarity": 0.0,
                "path_similarity": 0.0,
                "overall_similarity": 0.0,
                "mapped_cps": 0,
                "total_cps": concept_critical_count,
                "mapped_paths": 0,
                "total_paths": 0,
                "mapping": {},
                "cp_type_similarities": {},
                "quality_score": 0.0,
            }

        # 3. Calculate critical point similarity score by type (weighting different types)
        mapped_by_type = {}
        for concept_cp, image_cp in critical_point_mapping.items():
            # Find type of this critical point
            for cp_type, points in concept_critical_points.items():
                if concept_cp in points:
                    if cp_type not in mapped_by_type:
                        mapped_by_type[cp_type] = 0
                    mapped_by_type[cp_type] += 1
                    break

        # Default weights for different critical point types
        cp_type_weights = {
            "StartPoint": 1.0,  # StartPoints are essential
            "EndPoint": 0.6,  # EndPoints are important structural elements
            "IntersectionPoint": 0.8,  # IntersectionPoints define major structure
            "CornerPoint": 0.7,  # CornerPoints define shape
            "Point": 0.4,  # Generic points are less significant
        }

        # Calculate similarity by type
        cp_type_similarities = {}
        weighted_cp_sim_sum = 0.0
        total_weight = 0.0

        for cp_type, count in concept_cp_counts.items():
            if count == 0:  # Skip types with no points
                continue

            mapped = mapped_by_type.get(cp_type, 0)
            type_similarity = mapped / count
            cp_type_similarities[cp_type] = type_similarity

            # Apply weight for this type
            weight = cp_type_weights.get(cp_type, 0.5)
            weighted_cp_sim_sum += type_similarity * weight
            total_weight += weight

        # Overall critical point similarity (weighted by type)
        cp_similarity = weighted_cp_sim_sum / total_weight if total_weight > 0 else 0.0

        # Also calculate raw count-based similarity for reference
        raw_cp_similarity = (
            len(critical_point_mapping) / concept_critical_count
            if concept_critical_count > 0
            else 0.0
        )

        logging.info(f"Critical point similarity (weighted): {cp_similarity:.4f}")
        logging.info(f"Critical point similarity (raw): {raw_cp_similarity:.4f}")
        logging.info(f"Critical point similarities by type: {cp_type_similarities}")

        # 4. Find and match paths between critical points
        all_path_pairs = []
        total_concept_paths = 0

        # Track path quality for each critical point pair
        path_qualities_by_pair = {}

        # For each mapped critical point, find paths to other critical points
        for concept_cp, image_cp in critical_point_mapping.items():
            # Find paths from this critical point to other critical points
            concept_paths = self._find_paths_to_next_critical(
                concept_graph, concept_cp, concept_critical_points
            )
            image_paths = self._find_paths_to_next_critical(
                image_graph, image_cp, image_critical_points
            )

            total_concept_paths += len(concept_paths)

            # Find optimal matches between these paths
            matched_paths = self._find_optimal_path_matches(
                concept_graph,
                image_graph,
                concept_paths,
                image_paths,
                critical_point_mapping,
            )

            # Calculate quality metrics for paths between these critical points
            if matched_paths:
                pair_qualities = []
                for (end_c, path_c), (end_i, path_i) in matched_paths:
                    path_sim = self._calculate_path_similarity(
                        concept_graph, image_graph, path_c, path_i
                    )
                    pair_qualities.append(path_sim)

                # Store average quality for this critical point pair
                if pair_qualities:
                    pair_key = (
                        f"{concept_cp}-{critical_point_mapping.get(end_c, 'unmapped')}"
                    )
                    path_qualities_by_pair[pair_key] = sum(pair_qualities) / len(
                        pair_qualities
                    )

            all_path_pairs.extend(matched_paths)

        # 5. Calculate path similarity score (coverage)
        if total_concept_paths > 0:
            path_similarity = len(all_path_pairs) / total_concept_paths
        else:
            path_similarity = 0.0

        logging.info(
            f"Path similarity: {path_similarity:.4f} ({len(all_path_pairs)}/{total_concept_paths})"
        )

        # 6. Calculate path quality scores
        path_quality = 0.0
        max_path_quality = 0.0
        min_path_quality = 1.0

        if all_path_pairs:
            total_quality = 0.0
            path_qualities = []

            for (_, path_c), (_, path_i) in all_path_pairs:
                path_sim = self._calculate_path_similarity(
                    concept_graph, image_graph, path_c, path_i
                )
                path_qualities.append(path_sim)
                total_quality += path_sim

                # Track min/max for range calculation
                max_path_quality = max(max_path_quality, path_sim)
                min_path_quality = min(min_path_quality, path_sim)

            path_quality = total_quality / len(all_path_pairs)

            # Calculate standard deviation for quality consistency measure
            if len(path_qualities) > 1:
                import statistics

                quality_std_dev = statistics.stdev(path_qualities)
            else:
                quality_std_dev = 0.0

            quality_consistency = 1.0 - (
                quality_std_dev / max(0.01, path_quality)
            )  # Higher is better
        else:
            quality_std_dev = 0.0
            quality_consistency = 0.0

        path_quality_range = (
            max_path_quality - min_path_quality if all_path_pairs else 0.0
        )

        logging.info(f"Average path quality: {path_quality:.4f}")
        logging.info(
            f"Path quality range: {min_path_quality:.2f}-{max_path_quality:.2f}"
        )
        logging.info(f"Quality consistency: {quality_consistency:.4f}")

        # 7. Calculate connectivity score - how well critical points are connected
        connectivity_score = 0.0
        if (
            concept_critical_count > 1
        ):  # Need at least 2 critical points for connectivity
            max_possible_pairs = (
                concept_critical_count * (concept_critical_count - 1) / 2
            )
            connected_pairs = len(path_qualities_by_pair)
            connectivity_score = connected_pairs / max_possible_pairs

        logging.info(f"Connectivity score: {connectivity_score:.4f}")

        # 8. Calculate structure quality score - combines connectivity and path quality
        structure_quality = 0.5 * connectivity_score + 0.5 * path_quality

        # 9. Calculate overall quality score (how well matched parts match)
        # Weight critical point similarity more than path factors, but consider all aspects
        quality_score = (
            0.5 * cp_similarity
            + 0.2 * path_similarity
            + 0.2 * path_quality
            + 0.1 * quality_consistency
        )

        # 10. Calculate overall similarity score (coverage + quality)
        # More sophisticated weighting that considers both coverage and quality
        coverage_score = 0.65 * cp_similarity + 0.35 * path_similarity
        overall_similarity = 0.7 * coverage_score + 0.3 * quality_score

        logging.info(f"Coverage score: {coverage_score:.4f}")
        logging.info(f"Quality score: {quality_score:.4f}")
        logging.info(f"Overall similarity score: {overall_similarity:.4f}")

        # 11. Determine match type with more nuanced thresholds
        match_type = "no_match"
        # Complete match requires high overall similarity AND good quality
        if overall_similarity >= 0.85 and quality_score >= 0.75:
            match_type = "complete_match"
        # Good match is nearly complete with good quality
        elif overall_similarity >= 0.75 and quality_score >= 0.6:
            match_type = "good_match"
        # Partial match has decent similarity but may lack in quality
        elif overall_similarity >= self.min_structural_score:
            match_type = "partial_match"

        # Create mapping result
        # Convert critical_point_mapping to a standard dictionary for serialization
        serializable_mapping = {
            str(k): str(v) for k, v in critical_point_mapping.items()
        }

        return {
            "match_type": match_type,
            "cp_similarity": cp_similarity,
            "raw_cp_similarity": raw_cp_similarity,
            "path_similarity": path_similarity,
            "path_quality": path_quality,
            "quality_consistency": quality_consistency,
            "connectivity_score": connectivity_score,
            "structure_quality": structure_quality,
            "quality_score": quality_score,
            "coverage_score": coverage_score,
            "overall_similarity": overall_similarity,
            "mapped_cps": len(critical_point_mapping),
            "total_cps": concept_critical_count,
            "mapped_paths": len(all_path_pairs),
            "total_paths": total_concept_paths,
            "cp_type_similarities": cp_type_similarities,
            "path_quality_range": [min_path_quality, max_path_quality],
            "path_quality_by_pair": path_qualities_by_pair,
            "mapping": serializable_mapping,
        }

    def _identify_critical_points(self, graph: nx.Graph) -> Dict[str, List[Any]]:
        """
        Identify critical points in a graph (intersection points, corner points, end points, start points).
        Delegates to the preprocessor to ensure consistency with GraphMinorFinder.

        Args:
            graph: The graph to analyze

        Returns:
            Dictionary mapping point types to lists of node IDs
        """
        logging.debug(
            f"Identifying critical points in graph with {len(graph.nodes)} nodes"
        )
        # Delegate to the preprocessor's implementation
        critical_points = self.preprocessor._identify_critical_points(graph)

        logging.debug(
            f"Found critical points: {', '.join(f'{k}={len(v)}' for k, v in critical_points.items())}"
        )
        return critical_points

    def _calculate_node_similarity(
        self, graph1: nx.Graph, graph2: nx.Graph, node1: Any, node2: Any
    ) -> float:
        """
        Calculate similarity between two nodes using the NodeSimilarityCalculator.
        This replaces the basic property matching with a more sophisticated similarity measure.

        Args:
            graph1: First graph (concept)
            graph2: Second graph (image)
            node1: Node ID in first graph (concept)
            node2: Node ID in second graph (image)

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # First check asymmetric type compatibility - concept nodes must be exactly matched or higher
        if not self._check_asymmetric_node_type_compatibility(
            graph1.nodes[node1], graph2.nodes[node2]
        ):
            return 0.0  # Image node type is lower in hierarchy than concept requires

        # Use the NodeSimilarityCalculator for robust similarity calculation
        return self.similarity_calculator.calculate_node_similarity(
            graph1, graph2, node1, node2
        )

    def _check_asymmetric_node_type_compatibility(
        self, concept_node_data: Dict[str, Any], image_node_data: Dict[str, Any]
    ) -> bool:
        """
        Check if image node type is compatible with concept node type in an asymmetric way.
        The image node can be reduced (treated as a lower type), but concept node requirements are strict.

        Hierarchy: Point (lowest) < CornerPoint < IntersectionPoint (highest)

        Args:
            concept_node_data: Node data from concept graph
            image_node_data: Node data from image graph

        Returns:
            True if image node's type is compatible with concept node's type, False otherwise
        """
        # Define the hierarchy of point types (higher number = higher in hierarchy)
        type_hierarchy = {
            "Point": 0,
            "CornerPoint": 1,
            "IntersectionPoint": 2,
            # StartPoint and EndPoint are special and handled separately
            "StartPoint": -1,  # Special case
            "EndPoint": -1,  # Special case
        }

        # Get labels for both nodes
        concept_labels = concept_node_data.get("labels", [])
        image_labels = image_node_data.get("labels", [])

        # Find highest type level for concept node
        concept_level = -1
        for label in concept_labels:
            if label in type_hierarchy and type_hierarchy[label] > concept_level:
                concept_level = type_hierarchy[label]

        # Find highest type level for image node
        image_level = -1
        for label in image_labels:
            if label in type_hierarchy and type_hierarchy[label] > image_level:
                image_level = type_hierarchy[label]

        # StartPoint must match with StartPoint, EndPoint with EndPoint
        if "StartPoint" in concept_labels and "StartPoint" not in image_labels:
            return False
        if "EndPoint" in concept_labels and "EndPoint" not in image_labels:
            return False

        # For regular point types, check hierarchy
        # Image level must be >= concept level for compatibility
        # This means image can match concept if it's of same or higher type
        if concept_level >= 0:  # Only check if concept has a defined point type
            return image_level >= concept_level

        # If concept doesn't have a point type in our hierarchy, default to compatible
        return True

    def _match_critical_points(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        concept_critical_points: Dict[str, List[Any]],
        image_critical_points: Dict[str, List[Any]],
    ) -> Dict[Any, Any]:
        """
        Match critical points between concept and image graphs based on compatibility and similarity.
        Creates a mapping from concept critical points to image critical points.

        Args:
            concept_graph: Concept graph
            image_graph: Image graph
            concept_critical_points: Dictionary of critical point types to nodes in concept graph
            image_critical_points: Dictionary of critical point types to nodes in image graph

        Returns:
            Dictionary mapping concept critical points to image critical points
        """
        # Dictionary to store the mapping from concept critical points to image critical points
        critical_point_mapping = {}

        # Log critical point counts
        concept_critical_count = sum(len(p) for p in concept_critical_points.values())
        image_critical_count = sum(len(p) for p in image_critical_points.values())

        logging.info(
            f"Matching {concept_critical_count} concept critical points to {image_critical_count} image critical points"
        )

        for cp_type, concept_points in concept_critical_points.items():
            logging.debug(
                f"Matching critical points of type {cp_type}: {len(concept_points)} in concept, {len(image_critical_points.get(cp_type, []))} in image"
            )
            image_points = image_critical_points.get(cp_type, [])

            # The preprocessor should have ensured that counts match, but let's verify
            if len(concept_points) != len(image_points):
                logging.warning(
                    f"Critical point count mismatch for {cp_type} after preprocessing: {len(concept_points)} vs {len(image_points)}"
                )

            # Calculate similarity between all points of this type
            available_image_points = set(image_points)

            # Handle each concept point
            for concept_cp in concept_points:
                best_match = None
                best_score = 0

                # Find the best match among available image points
                for image_cp in available_image_points:
                    # Use our node similarity method for more robust comparison
                    similarity = self._calculate_node_similarity(
                        concept_graph, image_graph, concept_cp, image_cp
                    )

                    if similarity > best_score:
                        best_score = similarity
                        best_match = image_cp

                # Use a good match if found
                if (
                    best_match and best_score > 0.3
                ):  # Lower threshold since preprocess aligned points
                    critical_point_mapping[concept_cp] = best_match
                    available_image_points.remove(best_match)
                    logging.debug(
                        f"Matched {cp_type} {concept_cp} to {best_match} with score {best_score:.2f}"
                    )
                else:
                    # Just pick the first available one if none has good similarity
                    if available_image_points:
                        fallback_match = next(iter(available_image_points))
                        critical_point_mapping[concept_cp] = fallback_match
                        available_image_points.remove(fallback_match)
                        logging.debug(
                            f"Fallback match for {cp_type} {concept_cp} to {fallback_match} (no good similarity)"
                        )
                    else:
                        logging.warning(
                            f"Could not find match for {cp_type} {concept_cp} - no available points left"
                        )

        # Log the results of matching
        logging.info(
            f"Successfully mapped {len(critical_point_mapping)} out of {concept_critical_count} concept critical points"
        )

        # Log which points were not mapped
        unmapped_points = set()
        for points in concept_critical_points.values():
            for cp in points:
                if cp not in critical_point_mapping:
                    unmapped_points.add(cp)

        if unmapped_points:
            logging.warning(f"Failed to map {len(unmapped_points)} critical points")
            for cp in unmapped_points:
                for cp_type, points in concept_critical_points.items():
                    if cp in points:
                        logging.warning(f"  - Unmapped {cp_type}: {cp}")

        return critical_point_mapping
