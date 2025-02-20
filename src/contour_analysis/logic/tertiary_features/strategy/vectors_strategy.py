import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class VectorsStrategy(TertiaryFeatureStrategy):
    """Strategy for extracting vectors.
    This class counts the number of vectors per sample (image) and creates a new node
    named VectorsCount:Feature. With the count as a property.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
           MATCH (vector:Vector {image_id: $image_id})
           WITH COUNT(vector) AS count
           MATCH (n)
           WHERE n.image_id = $image_id
           SET n.vectors_count = count
           /*
            MERGE (vectors_count:VectorsCount:Feature {session_id: $session_id, value: count})
            ON CREATE SET vectors_count.samples = [$image_id]
            ON MATCH SET vectors_count.samples = CASE WHEN $image_id IN vectors_count.samples THEN vectors_count.samples ELSE vectors_count.samples + $image_id END
            RETURN vectors_count
            */
        """
        result = tx.run(query, image_id=image_id, session_id=self.session_id)
        result_data = result.data()
        logging.info(f"Vectors count: {result_data}")
