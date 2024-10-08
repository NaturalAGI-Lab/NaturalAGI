import networkx as nx
from neo4j import GraphDatabase


class GraphPersistenceService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def save_graph_to_neo4j(
        self, graph: nx.Graph, image_id: str, session_id: str
    ) -> None:
        with self.driver.session() as session:
            session.write_transaction(self._save_graph, graph, image_id, session_id)

    def _save_graph(self, tx, graph: nx.Graph, image_id: str, session_id: str) -> None:
        # Create nodes
        for node, data in graph.nodes(data=True):
            tx.run(
                """
                CREATE (n:Point {id: $id, x: $x, y: $y, image_id: $image_id, session_id: $session_id})
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
                CREATE (a)-[:CONNECTED_TO]->(v)
                CREATE (v)<-[:CONNECTED_TO]-(b)            
                """,
                u=u_data["uuid"],
                v=v_data["uuid"],
                vector_id=vector_id,
                image_id=image_id,
                session_id=session_id,
                length=length,
            )

    def close(self):
        self.driver.close()
