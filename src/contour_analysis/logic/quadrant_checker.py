from neo4j import ManagedTransaction


def check_quadrant_change(
    tx: ManagedTransaction, vector1_id: str, vector2_id: str
) -> bool:
    """
    Check if there is a change in quadrant between two vectors.

    Parameters:
    - tx (ManagedTransaction): The Neo4j transaction object.
    - vector1_id (str): The ID of the first vector.
    - vector2_id (str): The ID of the second vector.

    Returns:
    - bool: True if there is a change in quadrant, False otherwise.
    """
    vector1_quadrant = _get_vector_quadrant(tx, vector1_id)
    vector2_quadrant = _get_vector_quadrant(tx, vector2_id)

    return vector1_quadrant != vector2_quadrant


def mark_quadrant_change(
    tx: ManagedTransaction, vector1_id: str, vector2_id: str, image_id: str, session_id: str
) -> None:
    """
    Mark the change in quadrant between two vectors.
    As well as create a CriticalPoint at the angle between the vectors, so we know it's a critical point.

    Parameters:
    - tx (ManagedTransaction): The Neo4j transaction object.
    - vector1_id (str): The ID of the first vector.
    - vector2_id (str): The ID of the second vector.
    - image_id (str): The ID of the image.
    - session_id (str): The ID of the session.
    """
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})
        MATCH (v2:Vector {vector_id: $vector2_id})
        // CREATE (quad_change:QuadrantChange:Feature {image_id: $image_id})
        // CREATE (v1)-[:HAS_QUADRANT_CHANGE]->(quad_change)-[:HAS_QUADRANT_CHANGE]->(v2)
        WITH v1, v2
        MATCH (v1)--(ap:IntersectionPoint)--(v2)
        MERGE (ap)-[:IS_CRITICAL_POINT]->(cp:CriticalPoint:Feature {reason: 'Quadrant Change', session_id: $session_id})
        ON CREATE SET cp.samples = [$image_id]
        ON MATCH SET cp.samples = CASE WHEN $image_id IN cp.samples THEN cp.samples ELSE cp.samples + [$image_id] END
    """
    tx.run(query, vector1_id=vector1_id, vector2_id=vector2_id, image_id=image_id, session_id=session_id)


def _get_vector_quadrant(tx: ManagedTransaction, vector_id: str) -> int:
    """
    Get the quadrant of a vector.

    Args:
        tx (ManagedTransaction): The Neo4j transaction object.
        vector_id (str): The ID of the vector.

    Returns:
        int: Quadrant value of the vector.
    """

    print(f"Quadrant check, vector:{vector_id}")
    query: str = """
        MATCH (v:Vector {vector_id: $vector_id})--(quadrant:Quadrant)
        RETURN quadrant.value AS quadrant
    """
    return tx.run(query, vector_id=vector_id).single()["quadrant"]