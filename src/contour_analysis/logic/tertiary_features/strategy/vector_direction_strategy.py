import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class VectorDirectionStrategy(TertiaryFeatureStrategy):
    """Sets horizontal_direction and vertical_direction on Vector nodes.

    Values match common.model.enums: LEFT=1, RIGHT=2, NONE=3 / TOP=1, BOTTOM=2, NONE=3.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    def execute(self, tx: ManagedTransaction, image_id: str):
        query = """
            MATCH (v:Vector {image_id: $image_id})
            SET v.horizontal_direction = CASE
                    WHEN v.x2 > v.x1 THEN 2
                    WHEN v.x2 < v.x1 THEN 1
                    ELSE 3
                END,
                v.vertical_direction = CASE
                    WHEN v.y2 > v.y1 THEN 2
                    WHEN v.y2 < v.y1 THEN 1
                    ELSE 3
                END
        """
        tx.run(query, image_id=image_id)
        logging.info("VectorDirectionStrategy: set h/v direction for image %s", image_id)
