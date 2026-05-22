import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class VectorsStrategy(TertiaryFeatureStrategy):
    """Strategy for counting vectors per sample and storing count as a node property."""

    def __init__(self, session_id: str):
        self.session_id = session_id

    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
           MATCH (vector:Vector {image_id: $image_id})
           WITH COUNT(vector) AS count
           CALL {
               WITH count
               MATCH (n:Point {image_id: $image_id})
               SET n.vectors_count = count
           }
           CALL {
               WITH count
               MATCH (n:Vector {image_id: $image_id})
               SET n.vectors_count = count
           }
        """
        result = tx.run(query, image_id=image_id, session_id=self.session_id)
        result_data = result.data()
        logging.info(f"Vectors count: {result_data}")
