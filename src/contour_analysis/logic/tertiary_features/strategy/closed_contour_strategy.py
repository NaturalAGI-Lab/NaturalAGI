import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import TertiaryFeatureStrategy


class ClosedContourStrategy(TertiaryFeatureStrategy):
    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
            MATCH (closed:Closed {image_id: $image_id})
            WITH COUNT(closed) > 0 AS closed_exists
            RETURN closed_exists
        """
        result = tx.run(query, image_id=image_id)
        logging.info(f"Closed contour exists: {result.single()['closed_exists']}")
