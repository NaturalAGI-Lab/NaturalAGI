# Standard library imports
import uuid
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

# Third-party imports
import networkx as nx
import numpy as np
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans, OPTICS

# Local imports
from common.critical_point import CriticalPoint, CriticalPointType


class StartPointPicker:
    def __init__(
        self, sample_graphs: List[nx.Graph], clustering_algorithm: str = "dbscan"
    ):
        if not sample_graphs:
            raise ValueError("Sample graphs list cannot be empty.")
        self.sample_graphs: List[nx.Graph] = sample_graphs
        self.num_samples: int = len(sample_graphs)
        self.start_point_characteristic: Optional[Tuple[str, np.ndarray]] = None
        self.critical_point_labels: Set[str] = {
            CriticalPointType.END_POINT.value,
            CriticalPointType.CORNER_POINT.value,
            CriticalPointType.INTERSECTION_POINT.value,
            CriticalPointType.START_POINT.value,
        }
        self.all_critical_points: List[CriticalPoint] = []
        self.clusters: Dict[int, List[CriticalPoint]] = {}
        self.valid_clusters: Dict[int, List[CriticalPoint]] = {}
        self.final_cluster_points: Optional[List[CriticalPoint]] = None

        # Set the clustering algorithm
        self.clustering_algorithm = clustering_algorithm.lower()
        self._validate_clustering_algorithm()
        self.structure_type = self._determine_structure_type()
        self.all_critical_points = self._extract_critical_points(self.structure_type)

    def _validate_clustering_algorithm(self):
        valid_algorithms = ["dbscan", "kmeans", "agglomerative", "optics"]
        if self.clustering_algorithm not in valid_algorithms:
            raise ValueError(
                f"Invalid clustering algorithm. Choose from: {', '.join(valid_algorithms)}"
            )

    def _extract_critical_points(self, structure_type: str) -> List[CriticalPoint]:
        critical_points = []
        for i, graph in enumerate(self.sample_graphs):
            graph_id = uuid.uuid4()
            for node_id, data in graph.nodes(data=True):
                node_labels = data.get("labels", [])
                is_critical = any(
                    label in self.critical_point_labels for label in node_labels
                )
                if structure_type == "Open":
                    is_critical = is_critical and any(
                        label
                        in [
                            CriticalPointType.END_POINT.value,
                            CriticalPointType.START_POINT.value,
                        ]
                        for label in node_labels
                    )
                elif structure_type == "Closed":
                    is_critical = is_critical and any(
                        label
                        in [
                            CriticalPointType.START_POINT.value,
                            CriticalPointType.CORNER_POINT.value,
                            CriticalPointType.INTERSECTION_POINT.value,
                        ]
                        for label in node_labels
                    )
                norm_x = data.get("normalized_x")
                norm_y = data.get("normalized_y")

                if is_critical and norm_x is not None and norm_y is not None:
                    # Use the most specific critical point label
                    # Priority: END_POINT > INTERSECTION_POINT > CORNER_POINT > START_POINT
                    critical_label = None
                    for label_type in [
                        CriticalPointType.END_POINT.value,
                        CriticalPointType.INTERSECTION_POINT.value,
                        CriticalPointType.CORNER_POINT.value,
                        CriticalPointType.START_POINT.value,
                    ]:
                        if label_type in node_labels:
                            critical_label = label_type
                            break

                    critical_points.append(
                        CriticalPoint(graph_id, node_id, critical_label, norm_x, norm_y)
                    )
        return critical_points

    def _cluster_points(
        self,
        points: List[CriticalPoint],
        eps: float = 0.1,
        min_samples: int = 2,
        n_clusters: int = 8,
    ) -> Dict[int, List[CriticalPoint]]:
        if not points:
            return {}

        coordinates = np.array([p.coordinates for p in points])

        # Handle case with very few points where clustering might fail or be meaningless
        if len(points) <= 1:
            # Assign all points to a single cluster (e.g., cluster 0)
            labels = np.zeros(len(points), dtype=int)
        else:
            # Apply the selected clustering algorithm
            if self.clustering_algorithm == "dbscan":
                # Ensure min_samples is not greater than the number of points
                actual_min_samples = min(min_samples, len(points))
                if actual_min_samples < 1:
                    actual_min_samples = 1  # DBSCAN min_samples must be >= 1

                # Perform DBSCAN clustering
                clusterer = DBSCAN(eps=eps, min_samples=actual_min_samples)
                labels = clusterer.fit_predict(coordinates)

            elif self.clustering_algorithm == "kmeans":
                # Ensure n_clusters is not greater than the number of points
                actual_n_clusters = min(n_clusters, len(points))
                # Perform KMeans clustering
                clusterer = KMeans(n_clusters=actual_n_clusters, random_state=42)
                labels = clusterer.fit_predict(coordinates)

            elif self.clustering_algorithm == "agglomerative":
                # Ensure n_clusters is not greater than the number of points
                actual_n_clusters = min(n_clusters, len(points))
                # Perform Agglomerative clustering
                clusterer = AgglomerativeClustering(n_clusters=actual_n_clusters)
                labels = clusterer.fit_predict(coordinates)

            elif self.clustering_algorithm == "optics":
                # Perform OPTICS clustering
                clusterer = OPTICS(min_samples=min_samples)
                labels = clusterer.fit_predict(coordinates)

        clusters = defaultdict(list)
        for point, label in zip(points, labels):
            if label != -1:  # Ignore noise points (applicable to DBSCAN and OPTICS)
                clusters[label].append(point)
        return clusters

    def _determine_structure_type(self) -> str:
        has_endpoint = True
        for graph in self.sample_graphs:
            has_endpoint_in_graph = False
            for node_id in graph.nodes:
                if nx.degree(graph, node_id) == 1:
                    has_endpoint_in_graph = True
                    break
            if not has_endpoint_in_graph:
                has_endpoint = False
                break
        return "Open" if has_endpoint else "Closed"

    def _filter_clusters_by_type_and_representation(
        self, clusters: Dict[int, List[CriticalPoint]], structure_type: str
    ) -> Dict[int, List[CriticalPoint]]:

        self.valid_clusters = {}

        for cluster_id, points_in_cluster in clusters.items():
            if not points_in_cluster:
                continue

            # Check representation across samples
            represented_graph_ids = {p.graph_id for p in points_in_cluster}
            if len(represented_graph_ids) >= self.num_samples * 0.9:
                self.valid_clusters[cluster_id] = points_in_cluster
            else:
                print(
                    f"cluster_id: {cluster_id} has {len(represented_graph_ids)} samples, expected {self.num_samples * 0.9}"
                )

        return self.valid_clusters

    def _select_top_leftmost_cluster(
        self, clusters: Dict[int, List[CriticalPoint]]
    ) -> Optional[List[CriticalPoint]]:
        if not clusters:
            return None

        min_metric = float("inf")
        best_cluster_id = -1

        for cluster_id, points_in_cluster in clusters.items():
            avg_x = np.mean([p.norm_x for p in points_in_cluster])
            avg_y = np.mean([p.norm_y for p in points_in_cluster])
            metric = 2 * avg_x + avg_y

            if metric < min_metric:
                min_metric = metric
                best_cluster_id = cluster_id

        return clusters.get(best_cluster_id)

    def determine_start_point_characteristic(
        self,
        clustering_eps: float = 0.1,
        clustering_min_samples: int = 2,
        n_clusters: int = 8,
    ):
        """
        Analyzes the sample graphs to determine the optimal starting point characteristic.
        Stores the result (dominant label, centroid coordinates) in self.start_point_characteristic.

        Args:
            clustering_eps: Epsilon parameter for DBSCAN and OPTICS algorithms
            clustering_min_samples: Min samples parameter for DBSCAN and OPTICS algorithms
            n_clusters: Number of clusters for KMeans and Agglomerative algorithms
        """
        if not self.all_critical_points:
            # Handle case with no critical points found
            self.start_point_characteristic = None
            print("Warning: No critical points found in sample graphs.")
            return

        self.clusters = self._cluster_points(
            self.all_critical_points,
            eps=clustering_eps,
            min_samples=clustering_min_samples,
            n_clusters=n_clusters,
        )
        print(f"self.clusters: {len(self.clusters) if self.clusters else 0}")
        if not self.clusters:
            # Handle case where clustering yields no valid clusters
            self.start_point_characteristic = None
            print("Warning: Clustering did not produce any valid clusters.")
            return

        candidate_clusters = self._filter_clusters_by_type_and_representation(
            self.clusters, self.structure_type
        )
        print(
            f"candidate_clusters: {len(candidate_clusters) if candidate_clusters else 0}"
        )
        self.final_cluster_points = self._select_top_leftmost_cluster(
            candidate_clusters
        )
        print(
            f"self.final_cluster_points: {len(self.final_cluster_points) if self.final_cluster_points else 0}"
        )
        if self.final_cluster_points:
            centroid = np.mean(
                [p.coordinates for p in self.final_cluster_points], axis=0
            )
            dominant_label = Counter(
                p.label for p in self.final_cluster_points
            ).most_common(1)[0][0]
            self.start_point_characteristic = (dominant_label, centroid)
            print(
                f"Determined start point characteristic: Label='{dominant_label}', Centroid={centroid}"
            )
        else:
            # Handle case where no cluster satisfies all criteria
            self.start_point_characteristic = None
            print(
                "Warning: No cluster satisfied all criteria for start point selection."
            )

    def get_start_point_characteristic(self) -> Optional[Tuple[str, np.ndarray]]:
        """Returns the determined start point characteristic."""
        if self.start_point_characteristic is None:
            # Optionally run determination if not already done, or raise error/warning
            print(
                "Start point characteristic not determined yet. Call determine_start_point_characteristic first."
            )
        return self.start_point_characteristic

    def get_start_point_for_graph(self, graph: nx.Graph) -> Optional[Any]:
        """
        Returns the node_id of the most appropriate starting point in the given graph.
        Simply finds the closest point of the appropriate type to the characteristic centroid.

        For open contours: Uses StartPoint or EndPoint
        For closed contours: Uses CornerPoint or IntersectionPoint

        Args:
            graph: The graph to analyze

        Returns:
            The node_id of the selected start point or None if no suitable point found
        """
        if self.start_point_characteristic is None:
            print("Warning: Start point characteristic not determined yet.")
            return None

        _, centroid = self.start_point_characteristic
        structure_type = self._determine_structure_type()

        # Define appropriate labels based on structure type
        appropriate_labels = []
        if structure_type == "Open":
            appropriate_labels = [
                CriticalPointType.END_POINT.value,
                CriticalPointType.START_POINT.value,
            ]
        else:  # Closed structure
            appropriate_labels = [
                CriticalPointType.CORNER_POINT.value,
                CriticalPointType.INTERSECTION_POINT.value,
            ]

        # Find the closest point of the appropriate type
        candidates = []

        for node_id, data in graph.nodes(data=True):
            node_labels = data.get("labels", [])
            norm_x = data.get("normalized_x")
            norm_y = data.get("normalized_y")

            if norm_x is None or norm_y is None:
                continue

            # Check if node has any of the appropriate labels for this structure type
            if any(label in appropriate_labels for label in node_labels):
                # Calculate distance to centroid
                node_coords = np.array([norm_x, norm_y])
                distance = np.linalg.norm(node_coords - centroid)
                candidates.append((node_id, distance))

        # Sort by distance (closest first)
        candidates.sort(key=lambda x: x[1])

        # Return the closest appropriate point
        if candidates:
            return candidates[0][0]

        # Fallback: just find the closest critical point of any type
        fallback_candidates = []
        for node_id, data in graph.nodes(data=True):
            node_labels = data.get("labels", [])
            if any(label in self.critical_point_labels for label in node_labels):
                norm_x = data.get("normalized_x")
                norm_y = data.get("normalized_y")
                if norm_x is not None and norm_y is not None:
                    node_coords = np.array([norm_x, norm_y])
                    distance = np.linalg.norm(node_coords - centroid)
                    fallback_candidates.append((node_id, distance))

        fallback_candidates.sort(key=lambda x: x[1])
        if fallback_candidates:
            print(
                f"Warning: No points with appropriate labels found. Using any critical point."
            )
            return fallback_candidates[0][0]

        print("Error: No suitable start point found in the graph.")
        return None
