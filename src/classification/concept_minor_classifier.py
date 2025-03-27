import logging
import networkx as nx
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor

from graph_similarity.neo4j_to_networkx import Neo4jToNetworkX
from property_handlers import PropertyMatcherManager

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
        # Get concept graph
        concept_graph = Neo4jToNetworkX.extract_concept_graph(tx, concept_id)

        # Quick size-based early rejection
        if len(concept_graph.nodes) > len(image_graph.nodes) * 1.5:
            return self._create_no_match_result(
                concept_id, len(concept_graph.nodes) + len(concept_graph.edges)
            )

        concept_complexity = len(concept_graph.nodes) + len(concept_graph.edges)

        # Get start points
        concept_start_points = self._get_nodes_with_label(concept_graph, "StartPoint")
        image_start_points = self._get_nodes_with_label(image_graph, "StartPoint")

        # Initialize result with no match
        result = self._create_no_match_result(concept_id, concept_complexity)

        # Handle early return cases
        if not concept_start_points or not image_start_points:
            result["comparison_message"] = (
                f"Cannot match concept {concept_id}: "
                f"Concept has {len(concept_start_points)} StartPoints, "
                f"Image has {len(image_start_points)} StartPoints"
            )
            return result

        # Early structural check - validate node labels distribution
        concept_label_counts = self._count_node_labels(concept_graph)
        image_label_counts = self._count_node_labels(image_graph)

        if not self._check_label_distribution_compatible(
            concept_label_counts, image_label_counts
        ):
            result["comparison_message"] = (
                f"Concept {concept_id} has incompatible node label distribution with image"
            )
            return result

        # Try all possible StartPoint matchings
        for concept_start in concept_start_points:
            for image_start in image_start_points:
                if not self._check_node_properties_match(
                    concept_graph.nodes[concept_start], image_graph.nodes[image_start]
                ):
                    continue

                # Try to find a complete matching starting from these points
                mapping = self._find_concept_minor_mapping(
                    concept_graph,
                    image_graph,
                    {concept_start: image_start},
                )

                if not mapping:
                    continue

                mapping_size = len(mapping)
                concept_size = len(concept_graph.nodes)

                # Count contractions if any
                contractions_count = 0
                if hasattr(mapping, "contractions"):
                    contractions_count = sum(
                        len(nodes) for nodes in mapping.contractions.values()
                    )

                # Update result if we found a complete or better partial match
                if mapping_size == concept_size:
                    return self._create_complete_match_result(
                        concept_id,
                        concept_complexity,
                        mapping_size,
                        concept_size,
                        len(image_graph.nodes),
                        contractions_count,
                    )
                elif mapping_size > 0:
                    partial_similarity = mapping_size / concept_size

                    # Early stopping if we found a good enough match
                    if partial_similarity >= self.early_stopping_threshold:
                        return self._create_partial_match_result(
                            concept_id,
                            concept_complexity,
                            partial_similarity,
                            mapping_size,
                            concept_size,
                            len(image_graph.nodes),
                            contractions_count,
                        )

                    if partial_similarity > result.get("raw_structural_score", 0):
                        result = self._create_partial_match_result(
                            concept_id,
                            concept_complexity,
                            partial_similarity,
                            mapping_size,
                            concept_size,
                            len(image_graph.nodes),
                            contractions_count,
                        )

        return result

    def _get_nodes_with_label(self, graph: nx.Graph, label: str) -> List[Any]:
        return [
            node
            for node, attrs in graph.nodes(data=True)
            if "labels" in attrs and label in attrs["labels"]
        ]

    def _create_no_match_result(
        self, concept_id: str, concept_complexity: int
    ) -> Dict[str, Any]:
        return {
            "concept_id": concept_id,
            "concept_name": concept_id,
            "session_id": concept_id,
            "raw_structural_score": 0.0,
            "is_minor": False,
            "concept_complexity": concept_complexity,
            "comparison_message": f"No match found for concept {concept_id}",
        }

    def _create_complete_match_result(
        self,
        concept_id: str,
        concept_complexity: int,
        mapping_size: int,
        concept_size: int,
        image_size: int,
        contractions_count: int = 0,
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
            "comparison_message": (
                f"Concept {concept_id} is a minor of the image graph "
                f"with a complete matching of {mapping_size} nodes"
                + (
                    f" using {contractions_count} node contractions"
                    if contractions_count > 0
                    else ""
                )
            ),
            "concept_complexity": concept_complexity,
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
            "comparison_message": (
                f"Partial matching for concept {concept_id} with "
                f"{mapping_size}/{concept_size} nodes matched "
                f"({partial_similarity:.2%})"
                + (
                    f" using {contractions_count} node contractions"
                    if contractions_count > 0
                    else ""
                )
            ),
            "concept_complexity": concept_complexity,
        }

    def _check_node_properties_match(
        self, concept_node_data: Dict[str, Any], image_node_data: Dict[str, Any]
    ) -> bool:
        """
        Check if all required properties of a concept node match an image node.
        Uses the PropertyMatcherManager to handle different property types.

        Args:
            concept_node_data: Properties of the concept node
            image_node_data: Properties of the image node

        Returns:
            True if all concept properties match the image, False otherwise
        """
        return self.property_matcher.check_node_properties_match(
            concept_node_data, image_node_data
        )

    def _property_values_match(self, concept_value: Any, image_value: Any) -> bool:
        """
        Check if a concept property value matches an image property value.
        Uses the PropertyMatcherManager to handle different property types.

        Args:
            concept_value: Value from the concept
            image_value: Value from the image

        Returns:
            True if values match, False otherwise
        """
        return self.property_matcher.is_property_match(concept_value, image_value)

    def _find_concept_minor_mapping(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        initial_mapping: Dict[Any, Any],
    ) -> Dict[Any, Any]:
        mapping = initial_mapping.copy()
        inverse_mapping = {v: k for k, v in mapping.items()}
        contractions = {}  # Store node contractions (paths)

        # Initialize frontier with neighbors of mapped nodes
        concept_frontier = self._get_initial_frontier(concept_graph, mapping)

        # Iteratively grow the mapping
        while concept_frontier:
            concept_node, image_node, contraction_path = self._find_next_match(
                concept_graph, image_graph, mapping, concept_frontier
            )

            if concept_node is None:  # No match found
                break

            # Update mappings and frontier
            mapping[concept_node] = image_node
            inverse_mapping[image_node] = concept_node
            concept_frontier.remove(concept_node)

            # Store contraction path if it exists
            if contraction_path:
                contractions[concept_node] = contraction_path

            # Add new frontier nodes
            for new_neighbor in concept_graph.neighbors(concept_node):
                if new_neighbor not in mapping and new_neighbor not in concept_frontier:
                    concept_frontier.add(new_neighbor)

        # Store contractions in the mapping object
        if contractions:
            mapping.contractions = contractions

        return mapping

    def _get_initial_frontier(
        self, concept_graph: nx.Graph, mapping: Dict[Any, Any]
    ) -> set:
        frontier = set()
        for concept_node in mapping:
            frontier.update(concept_graph.neighbors(concept_node))

        # Remove already mapped nodes
        return frontier - set(mapping.keys())

    def _find_next_match(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        mapping: Dict[Any, Any],
        concept_frontier: set,
    ) -> Tuple[Any, Any, List[Any]]:  # Now returns contraction path as third element
        # Sort frontier nodes by connectivity - prioritize nodes with more mapped neighbors
        concept_nodes_with_priority = []
        for concept_node in concept_frontier:
            mapped_neighbors = [
                n for n in concept_graph.neighbors(concept_node) if n in mapping
            ]
            if mapped_neighbors:
                concept_nodes_with_priority.append(
                    (concept_node, len(mapped_neighbors))
                )

        # Sort by number of mapped neighbors (descending)
        concept_nodes_with_priority.sort(key=lambda x: x[1], reverse=True)

        # Try to match nodes with more constraints first (more mapped neighbors)
        for concept_node, _ in concept_nodes_with_priority:
            mapped_neighbors = [
                n for n in concept_graph.neighbors(concept_node) if n in mapping
            ]

            # Get corresponding image nodes - now includes nodes reachable via paths
            image_candidates, path_data = self._get_image_candidates_with_paths(
                image_graph, mapped_neighbors, mapping
            )

            # Sort image candidates by how well they match the concept node
            scored_candidates = []
            for image_node in image_candidates:
                if self._check_node_properties_match(
                    concept_graph.nodes[concept_node], image_graph.nodes[image_node]
                ):
                    score = self._calculate_candidate_score(
                        concept_graph,
                        image_graph,
                        concept_node,
                        image_node,
                        mapped_neighbors,
                        mapping,
                        path_data.get(image_node, {}),
                    )
                    scored_candidates.append((image_node, score))

            # Sort candidates by score (descending)
            scored_candidates.sort(key=lambda x: x[1], reverse=True)

            # Try candidates in order of score
            for image_node, _ in scored_candidates:
                is_compatible, contraction_paths = self._is_compatible_match(
                    concept_graph,
                    image_graph,
                    concept_node,
                    image_node,
                    mapped_neighbors,
                    mapping,
                    path_data.get(image_node, {}),
                )

                if is_compatible:
                    # Flatten contraction paths into a single list of all intermediate nodes
                    all_contraction_nodes = []
                    for path in contraction_paths.values():
                        if (
                            path and len(path) > 2
                        ):  # Only include paths with intermediate nodes
                            all_contraction_nodes.extend(
                                path[1:-1]
                            )  # Skip first and last nodes

                    return concept_node, image_node, all_contraction_nodes

        return None, None, []  # No match found

    def _calculate_candidate_score(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        concept_node: Any,
        image_node: Any,
        mapped_neighbors: List[Any],
        mapping: Dict[Any, Any],
        path_data: Dict[Any, List[Any]] = None,
    ) -> float:
        # Base score from property matches
        property_score = 0
        concept_props = concept_graph.nodes[concept_node]
        image_props = image_graph.nodes[image_node]

        # Count matching properties
        matching_props = 0
        total_props = 0
        for key, value in concept_props.items():
            if key not in PropertyMatcherManager.LIST_IGNORE_KEYS:
                total_props += 1
                if key in image_props and self._property_values_match(
                    value, image_props[key]
                ):
                    matching_props += 1

        property_score = matching_props / max(1, total_props)

        # Structural score based on how many mapped neighbors are connected (directly or via path)
        structural_score = 0
        connected_neighbors = 0
        for concept_neighbor in mapped_neighbors:
            image_neighbor = mapping[concept_neighbor]
            # Check direct edge or path
            if image_graph.has_edge(image_node, image_neighbor) or (
                path_data and image_neighbor in path_data
            ):
                connected_neighbors += 1

                # Penalize slightly for longer paths
                if path_data and image_neighbor in path_data:
                    path_length = len(path_data[image_neighbor])
                    if path_length > 2:  # Direct edge is length 2 (start and end)
                        structural_score -= 0.05 * (
                            path_length - 2
                        )  # Small penalty for each intermediate node

        structural_score += connected_neighbors / max(1, len(mapped_neighbors))

        # Future connectivity score - how many unmapped neighbors this node has
        # that could potentially extend the mapping
        future_connectivity = 0
        unmapped_concept_neighbors = [
            n
            for n in concept_graph.neighbors(concept_node)
            if n not in mapping and n not in mapped_neighbors
        ]

        if unmapped_concept_neighbors:
            future_connectivity = len(unmapped_concept_neighbors) / len(
                concept_graph.nodes
            )

        # Combined score with weights
        return 0.4 * property_score + 0.5 * structural_score + 0.1 * future_connectivity

    def _get_image_candidates_with_paths(
        self,
        image_graph: nx.Graph,
        mapped_neighbors: List[Any],
        mapping: Dict[Any, Any],
    ) -> Tuple[set, Dict[Any, Dict[Any, List[Any]]]]:
        """
        Get all candidate image nodes that could match a concept node, including nodes
        reachable via paths from mapped neighbors.

        Returns:
            - Set of candidate image nodes
            - Dict mapping each candidate to its paths from mapped neighbors
        """
        # Get all neighboring image nodes (direct neighbors first)
        inverse_mapping = {v: k for k, v in mapping.items()}
        image_neighbors = set()
        path_data = {}  # Track paths from mapped neighbors to candidates

        # First, collect direct neighbors
        for concept_neighbor in mapped_neighbors:
            image_neighbor = mapping[concept_neighbor]
            direct_neighbors = set(image_graph.neighbors(image_neighbor))

            # Store direct paths
            for direct_node in direct_neighbors:
                if direct_node not in path_data:
                    path_data[direct_node] = {}
                path_data[direct_node][image_neighbor] = [image_neighbor, direct_node]

            image_neighbors.update(direct_neighbors)

        # Now find paths of any length
        for concept_neighbor in mapped_neighbors:
            image_neighbor = mapping[concept_neighbor]

            # Use BFS to find all reachable nodes
            for target_node, path in self._find_paths_bfs(
                image_graph, image_neighbor, inverse_mapping.keys()
            ).items():
                if (
                    target_node not in inverse_mapping
                ):  # Don't map to already mapped nodes
                    image_neighbors.add(target_node)
                    if target_node not in path_data:
                        path_data[target_node] = {}
                    path_data[target_node][image_neighbor] = path

        # Remove already mapped nodes
        return image_neighbors - set(inverse_mapping.keys()), path_data

    def _find_paths_bfs(
        self, graph: nx.Graph, start_node: Any, exclude_nodes: set
    ) -> Dict[Any, List[Any]]:
        """
        Find paths from start_node to all reachable nodes.
        Exclude paths through nodes in exclude_nodes.

        Returns dict mapping target nodes to their paths from start_node.
        """
        paths = {}  # Target node -> path from start_node
        queue = [(start_node, [start_node])]  # (node, path to this node)
        visited = {start_node}

        while queue:
            current, path = queue.pop(0)

            for neighbor in graph.neighbors(current):
                if neighbor in visited or neighbor in exclude_nodes:
                    continue

                new_path = path + [neighbor]
                paths[neighbor] = new_path

                queue.append((neighbor, new_path))
                visited.add(neighbor)

        return paths

    def _is_compatible_match(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        concept_node: Any,
        image_node: Any,
        mapped_neighbors: List[Any],
        mapping: Dict[Any, Any],
        path_data: Dict[Any, List[Any]] = None,
    ) -> Tuple[bool, Dict[Any, List[Any]]]:
        """
        Check if a concept node can be matched with an image node.
        Now returns both a boolean indicating compatibility and the paths used for contractions.
        """
        # Check property compatibility
        if not self._check_node_properties_match(
            concept_graph.nodes[concept_node], image_graph.nodes[image_node]
        ):
            return False, {}

        # Check structural compatibility - now allows paths instead of just direct edges
        compatible_paths = {}
        for concept_neighbor in mapped_neighbors:
            image_neighbor = mapping[concept_neighbor]

            # Case 1: Direct edge exists
            if image_graph.has_edge(image_node, image_neighbor):
                compatible_paths[image_neighbor] = [image_node, image_neighbor]
                continue

            # Case 2: Path exists in path_data
            if path_data and image_neighbor in path_data:
                compatible_paths[image_neighbor] = path_data[image_neighbor]
                continue

            # No connection found, not compatible
            return False, {}

        return True, compatible_paths

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
        apply_post_processing: bool = True,
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
        processed_results = self._process_and_sort_results(results, image_id)

        # Apply simple post-processing if requested
        if apply_post_processing and processed_results:
            return self._post_process_results(processed_results)

        return processed_results

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

        # Pre-filter results that don't meet our structural threshold for partial matches
        filtered_results = []
        for result in results:
            # Full matches (is_minor=True) are always included
            # if True:  # result.get("is_minor", False):
            #     filtered_results.append(result)
            # For partial matches, apply structural score threshold
            if result.get("raw_structural_score", 0) >= self.min_structural_score:
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

        # Group results by structural score to implement the new approach
        structural_score_groups = {}
        for result in filtered_results:
            score = result.get("raw_structural_score", 0)
            if score not in structural_score_groups:
                structural_score_groups[score] = []
            structural_score_groups[score].append(result)

        # Calculate additional metrics for each result
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

        # Process each group to implement the new scoring approach
        for score, group in structural_score_groups.items():
            if len(group) == 1:
                # Only one concept with this structural score, just use the raw score
                group[0]["combined_score"] = score
                group[0]["activation_level"] = score
            else:
                # Multiple concepts with the same structural score
                # Use complexity as a tiebreaker
                for result in group:
                    # Add a tiny weight to complexity as a tiebreaker
                    # The 0.0001 factor ensures it doesn't override the structural score
                    result["combined_score"] = score + (
                        0.0001 * result["normalized_complexity"]
                    )
                    result["activation_level"] = result["combined_score"]

            # Log scores for debugging
            for result in group:
                logging.info(
                    f"Scores for concept {result['concept_id']} and image {image_id}:\n"
                    f"Structural: {score:.4f}, "
                    f"Complexity: {result['normalized_complexity']:.4f}, "
                    f"Specificity: {result['normalized_specificity']:.4f}, "
                    f"Combined: {result['combined_score']:.4f}"
                )

        # Sort by combined score (which now prioritizes structural similarity)
        filtered_results.sort(
            key=lambda x: x.get("combined_score", 0),
            reverse=True,
        )

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

    def _post_process_results(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply simple post-processing to refine classification results"""
        if not results:
            return results

        # Apply any additional filtering or adjustments here
        # Since we don't have concept relationships, we just return the processed results

        return results

    def _count_node_labels(self, graph: nx.Graph) -> Dict[str, int]:
        """Count occurrences of each label in the graph"""
        label_counts = {}
        for _, attrs in graph.nodes(data=True):
            if "labels" in attrs:
                for label in attrs["labels"]:
                    if label not in label_counts:
                        label_counts[label] = 0
                    label_counts[label] += 1
        return label_counts

    def _check_label_distribution_compatible(
        self, concept_label_counts: Dict[str, int], image_label_counts: Dict[str, int]
    ) -> bool:
        """Check if the image has enough nodes of each label type needed by the concept"""
        for label, count in concept_label_counts.items():
            # Skip common labels like Point that may not be discriminative
            if label in ["Point"]:
                continue

            # If image doesn't have this label at all, it's incompatible
            if label not in image_label_counts:
                return False

            # If image has fewer nodes of this label than concept needs, it's incompatible
            if image_label_counts[label] < count:
                return False

        return True
