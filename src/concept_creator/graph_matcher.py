import logging

from neo4j import GraphDatabase


class GraphMatcher:
    def __init__(self, uri, user, password):
        logging.info("Initializing GraphMatcher")
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

    def match_graph(self):
        with self.driver.session() as session:
            result = session.read_transaction(self._match_graph)
            return result

    def _match_graph(self, tx):
        # Get starting point of concept graph (node_index = 'C') and starting points of all the other graphs (node_index = '$index')
        # traverse the graph in the way of line -> critical point (reason: first line)
        query = """
            MATCH (startingPoint:StartingPoint {node_index: 'C'})
        """
        return
