"""
Full in-process repro for Bug A through SyncedGraphMinorFinder.find_max_common_minor.

The graph has two critical-point segments:

  segment 1: StartPoint -> CornerPoint
  segment 2: CornerPoint -> EndPoint

Segment 1 uses the concept path as template and adds concept middle node id=1.
Segment 2 uses the image path as template; its middle node is also id=1, but it
represents a different path/location. _create_reduced_path_in_result then logs:

  Node 1 already exists in result graph. Properties not updated.
"""

import logging
import os
import sys

import networkx as nx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, "/Users/mlapin/Development/personal/NaturalAGI/common")

from src.critical_point_preprocessor import CriticalPointPreprocessor  # noqa: E402
from src.node_similarity_calculator import NodeSimilarityCalculator  # noqa: E402
from src.property_handlers import PropertyProcessor  # noqa: E402
from src.synced_graph_algorithm import SyncedGraphMinorFinder  # noqa: E402


def make_node(labels, x, y, marker):
    return {
        "labels": labels,
        "normalized_x": x,
        "normalized_y": y,
        "marker": marker,
    }


G_c = nx.Graph()
G_c.add_node(0, **make_node(["StartPoint", "Point"], 0.0, 0.0, "c-start"))
G_c.add_node(1, **make_node(["Point"], 0.1, 0.1, "concept-first-segment-node-id-1"))
G_c.add_node(2, **make_node(["CornerPoint", "Point"], 0.5, 0.5, "c-corner"))
G_c.add_node(10, **make_node(["Point"], 0.6, 0.6, "concept-second-a"))
G_c.add_node(11, **make_node(["Point"], 0.7, 0.7, "concept-second-b"))
G_c.add_node(3, **make_node(["EndPoint", "Point"], 1.0, 1.0, "c-end"))
G_c.add_edges_from([(0, 1), (1, 2), (2, 10), (10, 11), (11, 3)])

G_i = nx.Graph()
G_i.add_node(0, **make_node(["StartPoint", "Point"], 0.0, 0.0, "i-start"))
G_i.add_node(5, **make_node(["Point"], 0.2, 0.2, "image-first-segment-node-id-5"))
G_i.add_node(2, **make_node(["CornerPoint", "Point"], 0.5, 0.5, "i-corner"))
G_i.add_node(1, **make_node(["Point"], 0.9, 0.1, "image-second-segment-node-id-1"))
G_i.add_node(3, **make_node(["EndPoint", "Point"], 1.0, 1.0, "i-end"))
G_i.add_edges_from([(0, 5), (5, 2), (2, 1), (1, 3)])

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("bug_a_full_mcm")
logger.setLevel(logging.WARNING)

finder = SyncedGraphMinorFinder(
    prop_manager=PropertyProcessor(),
    similarity_calculator=NodeSimilarityCalculator(),
    critical_point_preprocessor=CriticalPointPreprocessor(),
    logger=logger,
)

result = finder.find_max_common_minor(G_c, G_i)

print("=== Bug A full MCM repro (fixed: namespaced interior IDs) ===")
print("Result graph nodes:")
for node_id, data in result.nodes(data=True):
    print(f"  {node_id}: {data}")
edges = sorted(tuple(sorted(map(str, edge))) for edge in result.edges())
print(f"Result graph edges: {edges}")

# Two segments with one interior node each → 4 critical + 2 interior nodes, 4 edges.
interior = [n for n in result.nodes if isinstance(n, str) and n.startswith("seg")]
assert len(interior) == 2, f"expected 2 namespaced interior nodes, got {interior}"
assert result.number_of_edges() == 4, (
    f"expected 4 edges (no collapse), got {result.number_of_edges()}"
)
print("→ FIXED: interior node IDs no longer collide; edges are not collapsed.")
