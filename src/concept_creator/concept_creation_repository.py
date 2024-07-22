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
            session.write_transaction(self.unwind)

            # session.write_transaction(self._link_features_to_concept)
            # session.write_transaction(self._remove_structural_elements)
            
    def unwind(self, tx: ManagedTransaction):
        # Step 1: Fetch the AnglePointCount node
        query = """
            MATCH (apc:AnglePointsCount)
            RETURN apc.count AS count
        """
        result = tx.run(query)
        count_data = result.single()
        if not count_data:
            raise ValueError("No AnglePointCount node found")
        
        count = count_data["count"]

        # Step 2: Create new AnglePoints based on the count
        create_query = """
            UNWIND range(1, $count) AS idx
            CREATE (ap:AnglePoint {id: idx})
            RETURN collect(ap) AS angle_points
        """
        result = tx.run(create_query, count=count)
        angle_points = result.single()["angle_points"]

        # Step 3: Connect the new AnglePoints to each other
        for i in range(len(angle_points) - 1):
            tx.run("""
                MATCH (ap1:AnglePoint), (ap2:AnglePoint)
                WHERE id(ap1) = $id1 AND id(ap2) = $id2
                CREATE (ap1)-[:NEXT]->(ap2)
            """, id1=angle_points[i].id, id2=angle_points[i + 1].id)

        # Step 4: Connect all remaining nodes to the new AnglePoints
        connect_query = """
            MATCH (n)
            WHERE NOT n:AnglePoint AND NOT n:AnglePointCount
            WITH collect(n) AS nodes
            UNWIND $angle_point_ids AS ap_id
            MATCH (ap:AnglePoint) WHERE id(ap) = ap_id
            UNWIND nodes AS n
            CREATE (n)-[:CONNECTED_TO]->(ap)
        """
        tx.run(connect_query, angle_point_ids=[ap.id for ap in angle_points])

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
            WITH vector99thPercentile, apoc.agg.percentiles(anglePointCount, [0.99]) AS anglePoint99thPercentile
            RETURN vector99thPercentile[0], anglePoint99thPercentile[0]
        """
        result = tx.run(query).single()
        logging.info(
            f"99th percentile of the vector count: {result[0]}, angle point: {result[1]}"
        )
        return result[0], result[1]