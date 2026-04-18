import math
import logging
from itertools import combinations
from typing import Any

import networkx as nx
from neo4j import ManagedTransaction

from common.feature_scales import h_k

from .base_analyzer import BaseAnalyzer

logging.basicConfig(level=logging.INFO)

MIN_CORNER_ANGLE = 160


class StructuralFeatureAnalyzer(BaseAnalyzer):
    """Computes structural features on the pre-persistence Point-only NetworkX graph.

    All numeric outputs are passed through h_k (Parzhyn formula 36) so Neo4j stores
    internal energy u_k ∈ [0, 1], not raw k. Categorical/binary flags are identity.
    Point features: node_degree, raw_node_degree (scratch for tertiary phase),
        is_endpoint/junction/corner/on_cycle, distance_to_centroid,
        junction_angle_min/max/mean, avg_neighbor_vector_length,
        betweenness/closeness_centrality, eccentricity, pagerank.
    Edge features (on Vector nodes): tortuosity, normalized_length,
        length_ratio_to_max, branch_type, connects_cycle_nodes.
    """

    def analyze(self) -> dict[str, dict]:
        node_types = self._classify_all_nodes()
        cx, cy = self._compute_centroid()
        max_dist = self._compute_max_centroid_distance(cx, cy)
        cycle_nodes = self._compute_cycle_nodes()
        centralities = self._compute_centralities()
        total_length, max_length = self._compute_length_aggregates()

        point_features = {}
        for node in self.graph.nodes():
            data = self.graph.nodes[node]
            degree = self.graph.degree(node)
            ntype = node_types[node]

            features: dict[str, Any] = {
                "node_degree": h_k("node_degree", degree),
                "raw_node_degree": degree,
                "is_endpoint": 1 if ntype == "E" else 0,
                "is_junction": 1 if ntype == "J" else 0,
                "is_corner": 1 if ntype == "C" else 0,
                "is_on_cycle": 1 if node in cycle_nodes else 0,
                "distance_to_centroid": h_k(
                    "distance_to_centroid",
                    self._normalized_distance(data["x"], data["y"], cx, cy, max_dist),
                ),
                "avg_neighbor_vector_length": h_k(
                    "avg_neighbor_vector_length", self._avg_neighbor_length(node)
                ),
            }

            angle_min, angle_max, angle_mean = self._junction_angles(node)
            if angle_min is not None:
                features["junction_angle_min"] = h_k("junction_angle_min", angle_min)
                features["junction_angle_max"] = h_k("junction_angle_max", angle_max)
                features["junction_angle_mean"] = h_k("junction_angle_mean", angle_mean)

            for key in ("betweenness_centrality", "closeness_centrality",
                        "eccentricity", "pagerank"):
                val = centralities.get(key, {}).get(node)
                if val is not None:
                    features[key] = round(h_k(key, val), 6)

            point_features[node] = features

        edge_features = {}
        for u, v, data in self.graph.edges(data=True):
            edge_id = data.get("id")
            if edge_id is None:
                logging.warning("Edge (%s, %s) missing 'id' attribute, skipping", u, v)
                continue

            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]
            euclidean = math.hypot(u_data["x"] - v_data["x"], u_data["y"] - v_data["y"])
            length = data.get("length", euclidean)

            raw_tortuosity = length / euclidean if euclidean > 1e-9 else 1.0
            raw_norm_length = length / total_length if total_length > 0 else 0.0
            raw_length_ratio = length / max_length if max_length > 0 else 0.0
            edge_features[edge_id] = {
                "tortuosity": round(h_k("tortuosity", raw_tortuosity), 4),
                "normalized_length": round(h_k("normalized_length", raw_norm_length), 4),
                "length_ratio_to_max": round(h_k("length_ratio_to_max", raw_length_ratio), 4),
                "branch_type": self._branch_type(node_types[u], node_types[v]),
                "connects_cycle_nodes": 1 if (u in cycle_nodes and v in cycle_nodes) else 0,
            }

        return {"point_features": point_features, "edge_features": edge_features}

    def persist(
        self, mx: ManagedTransaction, session_id: str, image_id: str, result: dict
    ) -> None:
        point_rows = [
            {"id": node_id, "props": {k: v for k, v in feats.items() if v is not None}}
            for node_id, feats in result["point_features"].items()
        ]
        if point_rows:
            mx.run(
                """
                UNWIND $rows AS r
                MATCH (n:Point {id: r.id, image_id: $image_id})
                SET n += r.props
                """,
                rows=point_rows,
                image_id=image_id,
            )

        edge_rows = [
            {"id": edge_id, "props": {k: v for k, v in feats.items() if v is not None}}
            for edge_id, feats in result["edge_features"].items()
        ]
        if edge_rows:
            mx.run(
                """
                UNWIND $rows AS r
                MATCH (n:Vector {id: r.id, image_id: $image_id})
                SET n += r.props
                """,
                rows=edge_rows,
                image_id=image_id,
            )

        self._persist_vector_centralities(mx, image_id)

    def _persist_vector_centralities(self, mx: ManagedTransaction, image_id: str):
        mx.run("""
            MATCH (p1:Point {image_id: $image_id})-[:CONNECTED_TO]->(v:Vector {image_id: $image_id})
                  <-[:CONNECTED_TO]-(p2:Point {image_id: $image_id})
            WHERE p1 <> p2
              AND p1.betweenness_centrality IS NOT NULL
              AND p2.betweenness_centrality IS NOT NULL
              AND p1.closeness_centrality IS NOT NULL
              AND p2.closeness_centrality IS NOT NULL
              AND p1.pagerank IS NOT NULL
              AND p2.pagerank IS NOT NULL
            SET v.betweenness_centrality = round(
                    (p1.betweenness_centrality + p2.betweenness_centrality) / 2.0 * 1000000
                ) / 1000000,
                v.closeness_centrality = round(
                    (p1.closeness_centrality + p2.closeness_centrality) / 2.0 * 1000000
                ) / 1000000,
                v.pagerank = round(
                    (p1.pagerank + p2.pagerank) / 2.0 * 1000000
                ) / 1000000
        """, image_id=image_id)

        mx.run("""
            MATCH (p1:Point {image_id: $image_id})-[:CONNECTED_TO]->(v:Vector {image_id: $image_id})
                  <-[:CONNECTED_TO]-(p2:Point {image_id: $image_id})
            WHERE p1 <> p2
              AND p1.eccentricity IS NOT NULL
              AND p2.eccentricity IS NOT NULL
            SET v.eccentricity = round(
                    (p1.eccentricity + p2.eccentricity) / 2.0 * 1000000
                ) / 1000000
        """, image_id=image_id)

    # ── helpers ──────────────────────────────────────────────────────────

    def _classify_all_nodes(self) -> dict[str, str]:
        types = {}
        for node in self.graph.nodes():
            degree = self.graph.degree(node)
            if degree == 1:
                types[node] = "E"
            elif degree > 2:
                types[node] = "J"
            elif degree == 2:
                neighbors = list(self.graph.neighbors(node))
                angle = self._angle_between(node, neighbors[0], neighbors[1])
                types[node] = "C" if angle < MIN_CORNER_ANGLE else "P"
            else:
                types[node] = "P"
        return types

    def _compute_centroid(self) -> tuple[float, float]:
        xs, ys = [], []
        for _, data in self.graph.nodes(data=True):
            xs.append(data["x"])
            ys.append(data["y"])
        if not xs:
            return 0.0, 0.0
        return sum(xs) / len(xs), sum(ys) / len(ys)

    def _compute_max_centroid_distance(self, cx: float, cy: float) -> float:
        max_d = 0.0
        for _, data in self.graph.nodes(data=True):
            d = math.hypot(data["x"] - cx, data["y"] - cy)
            if d > max_d:
                max_d = d
        return max_d

    @staticmethod
    def _normalized_distance(
        x: float, y: float, cx: float, cy: float, max_dist: float
    ) -> float:
        if max_dist < 1e-9:
            return 0.0
        return round(math.hypot(x - cx, y - cy) / max_dist, 4)

    def _compute_cycle_nodes(self) -> set:
        try:
            cycles = nx.cycle_basis(self.graph)
            nodes = set()
            for cycle in cycles:
                nodes.update(cycle)
            return nodes
        except nx.NetworkXError:
            return set()

    def _compute_centralities(self) -> dict[str, dict]:
        result: dict[str, dict] = {
            "betweenness_centrality": nx.betweenness_centrality(self.graph),
            "closeness_centrality": nx.closeness_centrality(self.graph),
            "pagerank": nx.pagerank(self.graph),
        }
        if nx.is_connected(self.graph):
            result["eccentricity"] = nx.eccentricity(self.graph)
        else:
            result["eccentricity"] = {}
        return result

    def _compute_length_aggregates(self) -> tuple[float, float]:
        lengths = [
            data.get("length", 0.0)
            for _, _, data in self.graph.edges(data=True)
        ]
        if not lengths:
            return 0.0, 0.0
        return sum(lengths), max(lengths)

    def _avg_neighbor_length(self, node) -> float:
        lengths = []
        for neighbor in self.graph.neighbors(node):
            edge_data = self.graph.get_edge_data(node, neighbor)
            if edge_data and "length" in edge_data:
                lengths.append(edge_data["length"])
        if not lengths:
            return 0.0
        return round(sum(lengths) / len(lengths), 2)

    def _junction_angles(self, node) -> tuple[float | None, float | None, float | None]:
        neighbors = list(self.graph.neighbors(node))
        if len(neighbors) < 2:
            return None, None, None
        angles = []
        for n1, n2 in combinations(neighbors, 2):
            angles.append(self._angle_between(node, n1, n2))
        if not angles:
            return None, None, None
        return round(min(angles), 1), round(max(angles), 1), round(sum(angles) / len(angles), 1)

    def _angle_between(self, center, n1, n2) -> float:
        cd = self.graph.nodes[center]
        d1 = self.graph.nodes[n1]
        d2 = self.graph.nodes[n2]
        v1 = (d1["x"] - cd["x"], d1["y"] - cd["y"])
        v2 = (d2["x"] - cd["x"], d2["y"] - cd["y"])
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        m1 = math.hypot(*v1)
        m2 = math.hypot(*v2)
        if m1 < 1e-10 or m2 < 1e-10:
            return 0.0
        cos_a = max(-1.0, min(1.0, dot / (m1 * m2)))
        return math.degrees(math.acos(cos_a))

    @staticmethod
    def _branch_type(type_u: str, type_v: str) -> int:
        pair = frozenset((type_u, type_v))
        mapping = {
            frozenset(("J", "J")): 1,
            frozenset(("J", "E")): 2,
            frozenset(("J", "C")): 3,
            frozenset(("E", "E")): 4,
            frozenset(("E", "C")): 5,
            frozenset(("C", "C")): 6,
        }
        return mapping.get(pair, 0)
