import json
import networkx as nx
from neo4j import ManagedTransaction
import uuid
import logging

logger = logging.getLogger(__name__)


class NetworkxToNeo4j:
    @staticmethod
    def create_structure(
        tx: ManagedTransaction, graph: nx.Graph, concept_id: str
    ) -> None:
        """Creates structural nodes and relationships in Neo4j from a NetworkX graph"""
        logger.info(f"Creating structure for concept {concept_id}")
        # First create all nodes
        node_uuids = {}
        for node, data in graph.nodes(data=True):
            labels = list(data.get("labels", set()))
            if not labels:
                continue

            # Create node properties
            uu_id = str(uuid.uuid4())
            node_uuids[node] = uu_id
            props = {
                "concept_id": concept_id,
                "uuid": uu_id,
            }
            # Add all other properties except labels
            props.update({k: NetworkxToNeo4j.serialize_value(v) for k, v in data.items() if k != "labels"})

            # Create node with all its labels
            labels_str = ":".join(labels)
            query = f"""
                CREATE (n:{labels_str} $props)
                RETURN n
            """
            tx.run(query, props=props)

        # Then create all edges
        for u, v in graph.edges():
            u_uuid = node_uuids[u]
            v_uuid = node_uuids[v]
            query = """
            MATCH (u), (v)
            WHERE u.concept_id = $concept_id 
              AND v.concept_id = $concept_id
              AND u.uuid = $u_uuid 
              AND v.uuid = $v_uuid
            CREATE (u)-[:CONNECTED_TO]->(v)
            """
            tx.run(query, concept_id=concept_id, u_uuid=u_uuid, v_uuid=v_uuid)
        logger.info(f"Created structure for concept {concept_id}")
        logger.info(f"Created {len(graph.nodes())} nodes and {len(graph.edges())} edges")
        
    # Helper functions for serialization
    @staticmethod
    def is_primitive(value):
        return isinstance(value, (int, float, str, bool, type(None)))

    @staticmethod
    def is_list_of_primitives(value):
        return isinstance(value, list) and all(NetworkxToNeo4j.is_primitive(item) for item in value)

    @staticmethod
    def needs_serialization(value):
        if NetworkxToNeo4j.is_primitive(value):
            return False
        elif isinstance(value, list):
            return not NetworkxToNeo4j.is_list_of_primitives(value)
        else:
            return True

    @staticmethod
    def serialize_value(value):
        if NetworkxToNeo4j.needs_serialization(value):
            return json.dumps(value)
        else:
            return value
