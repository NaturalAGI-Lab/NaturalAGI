from typing import List

import networkx as nx
import numpy as np
import uuid


class Converter:
    @staticmethod
    def convert_simplified_network_to_networkx(simplified_network: List[List[np.ndarray]]) -> nx.Graph:
        """
        Convert the simplified network to a NetworkX graph with labeled nodes and edge data.

        Args:
            simplified_network (List[List[np.ndarray]]): The simplified network as a list of segments,
                each segment is a list of points represented as numpy arrays.

        Returns:
            nx.Graph: A NetworkX graph with nodes labeled by coordinates and edges with endpoint data.
        """
        G = nx.Graph()
        for i, segment in enumerate(simplified_network):
            for j in range(len(segment) - 1):
                source_coord = tuple(segment[j])
                target_coord = tuple(segment[j + 1])

                # Create unique identifiers for source and target nodes
                source_id = hash(source_coord)
                target_id = hash(target_coord)

                # Add source node with attributes if not already present
                if source_id not in G:
                    G.add_node(
                        source_id,
                        x=source_coord[0],
                        y=source_coord[1],
                        uuid=str(uuid.uuid4()),
                    )

                # Add target node with attributes if not already present
                if target_id not in G:
                    G.add_node(
                        target_id,
                        x=target_coord[0],
                        y=target_coord[1],
                        uuid=str(uuid.uuid4()),
                    )

                # Calculate edge length
                length = np.linalg.norm(np.array(target_coord) - np.array(source_coord))

                # Add edge with segment ID and endpoint information
                G.add_edge(
                    source_id,
                    target_id,
                    segment_id=i,
                    uuid=str(uuid.uuid4()),
                    x1=source_coord[0],
                    y1=source_coord[1],
                    x2=target_coord[0],
                    y2=target_coord[1],
                    length=length,
                )

        return G