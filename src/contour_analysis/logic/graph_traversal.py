from typing import Generator, Any
import networkx as nx


class GraphTraversal:
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    def dfs_traversal(self, start_node: Any) -> Generator[Any, None, None]:
        """
        Generator for DFS traversal.
        
        Args:
            start_node (Any): The starting node for DFS.
        
        Yields:
            Any: The next node in DFS order.
        """
        visited = set()

        def _dfs(node: Any):
            visited.add(node)
            yield node
            for neighbor in sorted(self.graph.neighbors(node)):
                if neighbor not in visited:
                    yield from _dfs(neighbor)

        yield from _dfs(start_node)
