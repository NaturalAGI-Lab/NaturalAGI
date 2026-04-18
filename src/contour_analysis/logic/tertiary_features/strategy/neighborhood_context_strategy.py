import logging

from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.tertiary_feature_extraction_strategy import (
    TertiaryFeatureStrategy,
)


class NeighborhoodContextStrategy(TertiaryFeatureStrategy):
    """Counts neighbor Point types and persists them as u_k = count/raw_degree ∈ [0, 1].

    h_k (Parzhyn formula 36) is applied in-query by dividing by the raw degree
    stashed by StructuralFeatureAnalyzer. The scratch field is removed afterwards.
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
                 count(CASE WHEN neighbor:CornerPoint THEN 1 END) AS cp_count,
                 toFloat(coalesce(p.raw_node_degree, 0)) AS raw_degree
            SET p.neighbor_endpoint_count =
                    CASE WHEN raw_degree > 0 THEN toFloat(ep_count) / raw_degree ELSE 0.0 END,
                p.neighbor_junction_count =
                    CASE WHEN raw_degree > 0 THEN toFloat(jp_count) / raw_degree ELSE 0.0 END,
                p.neighbor_corner_count =
                    CASE WHEN raw_degree > 0 THEN toFloat(cp_count) / raw_degree ELSE 0.0 END
            REMOVE p.raw_node_degree
        """, image_id=image_id)

        logging.info(
            "NeighborhoodContextStrategy: set neighbor counts for image %s", image_id
        )
