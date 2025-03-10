import networkx as nx
from typing import Dict, List, Any
from neo4j import ManagedTransaction


class NetworkxToNeo4j:
    @staticmethod
    def create_structure(
        tx: ManagedTransaction, graph: nx.Graph, session_id: str, image_id: str
    ) -> None:
        """Creates structural nodes and relationships in Neo4j from a NetworkX graph"""

        # First create all nodes
        for node, data in graph.nodes(data=True):
            labels = list(data.get("labels", set()))
            if not labels:
                continue

            # Create node properties
            props = {"session_id": session_id, "image_id": image_id}
            # Add all other properties except labels
            props.update({k: v for k, v in data.items() if k != "labels"})

            # Create node with all its labels
            labels_str = ":".join(labels)
            query = f"""
                CREATE (n:{labels_str} $props)
                RETURN n
            """
            tx.run(query, props=props)

        # Then create all edges
        for u, v in graph.edges():
            query = """
            MATCH (u), (v)
            WHERE u.session_id = $session_id 
              AND v.session_id = $session_id
              AND id(u) = $u_id 
              AND id(v) = $v_id
            CREATE (u)-[:CONNECTS]->(v)
            """
            tx.run(query, session_id=session_id, u_id=u, v_id=v)

    @staticmethod
    def convert(graph: nx.Graph) -> List[Dict[str, Any]]:
        """
        Convert a NetworkX graph to a format that can be used to create nodes and
        relationships in Neo4j.

        Args:
            graph: NetworkX graph to convert

        Returns:
            List of dictionaries representing nodes and relationships
        """
        result = []

        # First add all nodes
        for node, data in graph.nodes(data=True):
            node_data = {
                "uuid": str(node),
                "type": "node",
                "properties": {k: v for k, v in data.items()},
            }

            # Handle labels separately
            if "labels" in data:
                if isinstance(data["labels"], (list, set)):
                    node_data["labels"] = list(data["labels"])
                else:
                    node_data["labels"] = [str(data["labels"])]
            else:
                node_data["labels"] = []

            result.append(node_data)

        # Then add all edges
        for u, v, data in graph.edges(data=True):
            edge_data = {
                "source": str(u),
                "target": str(v),
                "type": "relationship",
                "relationship_type": data.get("type", "CONNECTS"),
                "properties": {k: v for k, v in data.items() if k != "type"},
            }
            result.append(edge_data)

        return result
