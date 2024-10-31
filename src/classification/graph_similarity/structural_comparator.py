import logging
from neo4j import Session
import networkx as nx
from graph_similarity.neo4j_to_networkx import Neo4jToNetworkX
from typing import Dict, Any, Set
from grakel import Graph, VertexHistogram, WeisfeilerLehman


class StructuralComparator:
    @staticmethod
    def compare_graphs_wl(session: Session, image_id: str, concept_id: str, concept_name: str) -> float:
        logging.info(
            f"Comparing graph for image {image_id} with concept {concept_name} ({concept_id}) using WL kernel"
        )

        image_graph = Neo4jToNetworkX.extract_image_graph(session, image_id)
        concept_graph = Neo4jToNetworkX.extract_concept_graph(session, concept_id)

        logging.info(f"Image graph: {image_graph}")
        logging.info(f"Concept graph: {concept_graph}")

        # Convert NetworkX graphs to Grakel format
        g1 = StructuralComparator._convert_to_grakel_format(image_graph)
        g2 = StructuralComparator._convert_to_grakel_format(concept_graph)

        wl_kernel = WeisfeilerLehman(
            n_iter=5, base_graph_kernel=VertexHistogram, normalize=True
        )
        
        graph_list = [g1, g2]

        # Compute the kernel
        K = wl_kernel.fit_transform(graph_list)
        similarity = K[0, 1]

        logging.info(f"Weisfeiler-Lehman kernel similarity: {similarity}")
        return similarity

    @staticmethod
    def _convert_to_grakel_format(graph: nx.Graph) -> Dict:
        """Convert a NetworkX graph to Grakel format."""
        node_labels = {
            n: StructuralComparator._get_node_label(data)
            for n, data in graph.nodes(data=True)
        }
        edge_labels = {
            (u, v): data["type"] for u, v, data in graph.edges(data=True)
        }
        edge_list = list(graph.edges())
        logging.info(f"Final Nodes list: {node_labels}")
        logging.info(f"Final Edges list: {edge_labels}")
        return Graph(edge_list, node_labels=node_labels, edge_labels=edge_labels)

    @staticmethod
    def _get_node_label(node_data: Dict[str, Any]) -> str:
        """Get a label for a node based on its type."""
        labels = node_data.get("labels", set())
        return StructuralComparator._get_node_label_from_set(labels)

    @staticmethod
    def _get_node_label_from_set(labels: Set[str]) -> str:
        """Get a label for a node based on its type."""
        if "IntersectionPoint" in labels:
            return "IntersectionPoint"
        elif "CornerPoint" in labels:
            return "CornerPoint"
        else:
            return next(iter(labels), "Unknown")
