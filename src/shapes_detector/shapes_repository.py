import math

from neo4j import GraphDatabase


class ShapesRepository:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def find_and_create_shapes(self):
        with self.driver.session() as session:
            result = session.write_transaction(self._find_and_create_shapes)
            return result

    @staticmethod
    def _find_and_create_shapes(tx):
        query = """
            MATCH path=(l:Line)-[*6..12]-(l) 
            WHERE ALL(node IN nodes(path)[1..-1] WHERE SINGLE(x IN nodes(path) WHERE x = node))
            WITH DISTINCT path, [node IN nodes(path) WHERE node:Line] AS lineNodes
            MERGE (contour:Contour)
            SET contour.lines_conout = SIZE(lineNodes) - 1
            WITH contour, lineNodes
            UNWIND lineNodes AS lineNode
            MERGE (lineNode)-[:COMPOSES]->(contour)
            RETURN contour
        """
        result = tx.run(query)
        print('Printing results')
        for record in result:
            print(record)
        return result

# TODO count of the number of lines
# MATCH path=(l:Line)-[*3..10]-(l) 
# WHERE ALL(node IN nodes(path)[1..-1] WHERE SINGLE(x IN nodes(path) WHERE x = node))
# RETURN size([node IN nodes(path) WHERE node:Line]) - 1


# TODO create Contour
# MATCH path=(l:Line)-[*3..10]-(l) 
# WHERE ALL(node IN nodes(path)[1..-1] WHERE SINGLE(x IN nodes(path) WHERE x = node))
# WITH [node in nodes(path) WHERE node:Line] as nodes, path
# CREATE (contour:Contour)
# SET contour.lines_count = size(nodes) - 1 
# FOREACH (node in nodes | CREATE (node)-[:COMPOSES]->(contour))
# RETURN contour