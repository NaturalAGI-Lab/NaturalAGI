from typing import List
from neo4j import GraphDatabase
import networkx as nx

from .neo4j_to_networkx import Neo4jToNetworkX
from common.decorator import timed


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

    @timed(label="get_all_concept_ids")
    def get_all_concept_ids(self) -> List[str]:
        with self.driver.session() as session:
            concept_query = """
            MATCH (c:Point)
            WHERE c.concept_id IS NOT NULL
            RETURN DISTINCT c.concept_id AS concept_id
            """
            return [
                record["concept_id"]
                for record in session.run(concept_query)
            ]

    def get_concept_graph(self, concept_id: str) -> nx.Graph:
        query = """
            CALL {
                MATCH (n:Point {concept_id: $concept_id}) RETURN n
                UNION ALL
                MATCH (n:Vector {concept_id: $concept_id}) RETURN n
                UNION ALL
                MATCH (n:StartPoint {concept_id: $concept_id}) RETURN n
            }
            WITH n, labels(n) AS node_labels, properties(n) as node_props
            OPTIONAL MATCH (n)-[r]-(m {concept_id: $concept_id})
            WITH n, node_labels, r, m, node_props
            RETURN elementId(n) AS node_id,
                node_labels,
                node_props,
                type(r) AS rel_type,
                elementId(r) AS rel_id,
                elementId(m) AS target_id
        """
        with self.driver.session() as session:
            result = session.run(query, concept_id=concept_id)
            return Neo4jToNetworkX.build_networkx_graph(result, is_concept=True)
