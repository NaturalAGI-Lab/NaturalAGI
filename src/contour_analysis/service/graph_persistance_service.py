import networkx as nx
from neo4j import GraphDatabase
from logic.point_extractor import PointExtractor
import logging


class GraphPersistenceService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.point_extractor = None
        self.logger = logging.getLogger(__name__)

    def save_graph_to_neo4j(
        self, graph: nx.Graph, image_id: str, session_id: str
    ) -> None:
        self.point_extractor = PointExtractor(graph)
        with self.driver.session() as session:
            session.write_transaction(self._save_graph, graph, image_id, session_id)

    def _save_graph(self, tx, graph: nx.Graph, image_id: str, session_id: str) -> None:
        # Extract all points
        self.logger.info(
            f"Extracting points for image {image_id} and session {session_id}"
        )
        all_points = self.point_extractor.extract_points()
        self.logger.info(f"Extracted {len(all_points)} points")
        self.logger.info(f"Points: {all_points}")

        # Create a dictionary to map node ids to their point types
        point_types = {point.id: type(point).__name__ for point in all_points}

        # Create nodes
        for node_id, data in graph.nodes(data=True):
            labels = ["Point"]
            if node_id in point_types:
                labels.append(point_types[node_id])

            params = {
                "id": node_id,
                "image_id": image_id,
                "session_id": session_id,
                **data,
            }
            tx.run(
                f"""
                CREATE (n:{':'.join(labels)} $params)
                """,
                params=params,
            )

        # Create edges
        for u, v, data in graph.edges(data=True):
            vector_id = data["id"]

            tx.run(
                """
                MATCH (a:Point {id: $u, image_id: $image_id})
                WITH a
                MATCH (b:Point {id: $v, image_id: $image_id})
                CREATE (vec:Vector {
                    id: $vector_id,
                    x1: a.x, y1: a.y,
                    x2: b.x, y2: b.y,
                    length: $length,
                    image_id: $image_id,
                    session_id: $session_id
                })
                CREATE (a)-[:CONNECTED_TO]->(vec)
                CREATE (vec)<-[:CONNECTED_TO]-(b)
                """,
                u=u,
                v=v,
                vector_id=vector_id,
                image_id=image_id,
                session_id=session_id,
                length=data["length"],
            )

    def close(self):
        self.driver.close()
