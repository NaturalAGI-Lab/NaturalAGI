import numpy as np
import networkx as nx
from skimage.morphology import skeletonize
from skimage.util import img_as_ubyte
from ypstruct import structure
import gng
from rdp import rdp
from settings import Settings

class SkeletonGNGMapper:
    def __init__(self, settings: Settings):
        self.settings = settings

    def process_image(self, image):
        skeleton = self._skeletonize(image)
        points = self._skeleton_to_points(skeleton)
        net = self._fit_gng(points)
        simplified_network = self._simplify_network(net)
        graph = self._to_networkx(simplified_network)
        return graph

    def _skeletonize(self, image):
        binary = image > self.settings.skeletonization_threshold
        skeleton = skeletonize(binary)
        return img_as_ubyte(skeleton)

    def _skeleton_to_points(self, skeleton):
        return np.array(np.where(skeleton > 0)).T

    def _fit_gng(self, points):
        return gng.fit(points, self.settings)

    def _simplify_network(self, net, epsilon=1.0):
        # Find endpoints and intersections
        degree = np.sum(net.C, axis=0)
        endpoints = set(np.where(degree == 1)[0])
        intersections = set(np.where(degree > 2)[0])
        
        simplified_segments = []
        visited_edges = set()
        
        def traverse_segment(start, current):
            segment = [net.w[start]]
            while current not in endpoints and current not in intersections:
                segment.append(net.w[current])
                neighbors = set(np.where(net.C[current] == 1)[0]) - {start}
                if not neighbors:
                    break
                start, current = current, neighbors.pop()
            segment.append(net.w[current])
            return segment, current

        def process_node(node):
            neighbors = set(np.where(net.C[node] == 1)[0])
            for neighbor in neighbors:
                if (node, neighbor) not in visited_edges and (neighbor, node) not in visited_edges:
                    visited_edges.add((node, neighbor))
                    visited_edges.add((neighbor, node))
                    segment, end = traverse_segment(node, neighbor)
                    if len(segment) > 2:
                        simplified_segment = rdp(np.array(segment), epsilon)
                        simplified_segments.append(simplified_segment)
                    if end != neighbor:
                        process_node(end)

        # Process all endpoints and intersections
        for node in endpoints.union(intersections):
            process_node(node)
        
        return simplified_segments

    def _to_networkx(self, simplified_network):
        G = nx.Graph()
        for i, segment in enumerate(simplified_network):
            for j in range(len(segment) - 1):
                G.add_edge(tuple(segment[j]), tuple(segment[j+1]), segment_id=i)
        return G