import logging

from neo4j import GraphDatabase

logging.basicConfig(level=logging.DEBUG)

class GraphComparator:
    def __init__(self, neo4j_dsn: str, neo4j_user: str, neo4j_pass: str):
        self.driver = GraphDatabase.driver(neo4j_dsn, auth=(neo4j_user, neo4j_pass))
        
    def compare_graphs(self, concept_id: str, image_id: str) -> float:
        logging.info(f"Comparing concept {concept_id} with image {image_id}")
        with self.driver.session() as session:
            return session.read_transaction(self._compare_graphs, concept_id, image_id)

    @staticmethod
    def _compare_graphs(tx, concept_id: str, image_id: str) -> float:
        """
        Compare two graphs based on their similarity.
        As a comparison metric we use the percentage of matching nodes from concept graph to image graph.
        Edge matching is not considered.

        Args:
            tx: Neo4j transaction
            concept_id (str): Concept graph id
            image_id (str): Image id

        Returns:
            float: Confidence score between 0 and 1
        """

        query = """
            MATCH (c:Concept {id: $concept_id})-[:INCLUDES]->(cn)
            WITH collect(labels(cn)) AS concept_nodes
            MATCH (n)
            WHERE n.image_id = $image_id OR $image_id IN n.samples
            WITH concept_nodes, collect(labels(n)) AS image_nodes
            RETURN toFloat(size([x IN concept_nodes WHERE x IN image_nodes])) / size(concept_nodes) AS confidence
        """

        result = tx.run(query, concept_id=concept_id, image_id=image_id)
        confidence = result.single()["confidence"]
        logging.info(f"Confidence score for concept_id {concept_id} and image_id {image_id}: {confidence}")
        return confidence
        