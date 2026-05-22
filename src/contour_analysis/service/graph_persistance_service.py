import networkx as nx
from neo4j import Driver
from logic.point_extractor import PointExtractor
import logging


class GraphPersistenceService:
    def __init__(self, driver: Driver):
        self.driver = driver
        self.logger = logging.getLogger(__name__)

    def save_graph_to_neo4j(self, graph: nx.Graph, image_id: str, session_id: str) -> None:
        point_types = {
            point.id: type(point).__name__
            for point in PointExtractor(graph).extract_points()
        }
        with self.driver.session() as session:
            session.execute_write(self._save_graph, graph, image_id, session_id, point_types)

    def _save_graph(
        self, tx, graph: nx.Graph, image_id: str, session_id: str, point_types: dict
    ) -> None:
        by_label: dict[str | None, list[dict]] = {}
        for node_id, data in graph.nodes(data=True):
            label = point_types.get(node_id)
            by_label.setdefault(label, []).append(
                {"id": node_id, "image_id": image_id, "session_id": session_id, **data}
            )

        for label, nodes in by_label.items():
            label_clause = f":Point:{label}" if label else ":Point"
            tx.run(f"UNWIND $nodes AS p CREATE (n{label_clause}) SET n = p", nodes=nodes)

        edges = [
            {
                "u": u,
                "v": v,
                "vector_id": data["id"],
                "length": data["length"],
                "image_id": image_id,
                "session_id": session_id,
            }
            for u, v, data in graph.edges(data=True)
        ]
        if edges:
            tx.run(
                """
                UNWIND $edges AS e
                MATCH (a:Point {id: e.u, image_id: e.image_id})
                MATCH (b:Point {id: e.v, image_id: e.image_id})
                CREATE (vec:Vector {
                    id: e.vector_id,
                    x1: a.x, y1: a.y, x2: b.x, y2: b.y,
                    length: e.length,
                    image_id: e.image_id,
                    session_id: e.session_id
                })
                CREATE (a)-[:CONNECTED_TO]->(vec)
                CREATE (vec)<-[:CONNECTED_TO]-(b)
                """,
                edges=edges,
            )
