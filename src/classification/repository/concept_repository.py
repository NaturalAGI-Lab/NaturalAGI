from typing import List
from neo4j import GraphDatabase
import networkx as nx

from graph_similarity.neo4j_to_networkx import Neo4jToNetworkX


class ConceptRepository:

    def __init__(self, neo4j_dsn: str, neo4j_user: str, neo4j_pass: str):
        self.neo4j_dsn = neo4j_dsn
        self.neo4j_user = neo4j_user
        self.neo4j_pass = neo4j_pass
        self.driver = GraphDatabase.driver(
            neo4j_dsn, auth=(neo4j_user, neo4j_pass), max_connection_lifetime=200
        )

    def close(self):
        self.driver.close()

    def get_all_concept_ids(self) -> List[str]:
        with self.driver.session() as session:
            concept_query = """
            MATCH (c)
            WITH DISTINCT c.concept_id AS concept_id
            RETURN concept_id
            """
            return [
                record["concept_id"]
                for record in session.run(concept_query)
                if record["concept_id"] is not None
            ]

    def get_concept_graph(self, concept_id: str) -> nx.Graph:
        query = """
            MATCH (n {concept_id: $concept_id})
            WHERE n:Point OR n:Vector OR n:StartPoint
            WITH n, labels(n) AS node_labels, properties(n) as node_props
            OPTIONAL MATCH (n)-[r]-(m {concept_id: $concept_id})
            WITH n, node_labels, r, m, node_props
            RETURN elementId(n) AS node_id, 
                node_labels,
                node_props,
                type(r) AS rel_type, 
                elementId(m) AS target_id
        """
        with self.driver.session() as session:
            result = session.run(query, concept_id=concept_id)
            return Neo4jToNetworkX.build_networkx_graph(result)
