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
        min_structural_score: float = 0.7,
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
        visualization_callback: Optional[Callable] = None,
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
                    visualization_callback,
                )

                if not mapping:
                    continue

                mapping_size = len(mapping)
                concept_size = len(concept_graph.nodes)

                # Update result if we found a complete or better partial match
                if mapping_size == concept_size:
                    return self._create_complete_match_result(
                        concept_id,
                        concept_complexity,
                        mapping_size,
                        concept_size,
                        len(image_graph.nodes),
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
                        )

                    if partial_similarity > result.get("raw_structural_score", 0):
                        result = self._create_partial_match_result(
                            concept_id,
                            concept_complexity,
                            partial_similarity,
                            mapping_size,
                            concept_size,
                            len(image_graph.nodes),
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
            "comparison_message": (
                f"Concept {concept_id} is a minor of the image graph "
                f"with a complete matching of {mapping_size} nodes"
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
            "comparison_message": (
                f"Partial matching for concept {concept_id} with "
                f"{mapping_size}/{concept_size} nodes matched "
                f"({partial_similarity:.2%})"
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
        visualization_callback: Optional[Callable] = None,
    ) -> Dict[Any, Any]:
        mapping = initial_mapping.copy()
        inverse_mapping = {v: k for k, v in mapping.items()}

        # Initialize frontier with neighbors of mapped nodes
        concept_frontier = self._get_initial_frontier(concept_graph, mapping)

        # Iteratively grow the mapping
        while concept_frontier:
            concept_node, image_node = self._find_next_match(
                concept_graph, image_graph, mapping, concept_frontier
            )

            if concept_node is None:  # No match found
                break

            # Update mappings and frontier
            mapping[concept_node] = image_node
            inverse_mapping[image_node] = concept_node
            concept_frontier.remove(concept_node)

            # Add new frontier nodes
            for new_neighbor in concept_graph.neighbors(concept_node):
                if new_neighbor not in mapping and new_neighbor not in concept_frontier:
                    concept_frontier.add(new_neighbor)

        # Handle visualization if needed
        if visualization_callback and mapping:
            self._visualize_mapping(
                concept_graph, image_graph, mapping, visualization_callback
            )

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
    ) -> Tuple[Any, Any]:
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

            # Get corresponding image nodes
            image_candidates = self._get_image_candidates(
                image_graph, mapped_neighbors, mapping
            )

            # Sort image candidates by how well they match the concept node
            # (e.g., by number of matching properties or shared connections)
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
                    )
                    scored_candidates.append((image_node, score))

            # Sort candidates by score (descending)
            scored_candidates.sort(key=lambda x: x[1], reverse=True)

            # Try candidates in order of score
            for image_node, _ in scored_candidates:
                if self._is_compatible_match(
                    concept_graph,
                    image_graph,
                    concept_node,
                    image_node,
                    mapped_neighbors,
                    mapping,
                ):
                    return concept_node, image_node

        return None, None  # No match found

    def _calculate_candidate_score(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        concept_node: Any,
        image_node: Any,
        mapped_neighbors: List[Any],
        mapping: Dict[Any, Any],
    ) -> float:
        # Base score from property matches
        property_score = 0
        concept_props = concept_graph.nodes[concept_node]
        image_props = image_graph.nodes[image_node]

        # Count matching properties
        matching_props = 0
        total_props = 0
        for key, value in concept_props.items():
            if key not in ["labels", "visualization"]:
                total_props += 1
                if key in image_props and self._property_values_match(
                    value, image_props[key]
                ):
                    matching_props += 1

        property_score = matching_props / max(1, total_props)

        # Structural score based on how many mapped neighbors are connected
        structural_score = 0
        connected_neighbors = 0
        for concept_neighbor in mapped_neighbors:
            image_neighbor = mapping[concept_neighbor]
            if image_graph.has_edge(image_node, image_neighbor):
                connected_neighbors += 1

        structural_score = connected_neighbors / max(1, len(mapped_neighbors))

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

    def _get_image_candidates(
        self,
        image_graph: nx.Graph,
        mapped_neighbors: List[Any],
        mapping: Dict[Any, Any],
    ) -> set:
        # Get all neighboring image nodes
        inverse_mapping = {v: k for k, v in mapping.items()}
        image_neighbors = set()

        for concept_neighbor in mapped_neighbors:
            image_neighbor = mapping[concept_neighbor]
            image_neighbors.update(image_graph.neighbors(image_neighbor))

        # Remove already mapped nodes
        return image_neighbors - set(inverse_mapping.keys())

    def _is_compatible_match(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        concept_node: Any,
        image_node: Any,
        mapped_neighbors: List[Any],
        mapping: Dict[Any, Any],
    ) -> bool:
        # Check property compatibility
        if not self._check_node_properties_match(
            concept_graph.nodes[concept_node], image_graph.nodes[image_node]
        ):
            return False

        # Check structural compatibility
        for concept_neighbor in mapped_neighbors:
            image_neighbor = mapping[concept_neighbor]
            if not image_graph.has_edge(image_node, image_neighbor):
                return False

        return True

    def _visualize_mapping(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        mapping: Dict[Any, Any],
        visualization_callback: Callable,
    ) -> None:
        # Deep copy graphs to avoid modifying the originals
        concept_copy = concept_graph.copy()
        image_copy = image_graph.copy()

        # Highlight matched nodes
        for concept_node, image_node in mapping.items():
            self._highlight_node(concept_copy, concept_node, image_node)
            self._highlight_node(image_copy, image_node, concept_node)

        visualization_callback(
            "Minor Mapping",
            concept_copy,
            image_copy,
            None,  # No MCM graph
            mapping,
            {v: k for k, v in mapping.items()},
            [],  # No contractions
            None,  # No property changes
        )

    def _highlight_node(self, graph: nx.Graph, node: Any, matched_to: Any) -> None:
        if "visualization" not in graph.nodes[node]:
            graph.nodes[node]["visualization"] = {}

        graph.nodes[node]["visualization"]["highlight"] = True
        graph.nodes[node]["visualization"]["matched_to"] = matched_to

    def _check_single_concept(
        self,
        image_graph: nx.Graph,
        concept_id: str,
        visualization_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        with self.driver.session() as session:
            return session.execute_read(
                self._check_concept_minor_tx,
                image_graph,
                concept_id,
                visualization_callback,
            )

    def classify(
        self,
        image_id: str,
        visualization_callback: Optional[Callable] = None,
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
            results = self._classify_with_multithreading(
                image_graph, concepts, visualization_callback
            )
        else:
            results = self._classify_sequentially(
                image_graph, concepts, visualization_callback
            )

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
        visualization_callback: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._check_single_concept,
                    image_graph,
                    concept_id,
                    visualization_callback,
                ): concept_id
                for concept_id in concepts
            }

            for future in futures:
                try:
                    result = future.result(timeout=30)
                    if result.get("is_minor", False):
                        results.append(result)
                except Exception as e:
                    logging.error(f"Error checking concept minor: {str(e)}")

        return results

    def _classify_sequentially(
        self,
        image_graph: nx.Graph,
        concepts: List[str],
        visualization_callback: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for concept in concepts:
            try:
                result = self._check_single_concept(
                    image_graph,
                    concept,
                    visualization_callback,
                )
                if result.get("is_minor", False):
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
            if result.get("is_minor", False):
                filtered_results.append(result)
            # For partial matches, apply structural score threshold
            elif result.get("raw_structural_score", 0) >= self.min_structural_score:
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

        # Calculate activation levels with weighted components
        for result in filtered_results:
            # Normalize complexity
            normalized_complexity = (
                result.get("concept_complexity", 0) - min_complexity
            ) / complexity_range

            # Specificity score - higher when concept is more specific to the image
            normalized_specificity = (
                result.get("specificity", 0) - min_specificity
            ) / specificity_range

            # Raw structural score is already normalized
            structural_score = result.get("raw_structural_score", 0)

            # Combined activation with configurable weights
            activation = (
                self.activation_weights["complexity"] * normalized_complexity
                + self.activation_weights["structural"] * structural_score
                + self.activation_weights["specificity"] * normalized_specificity
            )

            result["activation_level"] = activation
            result["combined_score"] = activation

            # Add detailed scores for debugging
            result["normalized_complexity"] = normalized_complexity
            result["normalized_specificity"] = normalized_specificity

            logging.info(
                f"Scores for concept {result['concept_id']} and image {image_id}:\n"
                f"Structural: {structural_score:.4f}, "
                f"Complexity: {normalized_complexity:.4f}, "
                f"Specificity: {normalized_specificity:.4f}, "
                f"Activation: {activation:.4f}"
            )

        # Sort by activation level
        filtered_results.sort(
            key=lambda x: x.get("activation_level", 0),
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
