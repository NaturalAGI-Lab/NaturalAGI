from neo4j import Driver, ManagedTransaction
from logic.tertiary_features.strategy.vectors_strategy import VectorsStrategy
from logic.tertiary_features.strategy.end_points_strategy import EndPointsStrategy
from logic.tertiary_features.strategy.intersection_points_strategy import IntersectionPointsStrategy
from logic.tertiary_features.strategy.corner_points_strategy import CornerPointsStrategy
from logic.tertiary_features.strategy.quadrant_change_strategy import QuadrantChangeStrategy


class TertiaryFeaturesService:
    def __init__(self, driver: Driver):
        self.driver = driver
        
    def create_tertiary_features(self, image_id: str, session_id: str):
        with self.driver.session() as session:
            session.execute_write(self._create_tertiary_features, image_id, session_id)
        
    def _create_tertiary_features(self, tx: ManagedTransaction, image_id: str, session_id: str):
        VectorsStrategy(session_id).execute(tx, image_id)
        QuadrantChangeStrategy(session_id).execute(tx, image_id)
        IntersectionPointsStrategy(session_id).execute(tx, image_id)
        CornerPointsStrategy(session_id).execute(tx, image_id)
        EndPointsStrategy(session_id).execute(tx, image_id)
