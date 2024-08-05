import logging


def compare_vector_magnitude_and_create_nodes(tx, vector1_id: str, vector2_id: str, image_id: str, session_id: str):
    logging.info(f"Comparing vector magnitudes and creating respective nodes between vector1:{vector1_id} and vector2{vector2_id}")
    # First, compare the magnitudes to determine the label
    compare_query = """
      MATCH (v1:Vector {vector_id: $vector1_id})-[:HAS_LENGTH]->(length1:Length),
            (v2:Vector {vector_id: $vector2_id})-[:HAS_LENGTH]->(length2:Length)
      RETURN CASE WHEN length1.value > length2.value THEN 'VectLonger'
                  WHEN length1.value < length2.value THEN 'VectShorter'
                  ELSE 'VectEqual' END AS label
    """
    result = tx.run(compare_query, vector1_id=vector1_id, vector2_id=vector2_id, image_id=image_id)
    label = result.single()[0]

    create_node_query = f"""
      MATCH (v1:Vector {{vector_id: $vector1_id}}),
                  (v2:Vector {{vector_id: $vector2_id}})
      MERGE (vect:{label}:Feature {{session_id: $session_id}})
      ON CREATE SET vect.samples = [$image_id]
      ON MATCH SET vect.samples = CASE WHEN $image_id IN vect.samples THEN vect.samples ELSE vect.samples + [$image_id] END
      MERGE (v1)-[:IN]->(vect)-[:OUT]->(v2)
    """
    tx.run(create_node_query, vector1_id=vector1_id, vector2_id=vector2_id, image_id=image_id, session_id=session_id)
