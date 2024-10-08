# TODO maybe to move to the another Nuclio function

import logging
from neo4j import ManagedTransaction, Result


def analyze_exposition(tx: ManagedTransaction, image_id: str, session_id: str) -> None:
    """
    Analyzes the contour development for a given image.
    The contour development is considered to be monotonic if all the vectors have the same direction.
    The contour development is considered to be non-monotonic if there are vectors with different directions.

    Args:
        tx (ManagedTransaction): The managed transaction object for database operations.
        image_id (int): The ID of the image to analyze.
        session_id (str): The ID of the session to analyze.
    Returns:
        None
    """
    logging.info(f"Analyzing exposition for image {image_id}")
    _analyze_contour_development(tx, image_id, session_id)
    _analyze_contour_type(tx, image_id, session_id)


def _analyze_contour_development(tx: ManagedTransaction, image_id: str, session_id: str) -> None:
    logging.info(f"Analyzing contour development for image {image_id}")
    query = """
        MATCH (vectorDirection:VectDirection)--(:Vector {image_id: $image_id})
        RETURN vectorDirection.direction
    """
    result: Result = tx.run(query, image_id=image_id)
    result_list = set(result)

    if len(result_list) == 0:
        logging.warning(f"No vector directions found for image {image_id}")
        return
    elif len(result_list) == 1:
        _mark_monotony_development(tx, image_id, session_id)
    else:
        _mark_non_monotony_development(tx, image_id, session_id)
        return


def _mark_monotony_development(tx: ManagedTransaction, image_id: str, session_id: str) -> None:
    logging.info(f"Marking monotony development for image {image_id}")
    query = """
        MATCH (vector:Vector {image_id: $image_id})
        MERGE (mono:Monotony:Feature {session_id: $session_id})
        ON CREATE SET mono.samples = [$image_id]
        ON MATCH SET mono.samples = CASE WHEN $image_id IN mono.samples THEN mono.samples ELSE mono.samples + [$image_id] END
        CREATE (vector)-[:HAS_MONOTONY]->(mono)
    """
    tx.run(query, image_id=image_id, session_id=session_id)


def _mark_non_monotony_development(tx: ManagedTransaction, image_id: str, session_id: str) -> None:
    logging.info(f"Marking non-monotony development for image {image_id}")
    query = """
        MATCH (vector:Vector {image_id: $image_id})
        MERGE (nonMono:NonMonotony:Feature {session_id: $session_id})
        ON CREATE SET nonMono.samples = [$image_id]
        ON MATCH SET nonMono.samples = CASE WHEN $image_id IN nonMono.samples THEN nonMono.samples ELSE nonMono.samples + $image_id END
        CREATE (vector)-[:HAS_NON_MONOTONY]->(nonMono)
    """
    tx.run(query, image_id=image_id, session_id=session_id)


def _analyze_contour_type(tx: ManagedTransaction, image_id: str, session_id: str) -> None:
    """
    Analyzes the contour type for a given image. If query is able to find the path from the
    starting vector back to itself, then the contour is considered to be closed.

    Args:
        tx (ManagedTransaction): The managed transaction object for database operations.
        image_id (int): The ID of the image to analyze.

    Returns:
        None
    """

    query = """
        MATCH (v:Vector {image_id: $image_id})
        CALL apoc.path.expand(v, '>', 'IntersectionPoint|Vector', 0, 100) YIELD path
        WHERE last(nodes(path)) = v AND size(nodes(path)) > 2
        RETURN path
    """
    result: Result = tx.run(query, image_id=image_id)
    result_list = list(result)

    if result_list:
        # If a path is found, create a 'Closed' node and link it to all Vector and IntersectionPoint nodes
        query = """
            MATCH (n)
            WHERE (n:Vector OR n:IntersectionPoint) AND n.image_id = $image_id
            MERGE (closed:Closed:Feature {session_id: $session_id})
            ON CREATE SET closed.samples = [$image_id]
            ON MATCH SET closed.samples = CASE WHEN $image_id IN closed.samples THEN closed.samples ELSE closed.samples + $image_id END
            MERGE (n)-[:HAS_CONTOUR_TYPE]->(closed)
        """
    else:
        # If no path is found, create an 'Open' node and link it to all Vector and IntersectionPoint nodes
        query = """
            MATCH (n)
            WHERE (n:Vector OR n:IntersectionPoint) AND n.image_id = $image_id
            MERGE (open:Open:Feature {session_id: $session_id})
            ON CREATE SET open.samples = [$image_id]
            ON MATCH SET open.samples = CASE WHEN $image_id IN open.samples THEN open.samples ELSE open.samples + $image_id END
            MERGE (n)-[:HAS_CONTOUR_TYPE]->(open)
        """

    tx.run(query, image_id=image_id, session_id=session_id)
    logging.info(f"_analyze_contour_type: {result_list}")
