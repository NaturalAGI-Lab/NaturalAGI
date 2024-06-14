import logging

from neo4j import ManagedTransaction

from logic.repository.vector_repository import VectorRepository


def merge_graphs(tx: ManagedTransaction) -> None:
    """
    Merges the graphs of the structures in the database.
    It groups the structural elements (Vector, AnglePoint) by image_id and element id, then build the string representation
    of the properties of the structural elements in each group.
    Then we use Levenshtein distance to compare the string representations of the groups.
    If the distance is less than a certain threshold, we merge the groups.

    Args:
        tx (ManagedTransaction): The managed transaction object for database operations.

    Returns:
        None
    """
    vectors = VectorRepository.get_all_vectors(tx)
    for i, vector1 in enumerate(vectors):
        logging.info(f"Processing vector {i + 1}/{len(vectors)}. Details: {vector1}")
        min_distance = float('inf')
        closest_vector = None
        for vector2 in vectors:
            if vector1.image_id != vector2.image_id:
                distance = vector1.distance(vector2)
                if distance < min_distance:
                    min_distance = distance
                    closest_vector = vector2

        if closest_vector:
            logging.info(f"Found similar vectors with min distance {min_distance}")
            logging.info(f"Vector 1: {vector1}")
            logging.info(f"Vector 2: {closest_vector}")
