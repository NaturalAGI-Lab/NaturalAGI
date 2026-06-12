"""
Repro for Bug A: cross-graph node-ID collision in _create_reduced_path_in_result.

Shows that when graph2 (image) is shorter than graph1 (concept),
the template becomes graph2 and template_node_id values come from
image-graph IDs (0,1,2,...).  If the concept graph also has those
same integer IDs (it always does — both graphs use sequential Neo4j
integer IDs starting at 0), then:

  result_node_id = template_node_id   (line 378 hard-overrides)

... so the result graph ends up with ID 1 in it.  If a later
subpath also tries to add ID 1 (because the concept path
through a different segment also contains node 1), the code
hits the "Node X already exists in result graph. Properties not updated."
warning and silently keeps stale properties.

We demonstrate this directly without Neo4j by building two tiny
bipartite Point-Vector graphs with overlapping integer IDs but
different spatial coordinates.
"""
import sys
import os
import logging

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add common library
sys.path.insert(0, '/Users/mlapin/Development/personal/NaturalAGI/common')

import networkx as nx

logging.basicConfig(level=logging.WARNING)  # suppress verbose output for this probe

# ------------------------------------------------------------------ helpers --

def make_node(label, x, y, extra=None):
    d = {"labels": [label, "Point"], "normalized_x": x, "normalized_y": y}
    if extra:
        d.update(extra)
    return d

# ---------------------------------------------------------------
# Build concept graph:  StartPoint(0) - Point(1) - EndPoint(2)
# ---------------------------------------------------------------
G_c = nx.Graph()
G_c.add_node(0, **make_node("StartPoint", 0.1, 0.1))
G_c.add_node(1, **make_node("Point",      0.5, 0.5, {"source": "concept"}))
G_c.add_node(2, **make_node("EndPoint",   0.9, 0.9))
G_c.add_edge(0, 1)
G_c.add_edge(1, 2)

# ---------------------------------------------------------------
# Build image graph: same integer IDs but node 1 is at a DIFFERENT location
# (simulating a different image where the middle node is spatially displaced)
# ---------------------------------------------------------------
G_i = nx.Graph()
G_i.add_node(0, **make_node("StartPoint", 0.1, 0.1))
G_i.add_node(1, **make_node("Point",      0.3, 0.7, {"source": "image"}))  # different coords!
G_i.add_node(2, **make_node("EndPoint",   0.9, 0.9))
G_i.add_edge(0, 1)
G_i.add_edge(1, 2)

# ---------------------------------------------------------------
# Directly call _create_reduced_path_in_result to show the collision
# ---------------------------------------------------------------
from src.property_handlers.property_handlers import PropertyProcessor
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.critical_point_preprocessor import CriticalPointPreprocessor
from src.synced_graph_algorithm import SyncedGraphMinorFinder

prop_manager = PropertyProcessor()
similarity_calculator = NodeSimilarityCalculator()
preprocessor = CriticalPointPreprocessor()

finder = SyncedGraphMinorFinder(
    prop_manager=prop_manager,
    similarity_calculator=similarity_calculator,
    critical_point_preprocessor=preprocessor,
    logger=logging.getLogger("probe"),
)

# Manually call _create_reduced_path_in_result with overlapping sub-paths
# Concept sub-path: [0, 1, 2],  Image sub-path: [0, 1, 2]
result_graph = nx.Graph()

# ---- First call: add node 0 and 2 as start/end, 1 as middle via graph1 path ----
print("=== Bug A: Node ID collision demo ===")
print(f"Concept node 1 coords: x={G_c.nodes[1]['normalized_x']}, y={G_c.nodes[1]['normalized_y']}, source={G_c.nodes[1].get('source')}")
print(f"Image   node 1 coords: x={G_i.nodes[1]['normalized_x']}, y={G_i.nodes[1]['normalized_y']}, source={G_i.nodes[1].get('source')}")

# Sub-paths exclude start/end so sub_path1=[1], sub_path2=[1]
# Both have length 1, so len(sub_path1) <= len(sub_path2) → template=graph1(concept)
# result_node_id = template_node_id = 1 (from concept)
# That merges concept node 1 with image node 1.

finder._create_reduced_path_in_result(
    result_graph=result_graph,
    graph1=G_c,
    graph2=G_i,
    start1=0, end1=2,
    path1=[0, 1, 2],
    start2=0, end2=2,
    path2=[0, 1, 2],
)

print(f"\nResult graph nodes and properties:")
for nid in result_graph.nodes:
    print(f"  node {nid}: {result_graph.nodes[nid]}")

# ---- NOW simulate a SECOND subpath that also contains node 1 (e.g., from a cycle) ----
# This would happen in a figure-8 or a graph where node 1 appears in two segments.
# We simulate it by calling _create_reduced_path_in_result again with the same start=0, end=2.
# Result: node 1 is ALREADY in result_graph → properties NOT updated → silent property loss.

print("\n=== Simulating second subpath that revisits node 1 ===")
# New image node 1-prime has very different coords
G_i2 = nx.Graph()
G_i2.add_node(0, **make_node("StartPoint", 0.1, 0.1))
G_i2.add_node(1, **make_node("Point", 0.8, 0.2, {"source": "image2"}))
G_i2.add_node(2, **make_node("EndPoint", 0.9, 0.9))
G_i2.add_edge(0, 1)
G_i2.add_edge(1, 2)

import io
log_capture = io.StringIO()
handler = logging.StreamHandler(log_capture)
handler.setLevel(logging.WARNING)
logging.getLogger("probe").addHandler(handler)

finder._create_reduced_path_in_result(
    result_graph=result_graph,
    graph1=G_c,
    graph2=G_i2,
    start1=0, end1=2,
    path1=[0, 1, 2],
    start2=0, end2=2,
    path2=[0, 1, 2],
)

captured = log_capture.getvalue()
print(f"Captured log output:\n{captured if captured else '(no warnings - unexpected)'}")

print(f"\nResult graph node 1 AFTER second call (should still have first image's source):")
print(f"  node 1: {result_graph.nodes[1]}")
print()
print("VERDICT: If 'source' is still 'concept' (merged with image), node 1 was not updated on second call.")
print("The 'Properties not updated' warning would fire in real execution (log level DEBUG/WARNING).")
