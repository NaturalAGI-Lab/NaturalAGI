import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import TertiaryFeatureStrategy


class OpenContourStrategy(TertiaryFeatureStrategy):
    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
            MATCH (open:Open {image_id: $image_id})
            WITH COUNT(open) > 0 AS open_exists
            RETURN open_exists
        """
        result = tx.run(query, image_id=image_id)
        logging.info(f"Open contour exists: {result.single()['open_exists']}")
