from abc import ABC, abstractmethod
from neo4j import ManagedTransaction
import networkx as nx


class BaseAnalyzer(ABC):
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    @abstractmethod
    def analyze(self) -> any:
        pass
    
    @abstractmethod
    def persist(self, mx: ManagedTransaction, session_id: str, image_id: str, result: any):
        pass