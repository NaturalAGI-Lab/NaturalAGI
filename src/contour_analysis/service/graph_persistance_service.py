import networkx as nx
from neo4j import GraphDatabase
from logic.point_extractor import PointExtractor
from typing import List
from model.curve import Curve, CurveType


class GraphPersistenceService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.point_extractor = None

    def save_graph_to_neo4j(
        self, graph: nx.Graph, image_id: str, session_id: str
    ) -> None:
        self.point_extractor = PointExtractor(graph)
        with self.driver.session() as session:
            session.write_transaction(self._save_graph, graph, image_id, session_id)

    def _save_graph(self, tx, graph: nx.Graph, image_id: str, session_id: str) -> None:
        # Extract all points
        all_points = self.point_extractor.extract_points()

        # Create a dictionary to map node ids to their point types
        point_types = {point.id: type(point).__name__ for point in all_points}

        # Create nodes
        for _, data in graph.nodes(data=True):
            labels = ["Point"]
            if data["uuid"] in point_types:
                labels.append(point_types[data["uuid"]])

            tx.run(
                f"""
                CREATE (n:{':'.join(labels)} {{id: $id, x: $x, y: $y, image_id: $image_id, session_id: $session_id}})
                """,
                id=data["uuid"],
                x=data["x"],
                y=data["y"],
                image_id=image_id,
                session_id=session_id,
            )

        # Create edges
        for u, v, data in graph.edges(data=True):
            u_data = graph.nodes[u]
            v_data = graph.nodes[v]
            vector_id = data["uuid"]

            # Calculate length
            dx = v_data["x"] - u_data["x"]
            dy = v_data["y"] - u_data["y"]
            length = (dx**2 + dy**2) ** 0.5

            tx.run(
                """
                MATCH (a:Point {id: $u, image_id: $image_id}), (b:Point {id: $v, image_id: $image_id})
                CREATE (v:Vector {
                    id: $vector_id,
                    x1: a.x, y1: a.y,
                    x2: b.x, y2: b.y,
                    length: $length,
                    image_id: $image_id,
                    session_id: $session_id
                })
                MERGE (a)-[:CONNECTED_TO]->(v)
                MERGE (v)<-[:CONNECTED_TO]-(b)            
                """,
                u=u_data["uuid"],
                v=v_data["uuid"],
                vector_id=vector_id,
                image_id=image_id,
                session_id=session_id,
                length=length,
            )

    def _save_curves(
        self, tx, curves: List[Curve], image_id: str, session_id: str
    ) -> None:
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
                tx.run(
                    query
                    % curve_type.value.capitalize(),  # Creates labels like :Curve:Convex or :Curve:Concave
                    curves=[
                        {
                            "id": c.id,
                            "start_point": c.start_point,
                            "end_point": c.end_point,
                            "vectors": c.vectors,
                        }
                        for c in type_curves
                    ],
                    image_id=image_id,
                    session_id=session_id,
                )

    def close(self):
        self.driver.close()
