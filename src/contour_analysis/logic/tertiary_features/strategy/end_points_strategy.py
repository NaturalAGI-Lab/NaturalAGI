import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import TertiaryFeatureStrategy


class EndPointsStrategy(TertiaryFeatureStrategy):
    """Strategy for counting end points per sample and storing count as a node property."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
    
    
    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
           MATCH (end_point:EndPoint {image_id: $image_id})
           WITH COUNT(end_point) AS count
           CALL {
               WITH count
               MATCH (n:Point {image_id: $image_id})
               SET n.endpoints_count = count
           }
           CALL {
               WITH count
               MATCH (n:Vector {image_id: $image_id})
               SET n.endpoints_count = count
           }
        """
        result = tx.run(query, image_id=image_id, session_id=self.session_id)
        result_data = result.data()
        logging.info(f"End points count: {result_data}")
