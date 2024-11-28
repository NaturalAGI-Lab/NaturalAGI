import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class QuadrantChangeStrategy(TertiaryFeatureStrategy):
    """Strategy for extracting quadrant change.
    This class counts number of quadrant change per sample (image) and creates a new node
    named QuadrantChangeCount:Feature. With the count as a property.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    def execute(self, tx: ManagedTransaction, image_id: str):
        # Create quadrant changes
        create_quadrant_change_query = """
            MATCH (point:Point {image_id: $image_id})
            WHERE EXISTS {
                MATCH (point)--(v1:Vector {image_id: $image_id})--(q1:Quadrant)
                MATCH (point)--(v2:Vector {image_id: $image_id})--(q2:Quadrant)
                WHERE q1.value <> q2.value
            }
            CREATE (point)-[:HAS_QUADRANT_CHANGE]->(qc:QuadrantChange {image_id: $image_id})
        """
        tx.run(create_quadrant_change_query, image_id=image_id)

        # Count quadrant changes
        query = """
            MATCH (quad_change:QuadrantChange {image_id: $image_id})
            WITH COUNT(quad_change) AS count, collect(quad_change) AS quad_changes
            MERGE (quadrant_change_count:QuadrantChangeCount:Feature {session_id: $session_id, value: count})
            ON CREATE SET quadrant_change_count.samples = [$image_id]
            ON MATCH SET quadrant_change_count.samples = CASE WHEN $image_id IN quadrant_change_count.samples THEN quadrant_change_count.samples ELSE quadrant_change_count.samples + $image_id END
            RETURN count, [quad_change IN quad_changes | id(quad_change)] AS quad_change_ids
        """
        result = tx.run(query, image_id=image_id, session_id=self.session_id)
        result_data = result.single()
        logging.info(f"Quadrant change count: {result_data}")

        # Remove the quadrant changes after counting
        delete_query = """
            UNWIND $quad_change_ids AS quad_change_id
            MATCH (quad_change) WHERE id(quad_change) = quad_change_id
            DETACH DELETE quad_change
        """
        tx.run(delete_query, quad_change_ids=result_data["quad_change_ids"])
