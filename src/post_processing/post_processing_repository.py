import logging

from neo4j import GraphDatabase, ManagedTransaction

logging.basicConfig(level=logging.DEBUG)


class PostProcessingRepository:
    PROJECTION_NAME = "agi_projection"

    def __init__(self, uri, user, password):
        logging.info("Initializing Neo4jConnection")
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logging.info("Database connection established")
        except Exception as e:
            logging.error(f"Error establishing database connection: {e}")
            raise

    def close(self):
        try:
            self.driver.close()
            logging.info("Database connection closed")
        except Exception as e:
            logging.error(f"Error closing database connection: {e}")
            raise

    def merge_nodes_location(self, node_labels: list[str]):
        logging.info("Starting merge_vector_location method")
        with self.driver.session() as session:
            for node_label in node_labels:
                session.write_transaction(self._merge_node_transaction, node_label)

    def rank_nodes(self):
        logging.info("Starting rank_nodes method")
        with self.driver.session() as session:
            session.write_transaction(self._create_graph_projection)
            session.write_transaction(self._rank_nodes_transaction)
            session.write_transaction(self._degree_centrality)
            session.write_transaction(self._delete_nodes_with_low_degree)
            session.write_transaction(self._delete_graph_projection)

    def _merge_node_transaction(self, tx: ManagedTransaction, node_label: str):
        query = f"""
            MERGE (unified:{node_label} {{name: 'Unified Node'}})
            WITH unified
            MATCH (vl:{node_label})-[r]-()
            WITH unified, vl, collect(r) AS rels
            CALL apoc.refactor.mergeNodes([unified, vl], {{mergeRels: true}}) YIELD node
            RETURN node
        """
        tx.run(query)

    def _create_graph_projection(self, tx: ManagedTransaction):
        try:
            create_query = f"""
                CALL gds.graph.project('{PostProcessingRepository.PROJECTION_NAME}', '*', '*')
                """
            tx.run(create_query)
        except Exception as e:
            logging.error(f"Error creating graph projection: {e}")
            raise

    def _rank_nodes_transaction(self, tx: ManagedTransaction):
        query = f"""
            CALL gds.pageRank.write('{PostProcessingRepository.PROJECTION_NAME}', {{
                maxIterations: 20,
                dampingFactor: 0.85,
                writeProperty: 'nodeScore'
            }}) YIELD nodePropertiesWritten
        """
        tx.run(query)

    def _degree_centrality(self, tx: ManagedTransaction):
        query = f"""
            CALL gds.degree.write('{PostProcessingRepository.PROJECTION_NAME}', {{
                writeProperty: 'degreeScore',
                orientation: 'UNDIRECTED'
            }}) YIELD nodePropertiesWritten
        """
        tx.run(query)

    def _delete_nodes_with_low_degree(self, tx: ManagedTransaction):
        query = """
            CALL {
                MATCH (n)
                WHERE NOT n:Vector AND NOT n:AnglePoint
                WITH n.degreeScore AS degreeScore
                RETURN apoc.agg.percentiles(degreeScore, [0.995])[0] AS thresholdDegreeScore
            }
            WITH thresholdDegreeScore
            MATCH (n)
            WHERE NOT n:Vector AND NOT n:AnglePoint
            AND n.degreeScore <= thresholdDegreeScore
            DETACH DELETE n
        """
        tx.run(query)

    def _delete_graph_projection(self, tx: ManagedTransaction):
        query = f"""
            CALL gds.graph.drop('{PostProcessingRepository.PROJECTION_NAME}')
        """
        tx.run(query)
