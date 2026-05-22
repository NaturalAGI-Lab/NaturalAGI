import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class VectorNormalizedCoordsStrategy(TertiaryFeatureStrategy):
    """Sets normalized_x/y on Vectors (midpoint of connected Points) and quadrant on Points."""

    def __init__(self, session_id: str):
        self.session_id = session_id

    def execute(self, tx: ManagedTransaction, image_id: str):
        tx.run("""
            MATCH (p1:Point {image_id: $image_id})-[:CONNECTED_TO]->(v:Vector {image_id: $image_id})
                  <-[:CONNECTED_TO]-(p2:Point {image_id: $image_id})
            WHERE p1 <> p2
            WITH v,
                 (p1.normalized_x + p2.normalized_x) / 2.0 AS nx,
                 (p1.normalized_y + p2.normalized_y) / 2.0 AS ny
            SET v.normalized_x = round(nx * 10) / 10,
                v.normalized_y = round(ny * 10) / 10
        """, image_id=image_id)

        tx.run("""
            MATCH (p:Point {image_id: $image_id})
            SET p.quadrant = CASE
                WHEN p.normalized_x > 0 AND p.normalized_y > 0 THEN 1
                WHEN p.normalized_x < 0 AND p.normalized_y > 0 THEN 2
                WHEN p.normalized_x < 0 AND p.normalized_y < 0 THEN 3
                WHEN p.normalized_x > 0 AND p.normalized_y < 0 THEN 4
                ELSE -1
            END
        """, image_id=image_id)

        logging.info(
            "VectorNormalizedCoordsStrategy: set coords for image %s", image_id
        )
