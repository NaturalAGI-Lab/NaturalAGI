import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class VectorTypeStrategy(TertiaryFeatureStrategy):
    """Sets dx, dy, quadrant, and type labels on Vector nodes.

    Type labels: HorizontalVector (|dx|>|dy|), VerticalVector (|dy|>|dx|),
    DiagonalVector (|dx|==|dy|).
    Quadrant: 1-4 based on (dx,dy) signs, -1 for axis-aligned.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    def execute(self, tx: ManagedTransaction, image_id: str):
        tx.run("""
            MATCH (v:Vector {image_id: $image_id})
            WITH v, v.x2 - v.x1 AS dx, v.y2 - v.y1 AS dy
            SET v.dx = dx, v.dy = dy,
                v.quadrant = CASE
                    WHEN dx > 0 AND dy > 0 THEN 1
                    WHEN dx < 0 AND dy > 0 THEN 2
                    WHEN dx < 0 AND dy < 0 THEN 3
                    WHEN dx > 0 AND dy < 0 THEN 4
                    ELSE -1
                END
        """, image_id=image_id)

        tx.run("""
            MATCH (v:Vector {image_id: $image_id})
            REMOVE v:HorizontalVector, v:VerticalVector, v:DiagonalVector
            WITH v, abs(v.x2 - v.x1) AS adx, abs(v.y2 - v.y1) AS ady
            FOREACH (_ IN CASE WHEN adx > ady THEN [1] ELSE [] END |
                SET v:HorizontalVector)
            FOREACH (_ IN CASE WHEN ady > adx THEN [1] ELSE [] END |
                SET v:VerticalVector)
            FOREACH (_ IN CASE WHEN adx = ady THEN [1] ELSE [] END |
                SET v:DiagonalVector)
        """, image_id=image_id)

        logging.info("VectorTypeStrategy: set type labels for image %s", image_id)
