import networkx as nx
from typing import List, Type
from .analyzers.base_analyzer import BaseAnalyzer

class GraphAnalyzer:
    def __init__(self, graph: nx.Graph):
        self.graph = graph
        self.analyzers: List[BaseAnalyzer] = []

    def add_analyzer(self, analyzer_class: Type[BaseAnalyzer]):
        analyzer = analyzer_class(self.graph)
        self.analyzers.append(analyzer)

    def analyze(self) -> dict:
        results = {}
        for analyzer in self.analyzers:
            results.update(analyzer.analyze())
        return results