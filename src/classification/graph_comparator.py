import logging
import numpy as np
from neo4j import GraphDatabase
from typing import List, Dict, Any
import networkx as nx
from graph_similarity.neo4j_to_networkx import Neo4jToNetworkX
from graph_similarity.gat_classification import predict_for_image

logging.basicConfig(level=logging.INFO)


class GraphComparator:
    def __init__(
        self, neo4j_dsn: str, neo4j_user: str, neo4j_pass: str, max_workers: int = 4
    ):
        self.driver = GraphDatabase.driver(neo4j_dsn, auth=(neo4j_user, neo4j_pass))
        self.max_workers = max_workers

    def close(self):
        self.driver.close()

    def compare_graphs(
        self, image_id: str, classification_params: Any
    ) -> Dict[str, Any]:
        logging.info(f"Predicting class for image {image_id}")

        with self.driver.session() as session:
            image_graph = session.execute_read(
                Neo4jToNetworkX.extract_image_graph, image_id
            )

        activated_class = predict_for_image(image_graph)
        logging.info(f"Activated class: {activated_class}")

        return {"activated_class": str(activated_class)}

    def remove_image_nodes(self, image_id: str) -> None:
        with self.driver.session() as session:
            session.write_transaction(self._remove_image_nodes, image_id)

    def _remove_image_nodes(self, tx: Any, image_id: str) -> None:
        query = """
            MATCH (n)
            WHERE n.image_id = $image_id OR $image_id IN n.samples
            DETACH DELETE n
        """
        tx.run(query, image_id=image_id)
        logging.info(f"Removed all nodes for image_id: {image_id}")
