import logging
import networkx as nx
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor

from graph_similarity.neo4j_to_networkx import Neo4jToNetworkX

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
    ):
        self.neo4j_dsn = neo4j_dsn
        self.neo4j_user = neo4j_user
        self.neo4j_pass = neo4j_pass
        self.driver = GraphDatabase.driver(
            neo4j_dsn, auth=(neo4j_user, neo4j_pass), max_connection_lifetime=200
        )
        self.max_workers = max_workers
        self.use_multithreading = use_multithreading

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
        """
        Check if the concept is a minor of the image graph without removing properties.
        Start matching from StartPoint nodes and try to find a mapping that preserves
        all concept node properties.
        """
        concept_graph = Neo4jToNetworkX.extract_concept_graph(tx, concept_id)

        # Calculate complexity metrics for ranking
        concept_complexity = len(concept_graph.nodes) + len(concept_graph.edges)

        # Get all StartPoint nodes from both graphs
        concept_start_points = [
            node
            for node, attrs in concept_graph.nodes(data=True)
            if "labels" in attrs and "StartPoint" in attrs["labels"]
        ]

        image_start_points = [
            node
            for node, attrs in image_graph.nodes(data=True)
            if "labels" in attrs and "StartPoint" in attrs["labels"]
        ]

        # Initialize result with no match
        result = {
            "concept_id": concept_id,
            "concept_name": concept_id,
            "session_id": concept_id,
            "raw_structural_score": 0.0,
            "is_minor": False,
            "concept_complexity": concept_complexity,
            "comparison_message": f"No match found for concept {concept_id}",
        }

        # If concept has no StartPoints or image has no StartPoints, early return
        if not concept_start_points or not image_start_points:
            result["comparison_message"] = (
                f"Cannot match concept {concept_id}: "
                f"Concept has {len(concept_start_points)} StartPoints, "
                f"Image has {len(image_start_points)} StartPoints"
            )
            return result

        # Try all possible StartPoint matchings
        for concept_start in concept_start_points:
            for image_start in image_start_points:
                # Check if StartPoints have compatible properties
                if not self._check_node_properties_match(
                    concept_graph.nodes[concept_start], image_graph.nodes[image_start]
                ):
                    continue

                # Try to find a complete matching starting from these points
                matching = self._find_concept_minor_mapping(
                    concept_graph,
                    image_graph,
                    {concept_start: image_start},
                    visualization_callback,
                )

                # If we found a complete matching, this is a minor
                if matching and len(matching) == len(concept_graph.nodes):
                    structural_similarity = 1.0
                    result = {
                        "concept_id": concept_id,
                        "concept_name": concept_id,
                        "session_id": concept_id,
                        "raw_structural_score": structural_similarity,
                        "is_minor": True,
                        "mapping_size": len(matching),
                        "concept_size": len(concept_graph.nodes),
                        "image_size": len(image_graph.nodes),
                        "comparison_message": (
                            f"Concept {concept_id} is a minor of the image graph "
                            f"with a complete matching of {len(matching)} nodes"
                        ),
                        "concept_complexity": concept_complexity,
                    }
                    return result

                # If we found a partial matching, update result if it's better
                elif matching and len(matching) > 0:
                    partial_similarity = len(matching) / len(concept_graph.nodes)
                    if partial_similarity > result.get("raw_structural_score", 0):
                        result = {
                            "concept_id": concept_id,
                            "concept_name": concept_id,
                            "session_id": concept_id,
                            "raw_structural_score": partial_similarity,
                            "is_minor": False,
                            "mapping_size": len(matching),
                            "concept_size": len(concept_graph.nodes),
                            "image_size": len(image_graph.nodes),
                            "comparison_message": (
                                f"Partial matching for concept {concept_id} with "
                                f"{len(matching)}/{len(concept_graph.nodes)} nodes matched "
                                f"({partial_similarity:.2%})"
                            ),
                            "concept_complexity": concept_complexity,
                        }

        return result

    def _check_node_properties_match(
        self, concept_node_data: Dict[str, Any], image_node_data: Dict[str, Any]
    ) -> bool:
        """
        Check if the concept node properties are a subset of the image node properties.
        For labels, check if all concept node labels are in the image node labels.
        For other properties, check if they have the same value.
        """
        # Check labels first
        if "labels" in concept_node_data:
            concept_labels = set(concept_node_data["labels"])
            image_labels = set(image_node_data.get("labels", []))

            # All concept labels must be in the image labels
            if not concept_labels.issubset(image_labels):
                return False

        # Check other properties
        for key, value in concept_node_data.items():
            if key != "labels" and key != "visualization":
                # If property exists in concept but not in image or values don't match
                if key not in image_node_data or image_node_data[key] != value:
                    return False

        return True

    def _find_concept_minor_mapping(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        initial_mapping: Dict[Any, Any],
        visualization_callback: Optional[Callable] = None,
    ) -> Dict[Any, Any]:
        """
        Try to find a mapping from concept nodes to image nodes that preserves
        the structure and all properties of the concept graph.

        Starting from the initial mapping (usually StartPoints), grow the mapping
        by traversing both graphs in parallel, ensuring that properties match
        and the structure is preserved.
        """
        # Initialize with provided mapping
        mapping = initial_mapping.copy()
        inverse_mapping = {v: k for k, v in mapping.items()}

        # Keep track of frontier nodes to explore
        concept_frontier = set()
        for concept_node in mapping:
            concept_frontier.update(concept_graph.neighbors(concept_node))

        # Remove already mapped nodes from frontier
        concept_frontier = concept_frontier - set(mapping.keys())

        # Iteratively grow the mapping
        while concept_frontier:
            # Try to find the best mapping for a frontier node
            found_match = False
            for concept_node in list(concept_frontier):
                # Get all mapped neighbors of this concept node
                mapped_neighbors = [
                    n for n in concept_graph.neighbors(concept_node) if n in mapping
                ]

                if not mapped_neighbors:
                    continue

                # Get corresponding image nodes of mapped neighbors
                image_neighbors_of_mapped = set()
                for concept_neighbor in mapped_neighbors:
                    image_neighbor = mapping[concept_neighbor]
                    image_neighbors_of_mapped.update(
                        image_graph.neighbors(image_neighbor)
                    )

                # Remove already mapped image nodes
                image_candidates = image_neighbors_of_mapped - set(
                    inverse_mapping.keys()
                )

                # Try to find a matching image node
                for image_node in image_candidates:
                    # Check if image node has compatible properties with concept node
                    if not self._check_node_properties_match(
                        concept_graph.nodes[concept_node], image_graph.nodes[image_node]
                    ):
                        continue

                    # Check structural compatibility - all mapped neighbors of concept_node
                    # must be neighbors of image_node in the image graph
                    is_structurally_compatible = True
                    for concept_neighbor in mapped_neighbors:
                        image_neighbor = mapping[concept_neighbor]
                        if not image_graph.has_edge(image_node, image_neighbor):
                            is_structurally_compatible = False
                            break

                    if is_structurally_compatible:
                        # We found a match for this concept node
                        mapping[concept_node] = image_node
                        inverse_mapping[image_node] = concept_node
                        concept_frontier.remove(concept_node)

                        # Add new frontier nodes
                        for new_neighbor in concept_graph.neighbors(concept_node):
                            if (
                                new_neighbor not in mapping
                                and new_neighbor not in concept_frontier
                            ):
                                concept_frontier.add(new_neighbor)

                        found_match = True
                        break

                if found_match:
                    break

            # If we couldn't find any match in this iteration, we're stuck
            if not found_match:
                break

        # If visualization callback is provided, visualize the final mapping
        if visualization_callback:
            # Deep copy graphs to avoid modifying the originals
            concept_copy = concept_graph.copy()
            image_copy = image_graph.copy()

            # Highlight matched nodes
            for concept_node, image_node in mapping.items():
                if "visualization" not in concept_copy.nodes[concept_node]:
                    concept_copy.nodes[concept_node]["visualization"] = {}
                if "visualization" not in image_copy.nodes[image_node]:
                    image_copy.nodes[image_node]["visualization"] = {}

                concept_copy.nodes[concept_node]["visualization"]["highlight"] = True
                concept_copy.nodes[concept_node]["visualization"][
                    "matched_to"
                ] = image_node
                image_copy.nodes[image_node]["visualization"]["highlight"] = True
                image_copy.nodes[image_node]["visualization"][
                    "matched_to"
                ] = concept_node

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

        return mapping

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
    ) -> List[Dict[str, Any]]:
        """
        Classify an image by checking if it contains any concepts as minors.
        Returns a sorted list of concepts with activation levels.
        The most complex activated concept receives the highest activation.
        """
        logging.info(f"Classifying image {image_id} using concept minor approach")

        with self.driver.session() as session:
            concepts = session.execute_read(self._get_all_concepts)
            image_graph = session.execute_read(
                Neo4jToNetworkX.extract_image_graph, image_id
            )

        results = []

        if self.use_multithreading:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_concept = {
                    executor.submit(
                        self._check_single_concept,
                        image_graph,
                        concept_id,
                        visualization_callback,
                    ): concept_id
                    for concept_id in concepts
                }

                for future in future_to_concept:
                    try:
                        result = future.result(timeout=30)
                        # Only include results where the concept is confirmed as a minor
                        if result.get("is_minor", False):
                            results.append(result)
                    except Exception as e:
                        logging.error(f"Error checking concept minor: {str(e)}")
        else:
            # Sequential processing
            for concept in concepts:
                try:
                    result = self._check_single_concept(
                        image_graph,
                        concept,
                        visualization_callback,
                    )
                    # Only include results where the concept is confirmed as a minor
                    if result.get("is_minor", False):
                        results.append(result)
                except Exception as e:
                    logging.error(f"Error checking concept minor: {str(e)}")

        # Calculate activation levels based on complexity for true minors
        if results:
            # Normalize activation levels to [0, 1] range
            max_complexity = max(r.get("concept_complexity", 0) for r in results)
            min_complexity = min(r.get("concept_complexity", 0) for r in results)

            # Avoid division by zero if all concepts have the same complexity
            complexity_range = max(1, max_complexity - min_complexity)

            for result in results:
                # Scale complexity to [0, 1]
                normalized_complexity = (
                    result.get("concept_complexity", 0) - min_complexity
                ) / complexity_range

                # For true minors, activation is primarily based on complexity
                # with a small contribution from structural score for tiebreaking
                activation = (
                    0.9 * normalized_complexity + 0.1 * result["raw_structural_score"]
                )

                result["activation_level"] = activation
                result["combined_score"] = (
                    activation  # For compatibility with existing code
                )

                logging.info(
                    f"Scores for concept {result['concept_id']} and image {image_id}:\n"
                    f"Structural: {result['raw_structural_score']:.4f}, "
                    f"Is Minor: {result.get('is_minor', True)}, "  # This will always be True now
                    f"Complexity: {result.get('concept_complexity', 0)}, "
                    f"Activation: {activation:.4f}"
                )

        # Sort by activation level in descending order
        results.sort(
            key=lambda x: x.get("activation_level", 0),
            reverse=True,
        )

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
