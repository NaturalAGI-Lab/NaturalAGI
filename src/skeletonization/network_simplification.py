from typing import List, Tuple, Set
from ypstruct import structure
import numpy as np
from rdp import rdp


class NetworkSimplification:

    @staticmethod
    def simplify_network(network: structure, epsilon: float = 0.5) -> List[np.ndarray]:
        # Find endpoints and intersections
        degree = np.sum(network.C, axis=0)
        endpoints = set(np.where(degree == 1)[0])
        intersections = set(np.where(degree > 2)[0])

        simplified_segments = []
        visited_edges = set()

        def traverse_segment(start: int, current: int) -> Tuple[List[np.ndarray], int]:
            segment = [network.w[start]]
            initial_start = start
            visited = {start}

            while True:
                segment.append(network.w[current])

                # Stop if we hit an endpoint or intersection
                if current in endpoints or current in intersections:
                    if (
                        current != start
                    ):  # Don't stop if we just started from this point
                        return segment, current

                # Find unvisited neighbors
                neighbors = set(np.where(network.C[current] == 1)[0]) - {start}
                unvisited = neighbors - visited

                # If no unvisited neighbors, check if we can close a loop
                if not unvisited:
                    if initial_start in neighbors and len(segment) > 2:
                        segment.append(network.w[initial_start])  # Close the loop
                        return segment, initial_start
                    return segment, current

                # Move to next node
                start, current = current, next(iter(unvisited))
                visited.add(current)

        def process_node(node: int) -> None:
            neighbors = set(np.where(network.C[node] == 1)[0])
            for neighbor in neighbors:
                edge = tuple(sorted([node, neighbor]))
                if edge not in visited_edges:
                    visited_edges.add(edge)
                    segment, end = traverse_segment(node, neighbor)

                    if len(segment) > 2:
                        # Apply RDP simplification while preserving endpoints
                        simplified_segment = rdp(np.array(segment), epsilon)

                        # Ensure first and last points are preserved exactly
                        if not np.array_equal(simplified_segment[0], segment[0]):
                            simplified_segment = np.vstack(
                                [segment[0], simplified_segment[1:]]
                            )
                        if not np.array_equal(simplified_segment[-1], segment[-1]):
                            simplified_segment = np.vstack(
                                [simplified_segment[:-1], segment[-1]]
                            )

                        simplified_segments.append(simplified_segment)
                    else:
                        # Always keep segments of length 2 to maintain connectivity
                        simplified_segments.append(np.array(segment))

                    # Continue processing from the end point if it's not the neighbor
                    # and it's not an endpoint we already processed
                    if end != neighbor and end not in processed_nodes:
                        if end in endpoints or end in intersections:
                            processed_nodes.add(end)
                        process_node(end)

        # Track nodes we've processed to avoid duplicate processing
        processed_nodes: Set[int] = set()

        # Start with endpoints and intersections if they exist
        start_nodes = endpoints.union(intersections)

        # If no endpoints or intersections (e.g., perfect circle),
        # start with any node
        if not start_nodes:
            start_nodes = {0}  # Start with first node

        for node in start_nodes:
            if node not in processed_nodes:
                processed_nodes.add(node)
                process_node(node)

        # Post-processing to connect any disconnected segments
        return simplified_segments
