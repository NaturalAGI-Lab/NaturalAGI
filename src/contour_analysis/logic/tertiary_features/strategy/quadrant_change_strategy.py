import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class QuadrantChangeStrategy(TertiaryFeatureStrategy):
    """Strategy for extracting quadrant change count from vector quadrant properties."""

    def __init__(self, session_id: str):
        self.session_id = session_id

    def execute(self, tx: ManagedTransaction, image_id: str):
        create_quadrant_change_query = """
            MATCH (point:Point {image_id: $image_id})
            WHERE EXISTS {
                MATCH (point)--(v1:Vector {image_id: $image_id})
                MATCH (point)--(v2:Vector {image_id: $image_id})
                WHERE v1.quadrant <> v2.quadrant AND v1 <> v2
            }
            CREATE (point)-[:HAS_QUADRANT_CHANGE]->(qc:QuadrantChange {image_id: $image_id})
            SET point.is_quadrant_change = 1
        """
        tx.run(create_quadrant_change_query, image_id=image_id)

        query = """
            MATCH (quad_change:QuadrantChange {image_id: $image_id})
            WITH COUNT(quad_change) AS count, collect(elementId(quad_change)) AS quad_change_ids
            CALL {
                WITH count
                MATCH (n:Point {image_id: $image_id})
                SET n.quadrant_change_count = count
            }
            CALL {
                WITH count
                MATCH (n:Vector {image_id: $image_id})
                SET n.quadrant_change_count = count
            }
            RETURN count, quad_change_ids
        """
        result = tx.run(query, image_id=image_id, session_id=self.session_id)
        result_data = result.single()
        logging.info(f"Quadrant change count: {result_data}")

        delete_query = """
            UNWIND $quad_change_ids AS quad_change_id
            MATCH (quad_change) WHERE elementId(quad_change) = quad_change_id
            DETACH DELETE quad_change
        """
        tx.run(delete_query, quad_change_ids=result_data["quad_change_ids"])
