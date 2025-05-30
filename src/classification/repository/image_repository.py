from neo4j import GraphDatabase
import networkx as nx
import logging
from common.decorator import timed
from .neo4j_to_networkx import Neo4jToNetworkX


class ImageRepository:
    def __init__(self, neo4j_dsn: str, neo4j_user: str, neo4j_pass: str):
        self.neo4j_dsn = neo4j_dsn
        self.neo4j_user = neo4j_user
        self.neo4j_pass = neo4j_pass
        self.driver = GraphDatabase.driver(neo4j_dsn, auth=(neo4j_user, neo4j_pass))
        self.logger = logging.getLogger(__name__)

    def close(self):
        self.driver.close()

    @timed(label="get_image_graph")
    def get_image_graph(self, image_id: str) -> nx.Graph:
        query = """
            MATCH (n {image_id: $image_id})
            WHERE n:Point OR n:Vector
            WITH n, labels(n) as node_labels, properties(n) as node_props
            OPTIONAL MATCH (n)-[r]-(m {image_id: $image_id})
            WITH n, node_labels, r, m, node_props
            RETURN elementId(n) AS node_id, 
                node_labels,
                node_props,
                type(r) AS rel_type, 
                elementId(r) AS rel_id,
                elementId(m) AS target_id
        """
        with self.driver.session() as session:
            result = session.run(query, image_id=image_id)
            return Neo4jToNetworkX.build_networkx_graph(result, is_concept=False)

    def remove_image_nodes(self, image_id: str) -> None:
        query = """
            MATCH (n)
            WHERE n.image_id = $image_id OR $image_id IN n.samples
            DETACH DELETE n
        """
        with self.driver.session() as session:
            session.run(query, image_id=image_id)
            self.logger.info(f"Removed all nodes for image_id: {image_id}")
