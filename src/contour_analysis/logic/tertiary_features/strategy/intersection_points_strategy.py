import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class IntersectionPointsStrategy(TertiaryFeatureStrategy):
    """Strategy for counting intersection points per sample and storing count as a node property.

    Note: The intersection points are also added to corner_points_count in the CornerPointsStrategy,
    since intersection points can functionally replace corner points.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
           MATCH (intersection_point:IntersectionPoint {image_id: $image_id})
           WITH COUNT(intersection_point) AS count
           CALL {
               WITH count
               MATCH (n:Point {image_id: $image_id})
               SET n.intersection_points_count = count
           }
           CALL {
               WITH count
               MATCH (n:Vector {image_id: $image_id})
               SET n.intersection_points_count = count
           }
        """
        result = tx.run(query, image_id=image_id, session_id=self.session_id)
        result_data = result.data()
        logging.info(f"Intersection points count: {result_data}")
