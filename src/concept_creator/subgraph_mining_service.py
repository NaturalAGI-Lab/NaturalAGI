from typing import Dict, List, Set, Tuple, Any
from neo4j import GraphDatabase, Session
import networkx as nx
from gspan_mining import gSpan
import numpy as np
from neo4j_to_networkx import Neo4jToNetworkX

class SubgraphMiningService:
    def __init__(self, neo4j_dsn: str, neo4j_user: str, neo4j_pass: str, epsilon: float = 0.1):
        self.driver = GraphDatabase.driver(neo4j_dsn, auth=(neo4j_user, neo4j_pass))
        self.epsilon = epsilon

    def calculate_weights(self) -> None:
        """Calculate weights for nodes based on their involvement in frequent subgraphs across all concepts"""
        with self.driver.session() as session:
            # Get all concept graphs
            concept_graphs = self._get_all_concept_graphs(session)
            
            # Convert concept graphs to gSpan format and maintain mappings
            gspan_graphs, graph_mappings = self._convert_to_gspan_format(concept_graphs)
            
            # Write graphs to file for gSpan
            with open('graphs.dat', 'w') as f:
                for g in gspan_graphs:
                    f.write(g)
            
            # Mine frequent subgraphs
            support_threshold = 2  # Adjust based on your needs
            gs = gSpan(
                database_file_name='graphs.dat',
                min_support=support_threshold,
                is_undirected=True,
                min_num_vertices=3,
            )
            gs.run()
            
            # Extract frequent subgraphs and their embeddings
            frequent_subgraphs = gs.graphs
            
            # Map frequent subgraphs back to original nodes
            node_frequencies = self._map_subgraphs_to_nodes(frequent_subgraphs, graph_mappings)
            
            # Calculate and update weights
            self._update_node_weights(session, node_frequencies)

    def _get_all_concept_graphs(self, session: Session) -> Dict[str, nx.Graph]:
        """Get NetworkX graphs for all concepts"""
        query = """
        MATCH (c:Concept)
        RETURN c.id AS concept_id
        """
        result = session.run(query)
        concept_graphs = {}
        
        for record in result:
            concept_id = record["concept_id"]
            graph = Neo4jToNetworkX.extract_concept_graph(session, concept_id)
            concept_graphs[concept_id] = graph
            
        return concept_graphs

    def _convert_to_gspan_format(self, graphs: Dict[str, nx.Graph]) -> Tuple[List[str], Dict[int, Dict[str, Any]]]:
        """Convert NetworkX graphs to gSpan format and maintain mappings"""
        gspan_graphs = []
        graph_mappings = {}  # Mapping from gSpan graph ID to concept ID and node mappings
        
        for graph_idx, (concept_id, graph) in enumerate(graphs.items()):
            gspan_str = "t # {}\n".format(graph_idx)
            node_map = {}
            reverse_node_map = {}
            
            for i, node in enumerate(graph.nodes()):
                node_map[node] = i
                reverse_node_map[i] = node  # Map gSpan node ID to original node ID
                label = graph.nodes[node].get("label", "0")
                gspan_str += "v {} {}\n".format(i, label)
            
            for u, v, data in graph.edges(data=True):
                edge_label = data.get("label", "0")
                gspan_str += "e {} {} {}\n".format(node_map[u], node_map[v], edge_label)
            
            gspan_graphs.append(gspan_str)
            graph_mappings[graph_idx] = {
                'concept_id': concept_id,
                'node_mapping': reverse_node_map
            }
        
        return gspan_graphs, graph_mappings

    def _map_subgraphs_to_nodes(
        self,
        frequent_subgraphs: List,
        graph_mappings: Dict[int, Dict[str, Any]]
    ) -> Dict[str, int]:
        """Map frequent subgraphs back to original nodes and count frequencies"""
        node_frequencies = {}  # Key: (concept_id, node_id), Value: frequency count

        for subgraph in frequent_subgraphs:
            frequency = subgraph.support
            # Assuming subgraph instances contain embeddings with graph IDs and node IDs
            for gid, instances in subgraph.instances.items():
                concept_id = graph_mappings[gid]['concept_id']
                node_mapping = graph_mappings[gid]['node_mapping']
                for instance in instances:
                    # instance.vertex_mappings maps subgraph node IDs to graph node IDs
                    for sg_node_id in instance.vertex_mappings:
                        original_node_id = node_mapping[instance.vertex_mappings[sg_node_id]]
                        node_key = (concept_id, original_node_id)
                        node_frequencies[node_key] = node_frequencies.get(node_key, 0) + 1  # Increment count
        
        return node_frequencies

    def _update_node_weights(
        self,
        session: Session,
        node_frequencies: Dict[Tuple[str, Any], int]
    ) -> None:
        """Update node weights in Neo4j based on frequencies"""
        # Calculate weights
        weights = {
            node_key: 1.0 / (freq + self.epsilon)
            for node_key, freq in node_frequencies.items()
        }
        
        # Normalize weights to [0, 1]
        max_weight = max(weights.values()) if weights else 1
        normalized_weights = {
            node_key: weight / max_weight
            for node_key, weight in weights.items()
        }
        
        # Update weights in Neo4j
        with session.begin_transaction() as tx:
            for (concept_id, node_id), weight in normalized_weights.items():
                print(concept_id, node_id, weight)
                # query = """
                # MATCH (c:Concept {id: $concept_id})-[:INCLUDES]->(n)
                # WHERE id(n) = $node_id
                # SET n.weight = $weight
                # """
                # tx.run(
                #     query,
                #     concept_id=concept_id,
                #     node_id=node_id,
                #     weight=weight
                # )
            tx.commit()
