from neo4j import ManagedTransaction
from logic.tertiary_features.strategy.vectors_strategy import VectorsStrategy
from logic.tertiary_features.strategy.end_points_strategy import EndPointsStrategy
from logic.tertiary_features.strategy.intersection_points_strategy import IntersectionPointsStrategy

tertiary_features_strategies = [
    # ClosedContourStrategy(),
    # OpenContourStrategy(),
    # CriticalPointsStrategy(),
    # VectorsStrategy()
    # QuadrantChangeStrategy()
]


def create_tertiary_features(tx: ManagedTransaction, image_id: str, session_id: str):
    VectorsStrategy(session_id).execute(tx, image_id)
    IntersectionPointsStrategy(session_id).execute(tx, image_id)
    EndPointsStrategy(session_id).execute(tx, image_id)
