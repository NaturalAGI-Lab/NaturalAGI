from neo4j import ManagedTransaction

from logic.tertiary_features.strategy.closed_contour_strategy import ClosedContourStrategy
from logic.tertiary_features.strategy.critical_points_strategy import CriticalPointsStrategy
from logic.tertiary_features.strategy.open_contour_strategy import OpenContourStrategy
from logic.tertiary_features.strategy.vectors_strategy import VectorsStrategy

tertiary_features_strategies = [
    ClosedContourStrategy(),
    OpenContourStrategy(),
    CriticalPointsStrategy(),
    VectorsStrategy()
]


def find_tertiary_features(tx: ManagedTransaction, image_id: str):
    for service in tertiary_features_strategies:
        service.execute(tx, image_id)
