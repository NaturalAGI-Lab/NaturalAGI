import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class VectorAngleStrategy(TertiaryFeatureStrategy):
    """Sets angle_with_ox on Vector nodes as internal energy u_k ∈ [0, 1].

    Quantized to nearest 10° (discretization), then h_k = v/180 (Parzhyn formula 36).
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    def execute(self, tx: ManagedTransaction, image_id: str):
        tx.run("""
            MATCH (v:Vector {image_id: $image_id})
            WITH v, v.x2 - v.x1 AS dx, v.y2 - v.y1 AS dy
            WITH v, dx, dy, sqrt(dx * dx + dy * dy) AS mag
            WITH v, CASE
                WHEN mag < 1e-10 THEN 0.0
                ELSE degrees(acos(
                    CASE
                        WHEN toFloat(dx) / mag > 1.0 THEN 1.0
                        WHEN toFloat(dx) / mag < -1.0 THEN -1.0
                        ELSE toFloat(dx) / mag
                    END
                ))
            END AS raw_angle
            SET v.angle_with_ox = (round(raw_angle / 10.0) * 10) / 180.0
        """, image_id=image_id)

        logging.info("VectorAngleStrategy: set angle_with_ox for image %s", image_id)
