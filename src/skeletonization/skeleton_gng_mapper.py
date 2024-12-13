import logging
import uuid
import numpy as np
import networkx as nx
from skimage.morphology import skeletonize
from skimage.util import img_as_ubyte
import gng
from rdp import rdp
from settings import Settings
from typing import List


class SkeletonGNGMapper:
    def __init__(
        self,
        context,
        settings: Settings,
        skeletonization_threshold: int = None,
        simplification_epsilon: float = None,
    ):
        self.context = context
        self.settings = settings
        self.min_threshold = 20  # Minimum threshold value
        self.threshold_step = 10  # Step to decrease threshold
        self.skeletonization_threshold = (
            skeletonization_threshold or self.settings.skeletonization_threshold
        )
        self.simplification_epsilon = (
            simplification_epsilon or self.settings.simplification_epsilon
        )

    def process_image(self, image):
        try:
            self.context.logger.info(
                f"Processing image with skeletonization threshold: {self.skeletonization_threshold} "
                f"and simplification epsilon: {self.simplification_epsilon}"
            )
            current_threshold = self.skeletonization_threshold

            while current_threshold >= self.min_threshold:
                try:
                    skeleton = self._skeletonize(image, threshold=current_threshold)
                    self.context.logger.debug(f"Skeleton created with threshold {current_threshold}")
                    
                    points = self._skeleton_to_points(skeleton)
                    self.context.logger.debug(f"Extracted {len(points)} points from skeleton")
                    
                    net = self._fit_gng(points)
                    self.context.logger.debug("GNG network fitted")
                    
                    simplified_network = self._simplify_network(net, self.simplification_epsilon)
                    self.context.logger.debug(f"Network simplified into {len(simplified_network)} segments")
                    
                    graph = self._to_networkx(simplified_network)
                    self.context.logger.debug(f"Created graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")

                    if nx.is_connected(graph):
                        return graph

                    current_threshold -= self.threshold_step

                except Exception as e:
                    self.context.logger.error(f"Error processing with threshold {current_threshold}: {str(e)}")
                    current_threshold -= self.threshold_step
                    continue

            raise Exception("Could not create connected graph with any threshold")
            
        except Exception as e:
            self.context.logger.error(f"Failed to process image: {str(e)}")
            raise

    def _skeletonize(self, image, threshold: int):
        binary = image > threshold
        skeleton = skeletonize(binary)
        return skeleton

    def _skeleton_to_points(self, skeleton: np.ndarray):
        points = []
        h, w = skeleton.shape
        for y in range(h):
            for x in range(w):
                if skeleton[y, x] > 0:
                    points.append([x, y])
        return np.array(points)

    def _fit_gng(self, points):
        return gng.fit(points, self.settings)

    def _simplify_network(self, net, epsilon: float = 1.0) -> List[np.ndarray]:
        # Find endpoints and intersections
        degree = np.sum(net.C, axis=0)
        endpoints = set(np.where(degree == 1)[0])
        intersections = set(np.where(degree > 2)[0])
        
        simplified_segments = []
        visited_edges = set()
        
        def traverse_segment(start: int, current: int) -> tuple[List[np.ndarray], int]:
            segment = [net.w[start]]
            while current not in endpoints and current not in intersections:
                segment.append(net.w[current])
                neighbors = set(np.where(net.C[current] == 1)[0]) - {start}
                if not neighbors:
                    break
                start, current = current, neighbors.pop()
            segment.append(net.w[current])
            return segment, current

        def process_node(node: int) -> None:
            neighbors = set(np.where(net.C[node] == 1)[0])
            for neighbor in neighbors:
                edge = tuple(sorted([node, neighbor]))  # Sort to ensure consistent edge representation
                if edge not in visited_edges:
                    visited_edges.add(edge)
                    segment, end = traverse_segment(node, neighbor)
                    if len(segment) > 2:
                        simplified_segment = rdp(np.array(segment), epsilon)
                        # Only add if endpoints are preserved
                        if np.array_equal(simplified_segment[0], segment[0]) and np.array_equal(simplified_segment[-1], segment[-1]):
                            simplified_segments.append(simplified_segment)
                    else:
                        # Always keep segments of length 2 to maintain connectivity
                        simplified_segments.append(np.array(segment))
                    if end != neighbor:
                        process_node(end)

        # Process all endpoints and intersections
        for node in endpoints.union(intersections):
            process_node(node)
        
        return simplified_segments

    def _to_networkx(self, simplified_network: List[List[np.ndarray]]) -> nx.Graph:
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
