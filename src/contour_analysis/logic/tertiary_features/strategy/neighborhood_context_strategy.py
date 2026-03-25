import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class NeighborhoodContextStrategy(TertiaryFeatureStrategy):
    """Counts neighbor Point types within 2 hops via the bipartite Neo4j structure.

    Sets neighbor_endpoint_count, neighbor_junction_count, neighbor_corner_count
    on each Point node.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    def execute(self, tx: ManagedTransaction, image_id: str):
        tx.run("""
            MATCH (p:Point {image_id: $image_id})
            OPTIONAL MATCH (p)-[:CONNECTED_TO]->(v:Vector {image_id: $image_id})
                           <-[:CONNECTED_TO]-(neighbor:Point)
            WHERE neighbor <> p
            WITH p,
                 count(CASE WHEN neighbor:EndPoint THEN 1 END) AS ep_count,
                 count(CASE WHEN neighbor:IntersectionPoint THEN 1 END) AS jp_count,
                 count(CASE WHEN neighbor:CornerPoint THEN 1 END) AS cp_count
            SET p.neighbor_endpoint_count = ep_count,
                p.neighbor_junction_count = jp_count,
                p.neighbor_corner_count = cp_count
        """, image_id=image_id)

        logging.info(
            "NeighborhoodContextStrategy: set neighbor counts for image %s", image_id
        )
