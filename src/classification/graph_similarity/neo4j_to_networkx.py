from typing import Dict
import networkx as nx
from neo4j import Session

class Neo4jToNetworkX:
    """Responsible for converting Neo4j graphs to NetworkX format"""
    
    @staticmethod
    def extract_image_graph(session: Session, image_id: str) -> nx.Graph:
        """Extract graph from Neo4j and convert to NetworkX format."""
        query = """
        MATCH (n {image_id: $image_id})
        WHERE n:Point OR n:Vector
        WITH n, labels(n) as node_labels
        OPTIONAL MATCH (n)-[r]-(m {image_id: $image_id})
        WITH n, node_labels, r, m, 
             COUNT(r) as degree  // Fixed degree calculation
        RETURN id(n) as node_id, 
               node_labels, 
               type(r) as rel_type, 
               id(m) as target_id,
               degree
        """
        result = session.run(query, image_id=image_id)
        return Neo4jToNetworkX._build_networkx_graph(result)
    
    @staticmethod
    def extract_concept_graph(session: Session, concept_id: str) -> nx.Graph:
        """Extract graph from Neo4j and convert to NetworkX format."""
        query = """
        MATCH (n {concept_id: $concept_id})
        WHERE n:Point OR n:Vector
        WITH n, labels(n) as node_labels
        OPTIONAL MATCH (n)-[r]-(m {concept_id: $concept_id})
        WITH n, node_labels, r, m, 
             COUNT(r) as degree  // Fixed degree calculation
        RETURN id(n) as node_id, 
               node_labels, 
               type(r) as rel_type, 
               id(m) as target_id,
               degree
        """
        result = session.run(query, concept_id=concept_id)
        return Neo4jToNetworkX._build_networkx_graph(result)
    
    @staticmethod
    def _build_networkx_graph(result) -> nx.Graph:
        G = nx.Graph()
        nodes: Dict[int, Dict] = {}  # Store node data including degree
        
        # First pass: collect all nodes and their degrees
        for record in result:
            node_id = record["node_id"]
            if node_id not in nodes:
                nodes[node_id] = {
                    "labels": set(record["node_labels"]),
                    "degree": record["degree"]
                }
        
        # Add nodes to graph
        for node_id, node_data in nodes.items():
            G.add_node(node_id, **node_data)
        
        # Add edges
        for record in result:
            if record["target_id"] is not None:
                G.add_edge(
                    record["node_id"], 
                    record["target_id"], 
                    type=record["rel_type"]
                )
        
        return G

