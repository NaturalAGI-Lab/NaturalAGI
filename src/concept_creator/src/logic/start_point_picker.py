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
    TYPE_PRIORITY = {
        CriticalPointType.INTERSECTION_POINT.value: 2,
        CriticalPointType.CORNER_POINT.value: 1,
    }

    def __init__(
        self, sample_graphs: List[nx.Graph], clustering_algorithm: str = "dbscan"
    ):
        if not sample_graphs:
            raise ValueError("Sample graphs list cannot be empty.")
        self.sample_graphs: List[nx.Graph] = list(sample_graphs)
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
        self.expected_start_degree: Optional[int] = None
        self.degree_map: Dict[tuple, int] = {}
        self._uuid_to_graph_index: Dict[uuid.UUID, int] = {}
        self._sample_start_nodes: Dict[int, Any] = {}

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
            self._uuid_to_graph_index[graph_id] = i
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
                    self.degree_map[(graph_id, node_id)] = graph.degree(node_id)
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
                clusterer = OPTICS(min_samples=max(min_samples, 2))
                labels = clusterer.fit_predict(coordinates)

        clusters = defaultdict(list)
        for point, label in zip(points, labels):
            if label != -1:  # Ignore noise points (applicable to DBSCAN and OPTICS)
                clusters[label].append(point)
        return clusters

    def _check_betti_guard(self) -> Optional[Tuple[str, np.ndarray]]:
        """If ≥90% of samples have B1≥2 and share a common cycle-intersection node,
        return (INTERSECTION_POINT, centroid) as the mandated characteristic."""
        if self.structure_type != "Closed":
            return None

        intersection_coords = []
        intersection_degrees = []
        samples_with_multi_cycle = 0

        for graph in self.sample_graphs:
            cycle_basis = nx.cycle_basis(graph)
            if len(cycle_basis) < 2:
                continue
            samples_with_multi_cycle += 1

            cycle_sets = [set(c) for c in cycle_basis]
            shared = cycle_sets[0].intersection(*cycle_sets[1:])
            if not shared:
                continue

            shared_node = next(iter(shared))
            data = graph.nodes[shared_node]
            norm_x = data.get("normalized_x")
            norm_y = data.get("normalized_y")
            if norm_x is not None and norm_y is not None:
                intersection_coords.append(np.array([norm_x, norm_y]))
                intersection_degrees.append(graph.degree(shared_node))

        if samples_with_multi_cycle < self.num_samples * 0.9:
            return None
        if len(intersection_coords) < self.num_samples * 0.9:
            return None

        centroid = np.mean(intersection_coords, axis=0)
        if intersection_degrees:
            self.expected_start_degree = Counter(intersection_degrees).most_common(1)[0][0]
        return (CriticalPointType.INTERSECTION_POINT.value, centroid)

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

    def _select_best_cluster(
        self, clusters: Dict[int, List[CriticalPoint]]
    ) -> Optional[List[CriticalPoint]]:
        """Select the best cluster using type priority (closed only), then spatial metric."""
        if not clusters:
            return None

        best_cluster_id = None
        best_priority = -1
        best_metric = float("inf")

        for cluster_id, points_in_cluster in clusters.items():
            dominant_label = Counter(
                p.label for p in points_in_cluster
            ).most_common(1)[0][0]

            priority = self.TYPE_PRIORITY.get(dominant_label, 0) if self.structure_type == "Closed" else 0
            avg_x = np.mean([p.norm_x for p in points_in_cluster])
            avg_y = np.mean([p.norm_y for p in points_in_cluster])
            metric = 2 * avg_x + avg_y

            if priority > best_priority or (priority == best_priority and metric < best_metric):
                best_priority = priority
                best_metric = metric
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
        betti_result = self._check_betti_guard()
        if betti_result is not None:
            self.start_point_characteristic = betti_result
            print(f"Betti guard: mandated IntersectionPoint start, centroid={betti_result[1]}")
            return

        if not self.all_critical_points:
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
        self.final_cluster_points = self._select_best_cluster(
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
            cluster_degrees = [
                self.degree_map.get((p.graph_id, p.node_id))
                for p in self.final_cluster_points
            ]
            cluster_degrees = [d for d in cluster_degrees if d is not None]
            if cluster_degrees:
                self.expected_start_degree = Counter(cluster_degrees).most_common(1)[0][0]

            graph_points: Dict[int, List[CriticalPoint]] = defaultdict(list)
            for p in self.final_cluster_points:
                graph_idx = self._uuid_to_graph_index[p.graph_id]
                graph_points[graph_idx].append(p)
            for graph_idx, points in graph_points.items():
                best = min(points, key=lambda p: np.linalg.norm(p.coordinates - centroid))
                self._sample_start_nodes[graph_idx] = best.node_id

            print(
                f"Determined start point characteristic: Label='{dominant_label}', Centroid={centroid}, ExpectedDegree={self.expected_start_degree}"
            )
        else:
            # Handle case where no cluster satisfies all criteria
            self.start_point_characteristic = None
            print(
                "Warning: No cluster satisfied all criteria for start point selection."
            )

    def get_start_point_characteristic(self) -> Optional[Tuple[str, np.ndarray]]:
        """Returns the determined start point characteristic.
        Format: (dominant_label, centroid)
        centroid: (x, y)
        """
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

        for i, sample_graph in enumerate(self.sample_graphs):
            if graph is sample_graph and i in self._sample_start_nodes:
                return self._sample_start_nodes[i]

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

        # Use projection onto centroid direction to find the most extreme
        # endpoint in the centroid's direction, rather than the closest by
        # Euclidean distance. This avoids selecting branch endpoints that
        # happen to sit closer to the centroid than true curve endpoints.
        centroid_norm = np.linalg.norm(centroid)
        if centroid_norm > 0:
            centroid_direction = centroid / centroid_norm
        else:
            centroid_direction = np.array([0.0, 0.0])

        node_type_map = {}
        candidates = []

        for node_id, data in graph.nodes(data=True):
            node_labels = data.get("labels", [])
            norm_x = data.get("normalized_x")
            norm_y = data.get("normalized_y")

            if norm_x is None or norm_y is None:
                continue

            if any(label in appropriate_labels for label in node_labels):
                node_coords = np.array([norm_x, norm_y])
                projection = np.dot(node_coords, centroid_direction)
                node_type = None
                for label_type in [
                    CriticalPointType.INTERSECTION_POINT.value,
                    CriticalPointType.CORNER_POINT.value,
                    CriticalPointType.END_POINT.value,
                    CriticalPointType.START_POINT.value,
                ]:
                    if label_type in node_labels:
                        node_type = label_type
                        break
                node_type_map[node_id] = node_type
                candidates.append((node_id, projection))

        if self.structure_type == "Closed":
            exp_deg = self.expected_start_degree
            candidates.sort(
                key=lambda x: (
                    self.TYPE_PRIORITY.get(node_type_map.get(x[0]), 0),
                    -abs(graph.degree(x[0]) - exp_deg) if exp_deg is not None else 0,
                    x[1],
                ),
                reverse=True,
            )
        else:
            candidates.sort(key=lambda x: x[1], reverse=True)

        if candidates:
            return candidates[0][0]

        # Fallback: find the most extreme critical point of any type
        fallback_candidates = []
        for node_id, data in graph.nodes(data=True):
            node_labels = data.get("labels", [])
            if any(label in self.critical_point_labels for label in node_labels):
                norm_x = data.get("normalized_x")
                norm_y = data.get("normalized_y")
                if norm_x is not None and norm_y is not None:
                    node_coords = np.array([norm_x, norm_y])
                    projection = np.dot(node_coords, centroid_direction)
                    fallback_candidates.append((node_id, projection))

        fallback_candidates.sort(key=lambda x: x[1], reverse=True)
        if fallback_candidates:
            print(
                f"Warning: No points with appropriate labels found. Using any critical point."
            )
            return fallback_candidates[0][0]

        print("Error: No suitable start point found in the graph")
        return None
