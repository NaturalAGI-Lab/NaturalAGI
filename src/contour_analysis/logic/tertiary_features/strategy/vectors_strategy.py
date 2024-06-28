import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import TertiaryFeatureStrategy


class VectorsStrategy(TertiaryFeatureStrategy):
    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
            MATCH (vector:Vector {image_id: $image_id})
            RETURN vector
        """
        result = tx.run(query, image_id=image_id)
        result_data = result.data()
        logging.info(f"Vectors: {result_data}")
