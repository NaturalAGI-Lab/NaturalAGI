import logging


def compare_vector_magnitude_and_create_nodes(tx, vector1_id: str, vector2_id: str):
    logging.info("Comparing vector magnitudes and creating respective nodes")
    # First, compare the magnitudes to determine the label
    compare_query = """
      MATCH (v1:Vector {vector_id: $vector1_id})-[:HAS_MAGNITUDE]->(magnitude1:VectorMagnitude),
            (v2:Vector {vector_id: $vector2_id})-[:HAS_MAGNITUDE]->(magnitude2:VectorMagnitude)
      RETURN CASE WHEN magnitude1.value > magnitude2.value THEN 'VectLonger'
                  WHEN magnitude1.value < magnitude2.value THEN 'VectShorter'
                  ELSE 'VectEqual' END AS label
    """
    result = tx.run(compare_query, vector1_id=vector1_id, vector2_id=vector2_id)
    label = result.single()[0]

    create_node_query = f"""
      MATCH (v1:Vector {{vector_id: $vector1_id}}),
                  (v2:Vector {{vector_id: $vector2_id}})
      MERGE (vect:{label})
      MERGE (v1)-[:IN]->(vect)-[:OUT]->(v2)
    """
    tx.run(create_node_query, vector1_id=vector1_id, vector2_id=vector2_id)
