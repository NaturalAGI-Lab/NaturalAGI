import logging

from neo4j import GraphDatabase, ManagedTransaction


class ConceptCreationRepository:
    def __init__(self, uri, user, password):
        logging.info("Initializing ConceptCreationRepository")
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

    def create_concept(self):
        logging.info("Starting create_concept method")
        with self.driver.session() as session:
            session.write_transaction(self._create_concept)
            session.write_transaction(self._link_features_to_concept)
            session.write_transaction(self._remove_structural_elements)

    def _create_concept(self, tx: ManagedTransaction):
        """# TODO new idea will be to create the new concept with some hash instead of name.
        This hash will be based on the structural elements and the features of the concept.
        So we can ensure that the concept is unique.
        """
        vectorsCount, anglePointsCount = (
            self._count_99_percentile_of_structural_elements(tx)
        )

        query = """
            MERGE (concept:TriangleConcept)
            MERGE (structElements:StructuralElements {vectorsCount: $vectorsCount, anglePointsCount: $anglePointsCount})
            MERGE (concept)-[:HAS_STRUCTURAL_ELEMENTS]->(structElements)
            RETURN concept
        """
        tx.run(query, vectorsCount=vectorsCount, anglePointsCount=anglePointsCount)

    def _link_features_to_concept(self, tx: ManagedTransaction):
        """Links all the features left from the statistical reduction to the new concept"""
        query = """
            MATCH (n)
            WHERE NOT (n:StructuralElements OR n:Vector OR n:AnglePoint OR n:TriangleConcept)
            MATCH (concept:TriangleConcept)
            MERGE (n)-[:IS_PART_OF_CONCEPT]->(concept)
        """
        tx.run(query)

    def _remove_structural_elements(self, tx: ManagedTransaction):
        query = """
            MATCH (vector:Vector), (anglePoint:AnglePoint)
            DETACH DELETE vector, anglePoint
        """
        tx.run(query)

    def _count_99_percentile_of_structural_elements(
        self, tx: ManagedTransaction
    ) -> tuple[int, int]:
        query = """
            MATCH (vector:Vector)
            WITH vector.image_id AS imageId, COUNT(vector) AS vectorCount
            WITH apoc.agg.percentiles(vectorCount, [0.99]) AS vector99thPercentile
            MATCH (anglePoint:AnglePoint)-[:IS_CRITICAL_POINT]->(cp:CriticalPoint {reason: 'Quadrant Change'})
            WITH anglePoint.image_id AS imageId, COUNT(anglePoint) AS anglePointCount, vector99thPercentile
            WITH vector99thPercentile, anglePointCount
            WITH vector99thPercentile, apoc.agg.percentiles(anglePointCount, [0.99]) AS anglePoint99thPercentile
            RETURN vector99thPercentile[0], anglePoint99thPercentile[0]
        """
        result = tx.run(query).single()
        logging.info(
            f"99th percentile of the vector count: {result[0]}, angle point: {result[1]}"
        )
        return result[0], result[1]
