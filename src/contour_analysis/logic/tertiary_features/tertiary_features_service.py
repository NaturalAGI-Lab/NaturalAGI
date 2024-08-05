from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.angle_points_strategy import AnglePointsStrategy
from logic.tertiary_features.strategy.quadrant_change_strategy import (
    QuadrantChangeStrategy,
)

tertiary_features_strategies = [
    # ClosedContourStrategy(),
    # OpenContourStrategy(),
    # CriticalPointsStrategy(),
    # VectorsStrategy()
    # AnglePointsStrategy(),
    # QuadrantChangeStrategy()
]


def create_tertiary_features(tx: ManagedTransaction, image_id: str, session_id: str):
    AnglePointsStrategy(session_id).execute(tx, image_id)
