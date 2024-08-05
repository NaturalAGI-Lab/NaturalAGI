import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import TertiaryFeatureStrategy


class AnglePointsStrategy(TertiaryFeatureStrategy):
    """Strategy for extracting angle points.
    This class counts number of angle points per sample (image) and creates a new node
    named AnglePointsCount:Feature. With the count as a property.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
    
    
    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
           MATCH (angle_point:AnglePoint {image_id: $image_id})
           WITH COUNT(angle_point) AS count
           MERGE (angle_points_count:AnglePointsCount:Feature {session_id: $session_id})
           ON CREATE SET angle_points_count.count = count, angle_points_count.samples = [$image_id]
           ON MATCH SET angle_points_count.count = count, angle_points_count.samples = CASE WHEN $image_id IN angle_points_count.samples THEN angle_points_count.samples ELSE angle_points_count.samples + $image_id END
           RETURN angle_points_count
        """
        result = tx.run(query, image_id=image_id, session_id=self.session_id)
        result_data = result.data()
        logging.info(f"Angle points count: {result_data}")