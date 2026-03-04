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

    METRIC_NAME_TO_PROPERTY = {
        "GraphDensity": "graph_density",
        "AverageClusteringCoefficient": "avg_clustering_coeff",
        "AveragePathLength": "avg_path_length",
        "GraphDiameter": "graph_diameter",
        "GraphRadius": "graph_radius",
        "AverageDegree": "avg_degree",
        "AverageBetweenness": "avg_betweenness",
        "AverageCloseness": "avg_closeness",
    }

    def persist(
        self,
        mx: ManagedTransaction,
        session_id: str,
        image_id: str,
        result: Dict[str, float],
    ) -> None:
        for metric_name, value in result.items():
            prop = self.METRIC_NAME_TO_PROPERTY[metric_name]
            query = f"""
                CALL {{
                    MATCH (n:Point {{image_id: $image_id}})
                    SET n.{prop} = $value
                }}
                CALL {{
                    MATCH (n:Vector {{image_id: $image_id}})
                    SET n.{prop} = $value
                }}
            """
            mx.run(query, image_id=image_id, value=value)
