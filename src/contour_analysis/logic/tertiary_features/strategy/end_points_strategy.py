import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import TertiaryFeatureStrategy


class EndPointsStrategy(TertiaryFeatureStrategy):
    """Strategy for extracting end points.
    This class counts number of end points per sample (image) and creates a new node
    named EndPointsCount:Feature. With the count as a property.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
    
    
    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
           MATCH (end_point:EndPoint {image_id: $image_id})
           WITH COUNT(end_point) AS count
           MERGE (end_points_count:EndPointsCount:Feature {session_id: $session_id, value: count})
           ON CREATE SET end_points_count.samples = [$image_id]
           ON MATCH SET end_points_count.samples = CASE WHEN $image_id IN end_points_count.samples THEN end_points_count.samples ELSE end_points_count.samples + $image_id END
           RETURN end_points_count
        """
        result = tx.run(query, image_id=image_id, session_id=self.session_id)
        result_data = result.data()
        logging.info(f"End points count: {result_data}")
