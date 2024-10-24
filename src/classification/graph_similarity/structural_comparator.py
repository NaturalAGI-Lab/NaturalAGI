import logging
from neo4j import Session
import networkx as nx
from graph_similarity.neo4j_to_networkx import Neo4jToNetworkX
import numpy as np
from typing import Dict, Any, Optional, Tuple, Set


class StructuralComparator:
    @staticmethod
    def compare_graphs(session: Session, image_id: str, concept_id: str) -> float:
        logging.info(f"Comparing graph for image {image_id} with concept {concept_id}")
        image_graph = Neo4jToNetworkX.extract_image_graph(session, image_id)
        concept_graph = Neo4jToNetworkX.extract_concept_graph(session, concept_id)
        
        logging.info(f"Image graph: {image_graph}")
        logging.info(f"Concept graph: {concept_graph}")

        ged = nx.graph_edit_distance(
            image_graph,
            concept_graph,
            node_match=StructuralComparator._node_match,
            edge_match=StructuralComparator._edge_match,
            node_subst_cost=StructuralComparator._node_substitution_cost,
            node_del_cost=StructuralComparator._node_deletion_cost,
            node_ins_cost=StructuralComparator._node_insertion_cost,
            edge_subst_cost=StructuralComparator._edge_substitution_cost,
            edge_del_cost=StructuralComparator._edge_deletion_cost,
            edge_ins_cost=StructuralComparator._edge_insertion_cost,
            timeout=10,
        )
        logging.info(f"Graph edit distance: {ged}")
        return StructuralComparator._normalize_distance(ged, image_graph, concept_graph)

    @staticmethod
    def _node_match(n1: dict, n2: dict) -> bool:
        """Custom node matching function checking label intersection."""
        return "labels" in n1 and "labels" in n2 and bool(set(n1["labels"]) & set(n2["labels"]))

    @staticmethod
    def _edge_match(e1: dict, e2: dict) -> bool:
        """Match edges based on their type."""
        return e1["type"] == e2["type"]

    @staticmethod
    def _node_substitution_cost(node1: Dict[str, Any], node2: Dict[str, Any]) -> float:
        """
        Calculate cost of substituting one node for another based on:
        - Node type importance
        - Number of connected edges (degree)
        """
        # If node types don't match at all
        if not StructuralComparator._node_match(node1, node2):
            return 1.0
        
        # Get importance weights for both nodes
        importance1 = StructuralComparator._get_node_importance(node1['labels'])
        importance2 = StructuralComparator._get_node_importance(node2['labels'])
        
        # Compare connectivity (degree difference)
        degree_diff = abs(node1['degree'] - node2['degree']) / max(node1['degree'], node2['degree'], 1)
        
        # Higher cost for mismatching important nodes
        importance_diff = abs(importance1 - importance2)
        
        return 0.7 * importance_diff + 0.3 * degree_diff

    @staticmethod
    def _node_deletion_cost(node: Dict[str, Any]) -> float:
        """Cost of deleting a node based on its structural importance"""
        importance = StructuralComparator._get_node_importance(node['labels'])
        degree = node.get('degree', 1)
        
        # Higher cost for deleting well-connected or important nodes
        return importance * (1 + 0.2 * degree)

    @staticmethod
    def _node_insertion_cost(node: Dict[str, Any]) -> float:
        """Cost of inserting a node based on its structural importance"""
        return StructuralComparator._node_deletion_cost(node)

    @staticmethod
    def _edge_substitution_cost(edge1: Dict[str, Any], edge2: Dict[str, Any]) -> float:
        """
        Calculate cost of substituting one edge for another based on:
        - Edge type
        - Connected nodes types
        """
        if not StructuralComparator._edge_match(edge1, edge2):
            return 1.0
            
        # Compare connected nodes importance
        source1_imp = StructuralComparator._get_node_importance(edge1['source_labels'])
        target1_imp = StructuralComparator._get_node_importance(edge1['target_labels'])
        source2_imp = StructuralComparator._get_node_importance(edge2['source_labels'])
        target2_imp = StructuralComparator._get_node_importance(edge2['target_labels'])
        
        # Cost based on difference in endpoint importance
        endpoint_diff = (abs(source1_imp - source2_imp) + abs(target1_imp - target2_imp)) / 2
        
        return endpoint_diff

    @staticmethod
    def _edge_deletion_cost(edge: Dict[str, Any]) -> float:
        """Cost of deleting an edge based on its structural importance"""
        # Higher cost for edges connecting important nodes
        source_imp = StructuralComparator._get_node_importance(edge['source_labels'])
        target_imp = StructuralComparator._get_node_importance(edge['target_labels'])
        return 0.5 * (source_imp + target_imp)

    @staticmethod
    def _edge_insertion_cost(edge: Dict[str, Any]) -> float:
        """Cost of inserting an edge"""
        return StructuralComparator._edge_deletion_cost(edge)

    @staticmethod
    def _get_node_importance(labels: Set[str]) -> float:
        """
        Calculate importance weight based on node type.
        Higher values for structurally significant points and vectors.
        """
        importance_weights = {
            'CornerPoint': 1.0,      # Highest importance - defines shape corners
            'IntersectionPoint': 1.0, # Equally important - defines structure connections
            'EndPoint': 0.8,         # Important - defines boundaries
            'Vector': 0.7,           # Important - defines connections between points
            'Point': 0.4             # Basic points
        }
        
        max_importance = 0.4  # Default importance
        for label in labels:
            if label in importance_weights:
                max_importance = max(max_importance, importance_weights[label])
        
        return max_importance

    @staticmethod
    def _normalize_distance(ged: float, g1: nx.Graph, g2: nx.Graph) -> float:
        """Normalize the graph edit distance to a similarity score"""
        max_possible_distance = (
            len(g1.nodes) + len(g2.nodes) +  # Cost of deleting all nodes
            len(g1.edges) + len(g2.edges)     # Cost of deleting all edges
        )
        return 1 - (ged / max_possible_distance if max_possible_distance > 0 else 0)
