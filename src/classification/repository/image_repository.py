import networkx as nx
import logging
from common.decorator import timed
from .neo4j_to_networkx import Neo4jToNetworkX


class ImageRepository:
    def __init__(self, driver):
        self.driver = driver
        self.logger = logging.getLogger(__name__)

    @timed(label="get_image_graph")
    def get_image_graph(self, image_id: str) -> nx.Graph:
        query = """
            CALL {
                MATCH (n:Point {image_id: $image_id}) RETURN n
                UNION ALL
                MATCH (n:Vector {image_id: $image_id}) RETURN n
            }
            WITH n, labels(n) as node_labels, properties(n) as node_props
            OPTIONAL MATCH (n)-[r]-(m {image_id: $image_id})
            WITH n, node_labels, r, m, node_props
            RETURN n.id AS node_id,
                node_labels,
                node_props,
                type(r) AS rel_type,
                elementId(r) AS rel_id,
                m.id AS target_id
        """
        with self.driver.session() as session:
            result = session.run(query, image_id=image_id)
            return Neo4jToNetworkX.build_networkx_graph(result, is_concept=False)

    def remove_image_nodes(self, image_id: str) -> None:
        query = """
            CALL {
                MATCH (n:Point {image_id: $image_id})
                DETACH DELETE n
            }
            CALL {
                MATCH (n:Vector {image_id: $image_id})
                DETACH DELETE n
            }
        """
        with self.driver.session() as session:
            session.run(query, image_id=image_id)
            self.logger.info(f"Removed all nodes for image_id: {image_id}")
