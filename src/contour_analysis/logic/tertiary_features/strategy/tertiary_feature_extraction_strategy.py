from abc import ABC, abstractmethod

from neo4j import ManagedTransaction


class TertiaryFeatureStrategy(ABC):
    @abstractmethod
    def execute(self, tx: ManagedTransaction, image_id: str):
        pass
