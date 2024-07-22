from neo4j import ManagedTransaction

class Unwinder:
    """
    Unwinder should get the AnglePointCount node and create the new AnglePoints for each count from it and connect them by relations
    to the previous and next AnglePoints.
    All nodes that left should be connected by relations to all the AnglePoints.
    """

    def __init__(self, tx: ManagedTransaction):
        self.tx = tx

    def unwind(self):
        # Step 1: Fetch the AnglePointCount node
        query = """
            MATCH (apc:AnglePointCount)
            RETURN apc.count AS count
        """
        result = self.tx.run(query)
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
        result = self.tx.run(create_query, count=count)
        angle_points = result.single()["angle_points"]

        # Step 3: Connect the new AnglePoints to each other
        for i in range(len(angle_points) - 1):
            self.tx.run("""
                MATCH (ap1:AnglePoint {id: $id1}), (ap2:AnglePoint {id: $id2})
                CREATE (ap1)-[:NEXT]->(ap2)
            """, id1=angle_points[i].id, id2=angle_points[i + 1].id)

        # Step 4: Connect all remaining nodes to the new AnglePoints
        connect_query = """
            MATCH (n)
            WHERE NOT n:AnglePoint AND NOT n:AnglePointCount
            WITH collect(n) AS nodes
            UNWIND $angle_points AS ap
            UNWIND nodes AS n
            CREATE (n)-[:CONNECTED_TO]->(ap)
        """
        self.tx.run(connect_query, angle_points=[ap.id for ap in angle_points])