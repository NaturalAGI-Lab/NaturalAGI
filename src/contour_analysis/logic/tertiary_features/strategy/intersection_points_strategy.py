import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import TertiaryFeatureStrategy


class IntersectionPointsStrategy(TertiaryFeatureStrategy):
    """Strategy for extracting intersection points.
    This class counts number of intersection points per sample (image) and creates a new node
    named IntersectionPointsCount:Feature. With the count as a property.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
    
    
    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
           MATCH (intersection_point:IntersectionPoint {image_id: $image_id})
           WITH COUNT(intersection_point) AS count
           MERGE (intersection_points_count:IntersectionPointsCount:Feature {session_id: $session_id, count: count})
           ON CREATE SET intersection_points_count.samples = [$image_id]
           ON MATCH SET intersection_points_count.samples = CASE WHEN $image_id IN intersection_points_count.samples THEN intersection_points_count.samples ELSE intersection_points_count.samples + $image_id END
           RETURN intersection_points_count
        """
        result = tx.run(query, image_id=image_id, session_id=self.session_id)
        result_data = result.data()
        logging.info(f"Intersection points count: {result_data}")
