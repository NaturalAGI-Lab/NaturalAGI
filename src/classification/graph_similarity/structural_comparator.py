import logging
from neo4j import Session
import networkx as nx
from typing import Dict, Any, Set, List, Tuple
from grakel import Graph, VertexHistogram, WeisfeilerLehman
from .neo4j_to_networkx import Neo4jToNetworkX


class StructuralComparator:
    @staticmethod
    def compare_graphs_wl(session: Session, image_id: str, concept_id: str, concept_name: str) -> float:
        logging.info(
            f"Comparing graph for image {image_id} with concept {concept_name} ({concept_id}) using WL kernel"
        )

        # Get original graphs
        image_graph = Neo4jToNetworkX.extract_image_graph(session, image_id)
        concept_graph = Neo4jToNetworkX.extract_concept_graph(session, concept_id)

        # Compare at different abstraction levels
        scores = []
        
        # Level 1: Original structure
        original_score = StructuralComparator._compare_at_level(
            image_graph, 
            concept_graph, 
            abstraction_level="original"
        )
        scores.append(("original", original_score))
        
        # Level 2: Simplified structure (Intersection -> Corner)
        simplified_score = StructuralComparator._compare_at_level(
            image_graph, 
            concept_graph, 
            abstraction_level="simplified"
        )
        scores.append(("simplified", simplified_score))
        
        # Level 3: Basic structure (all -> Point)
        basic_score = StructuralComparator._compare_at_level(
            image_graph, 
            concept_graph, 
            abstraction_level="basic"
        )
        scores.append(("basic", basic_score))

        # Get the best score
        best_score = max(scores, key=lambda x: x[1])
        logging.info(f"Comparison scores: {scores}")
        logging.info(f"Best score: {best_score[0]} - {best_score[1]}")
        
        return best_score[1]

    @staticmethod
    def _compare_at_level(image_graph: nx.Graph, concept_graph: nx.Graph, abstraction_level: str) -> float:
        """Compare graphs at a specific abstraction level"""
        # Create copies to modify
        img_graph = image_graph.copy()
        con_graph = concept_graph.copy()
        
        # Apply abstraction
        StructuralComparator._apply_abstraction(img_graph, abstraction_level)
        StructuralComparator._apply_abstraction(con_graph, abstraction_level)
        
        # Convert to Grakel format
        g1 = StructuralComparator._convert_to_grakel_format(img_graph)
        g2 = StructuralComparator._convert_to_grakel_format(con_graph)
        
        # Compare using WL kernel
        wl_kernel = WeisfeilerLehman(
            n_iter=5, 
            base_graph_kernel=VertexHistogram, 
            normalize=True
        )
        
        similarity = wl_kernel.fit_transform([g1, g2])[0, 1]
        return similarity

    @staticmethod
    def _apply_abstraction(graph: nx.Graph, level: str) -> None:
        """Apply abstraction rules to the graph based on level"""
        for node, data in list(graph.nodes(data=True)):
            labels = data.get("labels", set())
            
            # Only modify nodes that are some type of Point
            if any(label.endswith('Point') for label in labels):
                new_labels = set(labels)
                
                if level == "simplified":
                    # Convert Intersection points to Corner points
                    if "IntersectionPoint" in labels:
                        new_labels.remove("IntersectionPoint")
                        new_labels.add("CornerPoint")
                
                elif level == "basic":
                    # Remove specific point types and just keep Point
                    new_labels = {label for label in labels if not label.endswith('Point')}
                    new_labels.add("Point")
                
                # Update node labels only for Point nodes
                graph.nodes[node]["labels"] = new_labels

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
        elif "Point" in labels:
            return "Point"
        else:
            return next(iter(labels), "Unknown")
