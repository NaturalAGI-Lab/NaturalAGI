import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import TertiaryFeatureStrategy


class CriticalPointsStrategy(TertiaryFeatureStrategy):
    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
            MATCH (critical_point: CriticalPoint)--(:AnglePoint {image_id: $image_id})
            RETURN critical_point
        """
        result = tx.run(query, image_id=image_id)
        result_data = result.data()
        logging.info(f"Critical points: {result_data}")
