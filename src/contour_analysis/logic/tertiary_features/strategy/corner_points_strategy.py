import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import TertiaryFeatureStrategy


class CornerPointsStrategy(TertiaryFeatureStrategy):
    """Strategy for extracting corner points.
    This class counts number of corner points per sample (image) and creates a new node
    named CornerPointsCount:Feature. With the count as a property.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
    
    
    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
           MATCH (corner_point:CornerPoint {image_id: $image_id})
           WITH COUNT(corner_point) AS count
           MERGE (corner_points_count:CornerPointsCount:Feature {session_id: $session_id})
           ON CREATE SET corner_points_count.count = count, corner_points_count.samples = [$image_id]
           ON MATCH SET corner_points_count.count = count, corner_points_count.samples = CASE WHEN $image_id IN corner_points_count.samples THEN corner_points_count.samples ELSE corner_points_count.samples + $image_id END
           RETURN corner_points_count
        """
        result = tx.run(query, image_id=image_id, session_id=self.session_id)
        result_data = result.data()
        logging.info(f"Corner points count: {result_data}")
