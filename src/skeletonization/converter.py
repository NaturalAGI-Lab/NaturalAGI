from typing import List

import networkx as nx
import numpy as np
import uuid


class Converter:
    @staticmethod
    def convert_simplified_network_to_networkx(
        simplified_network: List[List[np.ndarray]],
    ) -> nx.Graph:
        """
        Convert the simplified network to a NetworkX graph with labeled nodes and edge data.

        Args:
            simplified_network (List[List[np.ndarray]]): The simplified network as a list of segments,
                each segment is a list of points represented as numpy arrays.

        Returns:
            nx.Graph: A NetworkX graph with nodes labeled by coordinates and edges with endpoint data.
        """
        G = nx.Graph()
        for _, segment in enumerate(simplified_network):
            for j in range(len(segment) - 1):
                source_coord = tuple(segment[j])
                target_coord = tuple(segment[j + 1])

                # Create unique identifiers for source and target nodes
                source_node_hash = hash(source_coord)
                target_node_hash = hash(target_coord)
                source_id = str(uuid.uuid4())
                target_id = str(uuid.uuid4())

                # Add source node with attributes if not already present
                if source_node_hash not in G:
                    G.add_node(
                        source_node_hash,
                        x=source_coord[0],
                        y=source_coord[1],
                        id=source_id,
                    )

                # Add target node with attributes if not already present
                if target_node_hash not in G:
                    G.add_node(
                        target_node_hash,
                        x=target_coord[0],
                        y=target_coord[1],
                        id=target_id,
                    )

                # Calculate edge length
                length = np.linalg.norm(np.array(target_coord) - np.array(source_coord))

                # Add edge with segment ID and endpoint information
                G.add_edge(
                    source_node_hash,
                    target_node_hash,
                    id=str(uuid.uuid4()),
                    x1=source_coord[0],
                    y1=source_coord[1],
                    x2=target_coord[0],
                    y2=target_coord[1],
                    length=length,
                )

        return G
