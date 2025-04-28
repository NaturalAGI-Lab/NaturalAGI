from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
from scipy.interpolate import interp1d
import uuid
import logging
from neo4j import ManagedTransaction
import networkx as nx

from .base_analyzer import BaseAnalyzer
from model.curve import Curve, CurveType
from model.point import Point, InflectionPoint
from model.vector import Vector


@dataclass
class CurveSegment:
    points: List[Point]
    vectors: List[Vector]
    curvature: np.ndarray
    curve_type: CurveType
    inflection_point: Optional[InflectionPoint] = None


class CurveAnalyzer(BaseAnalyzer):
    def __init__(self, graph: nx.Graph):
        super().__init__(graph)

    def analyze(self) -> List[Curve]:
        """Analyzes the graph to detect curves and their inflection points"""
        curves = []
        visited_vectors = set()

        # Start tracing from endpoints
        for node in self.graph.nodes():
            if self.graph.degree(node) == 1:
                curve_segment = self._trace_curve_segment(node, visited_vectors)
                if curve_segment:
                    curves.append(self._create_curve(curve_segment))

        logging.info(f"Detected {len(curves)} curves")
        return curves

    def _trace_curve_segment(self, start_node: str, visited_vectors: set) -> Optional[CurveSegment]:
        """Traces a curve segment starting from a given node until an inflection point or endpoint"""
        points = [self._create_point(start_node)]
        vectors = []
        current_node = start_node

        while True:
            # Get unvisited neighbors
            unvisited_edges = [
                (current_node, n) for n in self.graph.neighbors(current_node)
                if self.graph[current_node][n]["uuid"] not in visited_vectors
            ]

            if not unvisited_edges or self.graph.degree(current_node) != 2:
                break

            next_edge = unvisited_edges[0]
            vector = self._create_vector(next_edge)
            vectors.append(vector)
            visited_vectors.add(vector.id)

            current_node = next_edge[1]
            points.append(self._create_point(current_node))

        if len(vectors) < 2:
            return None

        return self._analyze_curve_segment(points, vectors)

    def _analyze_curve_segment(self, points: List[Point], vectors: List[Vector]) -> Optional[CurveSegment]:
        """Analyzes a sequence of points to determine curve type and find inflection points"""
        coords = np.array([(p.x, p.y) for p in points])
        
        # Fit curve and calculate curvature
        t = np.linspace(0, 1, len(coords))
        spline = interp1d(x=t, y=coords.T, kind='cubic')
        
        # Sample points for analysis
        t_sample = np.linspace(0, 1, 100)
        curve_points = spline(t_sample)
        
        # Calculate curvature
        dx = np.gradient(curve_points[0], t_sample)
        dy = np.gradient(curve_points[1], t_sample)
        d2x = np.gradient(dx, t_sample)
        d2y = np.gradient(dy, t_sample)
        curvature = (dx * d2y - dy * d2x) / (dx * dx + dy * dy) ** 1.5

        # Find inflection point
        inflection_indices = np.where(np.diff(np.signbit(curvature)))[0]
        if len(inflection_indices) > 0:
            idx = inflection_indices[0]
            inflection_point = self._create_inflection_point(
                points[idx], 
                curvature[idx-1], 
                curvature[idx+1]
            )
            points = points[:idx+1]
            vectors = vectors[:idx]
            curvature = curvature[:idx]

        # Determine curve type
        curve_type = self._determine_curve_type(curvature)
        if not curve_type:
            return None

        return CurveSegment(
            points=points,
            vectors=vectors,
            curvature=curvature,
            curve_type=curve_type,
            inflection_point=inflection_point if 'inflection_point' in locals() else None
        )

    def _determine_curve_type(self, curvature: np.ndarray) -> Optional[CurveType]:
        """Determines if curve is convex or concave based on curvature"""
        threshold = len(curvature) * 0.7
        pos_curv = np.sum(curvature > 0.01)
        neg_curv = np.sum(curvature < -0.01)
        
        if pos_curv > threshold:
            return CurveType.CONVEX
        elif neg_curv > threshold:
            return CurveType.CONCAVE
        return None

    def _create_curve(self, segment: CurveSegment) -> Curve:
        """Creates a Curve object from a CurveSegment"""
        return Curve(
            id=str(uuid.uuid4()),
            vectors=segment.vectors,
            type=segment.curve_type,
            start_point=segment.points[0],
            end_point=segment.inflection_point or segment.points[-1]
        )

    def _create_point(self, node_id: str) -> Point:
        """Creates a Point object from a graph node"""
        node_data = self.graph.nodes[node_id]
        return Point(
            x=node_data["x"],
            y=node_data["y"],
            id=node_data["uuid"],
            nx_id=node_id
        )

    def _create_vector(self, edge: Tuple[str, str]) -> Vector:
        """Creates a Vector object from a graph edge"""
        edge_data = self.graph[edge[0]][edge[1]]
        return Vector(
            id=edge_data["uuid"],
            x1=self.graph.nodes[edge[0]]["x"],
            y1=self.graph.nodes[edge[0]]["y"],
            x2=self.graph.nodes[edge[1]]["x"],
            y2=self.graph.nodes[edge[1]]["y"],
            length=edge_data.get("length", 0.0)
        )

    def _create_inflection_point(self, point: Point, curvature_before: float, curvature_after: float) -> InflectionPoint:
        """Creates an InflectionPoint object"""
        return InflectionPoint(
            x=point.x,
            y=point.y,
            id=point.id,
            nx_id=point.nx_id,
            curvature_before=curvature_before,
            curvature_after=curvature_after
        )

    def persist(
        self,
        mx: ManagedTransaction,
        session_id: str,
        image_id: str,
        curves: List[Curve],
    ) -> None:
        """Persists detected curves to Neo4j"""
        logging.info(f"Persisting curves: {curves}")
        query = """
            UNWIND $curves as curve
            MATCH (start:Point {id: curve.start_point, image_id: $image_id})
            MATCH (end:Point {id: curve.end_point, image_id: $image_id})
            CREATE (c:Curve:%s {
                id: curve.id,
                image_id: $image_id,
                session_id: $session_id
            })
            CREATE (start)-[:STARTS]->(c)
            CREATE (c)-[:ENDS]->(end)
            WITH c, curve
            UNWIND curve.vectors as vector_id
            MATCH (v:Vector {id: vector_id, image_id: $image_id})
            CREATE (c)-[:CONTAINS]->(v)
        """

        for curve_type in CurveType:
            type_curves = [c for c in curves if c.type == curve_type]
            if type_curves:
                mx.run(
                    query
                    % curve_type.value.capitalize(),  # Creates labels like :Curve:Convex or :Curve:Concave
                    curves=[
                        {
                            "id": c.id,
                            "start_point": c.start_point.id,
                            "end_point": c.end_point.id,
                            "vectors": [v.id for v in c.vectors],
                        }
                        for c in type_curves
                    ],
                    image_id=image_id,
                    session_id=session_id,
                )
