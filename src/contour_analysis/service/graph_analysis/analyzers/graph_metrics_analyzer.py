import logging
from typing import Dict
from neo4j import ManagedTransaction
import networkx as nx

from .base_analyzer import BaseAnalyzer

logging.basicConfig(level=logging.INFO)


class GraphMetricsAnalyzer(BaseAnalyzer):
    def analyze(self) -> Dict[str, float]:
        metrics = self._calculate_metrics()
        return metrics

    def _calculate_metrics(self) -> Dict[str, float]:
        logging.info("Analyzing graph metrics")
        metrics = {}

        try:
            # Basic metrics
            metrics["GraphDensity"] = nx.density(self.graph)
            metrics["AverageClusteringCoefficient"] = nx.average_clustering(self.graph)

            # Path-based metrics (only if graph is connected)
            if nx.is_connected(self.graph):
                metrics["AveragePathLength"] = nx.average_shortest_path_length(self.graph)
                metrics["GraphDiameter"] = nx.diameter(self.graph)
                metrics["GraphRadius"] = nx.radius(self.graph)

            # Centrality metrics
            degree_centrality = nx.degree_centrality(self.graph)
            metrics["AverageDegree"] = sum(degree_centrality.values()) / len(self.graph)

            betweenness_centrality = nx.betweenness_centrality(self.graph)
            metrics["AverageBetweenness"] = sum(betweenness_centrality.values()) / len(
                self.graph
            )

            closeness_centrality = nx.closeness_centrality(self.graph)
            metrics["AverageCloseness"] = sum(closeness_centrality.values()) / len(
                self.graph
            )

            logging.info(f"Calculated metrics: {metrics}")
            return metrics

        except Exception as e:
            logging.error(f"Error calculating metrics: {str(e)}")
            return {}

    def persist(
        self,
        mx: ManagedTransaction,
        session_id: str,
        image_id: str,
        result: Dict[str, float],
    ) -> None:
        for metric_name, value in result.items():
            query = f"""
                MERGE (metric:{metric_name}:Feature {{
                    session_id: $session_id,
                    value: $value
                }})
                ON CREATE SET metric.samples = [$image_id]
                ON MATCH SET metric.samples = CASE
                    WHEN NOT $image_id IN metric.samples THEN metric.samples + $image_id
                    ELSE metric.samples
                END
            """

            mx.run(query, session_id=session_id, value=value, image_id=image_id)
