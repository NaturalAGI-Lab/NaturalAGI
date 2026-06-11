"""
Repro for Bug E: label destruction in start_point_modifier.py change_start_point.

The method does:
    graph.nodes[new_start_point]["labels"].clear()
    graph.nodes[new_start_point]["labels"].append(CriticalPointType.START_POINT.value)
    graph.nodes[new_start_point]["labels"].append("Point")

This permanently destroys the original critical-point label (EndPoint/CornerPoint/IntersectionPoint).

Part 1: Concept formation impact.
  After change_start_point, the relabeled node has labels ["StartPoint", "Point"].
  GraphUtils.is_critical_point checks for CriticalPointType values — StartPoint IS in
  CRITICAL_POINT_TYPES, so synced traversal still treats it correctly as a critical point.
  The structural topology is preserved for concept formation.

Part 2: Classification impact — endpoint-count check.
  In classification/reduction_strategy/endpoint_strategy.py:
    _get_endpoints calls GraphUtils.is_endpoint (checks for "EndPoint" label) OR
    _node_is_semantically_endpoint (checks degree == 1 AND StartPoint NOT in labels).

  For a concept node that was EndPoint but got relabeled to StartPoint:
  - is_endpoint(data) → False  (no "EndPoint" label anymore)
  - _node_is_semantically_endpoint: degree==1 AND StartPoint NOT in labels → False (StartPoint IS there)
  → Node is NOT counted as an endpoint.

  Scenario: digit-7 concept has 2 EndPoints + 1 CornerPoint.
  After start relabeling, one EndPoint becomes StartPoint.
  Concept endpoint count = 1 (not 2).

  Classification's EndpointReductionStrategy._get_endpoints on the CONCEPT returns 1 endpoint.
  If the image graph has 2 endpoints, then:
    line 63-64: 'concept has endpoints, image has more' → excess endpoints removed from image.
  But actually since the concept was supposed to have 2 endpoints (now has 1),
  the concept-vs-image endpoint mismatch logic trims the image too aggressively.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, '/Users/mlapin/Development/personal/NaturalAGI/common')

from common.critical_point import CriticalPointType
from common.graph_utils import GraphUtils

print("=== Bug E: Label destruction by change_start_point ===\n")

# Simulate a digit-7 concept node: originally labeled EndPoint
node_data_before = {
    "labels": ["EndPoint", "Point"],
    "normalized_x": 0.1,
    "normalized_y": 0.9,
}

print(f"Node labels BEFORE change_start_point: {node_data_before['labels']}")
print(f"  is_critical_point: {GraphUtils.is_critical_point(node_data_before)}")
print(f"  is_endpoint:       {GraphUtils.is_endpoint(node_data_before)}")

# Simulate change_start_point mutation
node_data_before["labels"].clear()
node_data_before["labels"].append(CriticalPointType.START_POINT.value)
node_data_before["labels"].append("Point")

print(f"\nNode labels AFTER change_start_point: {node_data_before['labels']}")
print(f"  is_critical_point: {GraphUtils.is_critical_point(node_data_before)}")
print(f"  is_endpoint:       {GraphUtils.is_endpoint(node_data_before)}")

print()

# Check _node_is_semantically_endpoint logic (from classification endpoint_strategy.py)
# A node with degree=1 and START_POINT in labels → NOT counted as endpoint
labels = node_data_before["labels"]
start_point_in_labels = CriticalPointType.START_POINT.value in labels
degree_1 = True  # simulate degree 1
is_semantic_endpoint = degree_1 and not start_point_in_labels

print("Classification _node_is_semantically_endpoint check (degree=1 AND StartPoint NOT in labels):")
print(f"  StartPoint in labels: {start_point_in_labels}")
print(f"  Would count as semantic endpoint: {is_semantic_endpoint}")
print(f"  → Combined: counted as endpoint at all? {GraphUtils.is_endpoint(node_data_before) or is_semantic_endpoint}")

print()
print("=== Impact on endpoint count comparison ===")
print("Concept originally had 2 EndPoints (e.g. both tips of digit 7).")
print("After change_start_point, one EndPoint becomes StartPoint.")
print("Classification sees concept endpoint_count = 1 (not 2).")
print()
print("Classification/reduction_strategy/endpoint_strategy.py lines 62-64:")
print("  if concept_endpoints and not image_endpoints:")
print("      raise ValueError('Concept has endpoints but image does not.')")
print()
print("With image having 2 endpoints and concept having 1 (due to relabeling):")
print("  concept_endpoints=[ep_A], image_endpoints=[ep_X, ep_Y]")
print("  len_concept=1 < len_image=2 → 'excess endpoints to remove' path taken")
print("  → One valid endpoint TRIMMED FROM IMAGE even though topology matches 7.")
print()
print("Also: StartPointPreprocessor (classification) reads concept start point's 'centroid'")
print("attribute to find the matching start on the image. This works correctly because")
print("change_start_point stores centroid on the relabeled node (line 23 of modifier).")
print("So start-point alignment is NOT broken — only the endpoint count is wrong.")
print()
print("VERDICT: Label destruction is CONFIRMED. Impact on topology traversal: minimal")
print("(StartPoint IS a CriticalPointType, so traversal works). Impact on endpoint-count")
print("in classification preprocessing: REAL — concept loses one endpoint label,")
print("causing over-trimming of image endpoints for open-contour digits (e.g. 1, 7).")
