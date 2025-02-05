import networkx as nx
from neo4j import ManagedTransaction

class NetworkXToNeo4j:
    @staticmethod
    def create_structure(
        tx: ManagedTransaction, 
        graph: nx.Graph, 
        session_id: str,
        image_id: str
    ) -> None:
        """Creates structural nodes and relationships in Neo4j from a NetworkX graph"""
        
        # First create all nodes
        for node, data in graph.nodes(data=True):
            labels = list(data.get("labels", set()))
            if not labels:
                continue
                
            # Create node properties
            props = {
                "session_id": session_id,
                "image_id": image_id
            }
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