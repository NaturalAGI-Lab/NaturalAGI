"""
Repro for Bug C (CC-03): thresholdless argmax in _find_best_matching_node.

The docstring says "None if no good match" but the implementation always returns
argmax — even at score 0.0.  Additionally, there is no monotonicity constraint:
the same other_path index can be returned for multiple template_path indices
(many-to-one), and indices can be non-monotone (e.g. template idx 0 maps to
other idx 2 while template idx 1 maps to other idx 0), which means spatially
distant nodes get merged.

We show:
  1. Score-0 case → argmax still returned (not None)
  2. Many-to-one: multiple template nodes mapped to same other node
  3. Non-monotone: earlier template node maps to later other node
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, '/Users/mlapin/Development/personal/NaturalAGI/common')

import logging
logging.basicConfig(level=logging.WARNING)

from src.synced_graph_algorithm import SyncedGraphMinorFinder
from src.property_handlers.property_handlers import PropertyProcessor
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.critical_point_preprocessor import CriticalPointPreprocessor

finder = SyncedGraphMinorFinder(
    prop_manager=PropertyProcessor(),
    similarity_calculator=NodeSimilarityCalculator(),
    critical_point_preprocessor=CriticalPointPreprocessor(),
    logger=logging.getLogger("probe_c"),
)


def align(matrix):
    return [finder._find_best_matching_node(matrix, i) for i in range(len(matrix))]


print("=== Bug C (baseline): thresholdless per-row argmax ===\n")

# Case 1: All-zero similarity row → argmax still returns idx 0, never None
all_zero_matrix = [[0.0, 0.0, 0.0]]
match = align(all_zero_matrix)
print(f"All-zero row: match = {match}")
assert match == [0], "BUG: score-0 row still matched to idx 0 (expected on baseline)"

# Case 2: Many-to-one — both template rows map to the same other node
many_to_one_matrix = [
    [0.1, 0.2, 0.9],
    [0.1, 0.3, 0.8],
]
match = align(many_to_one_matrix)
used = [j for j in match if j is not None]
print(f"Many-to-one: match = {match}")
assert len(used) != len(set(used)), "BUG: many-to-one mapping (expected on baseline)"

# Case 3: Non-monotone — template idx 0 → other idx 2, template idx 1 → other idx 0
non_monotone_matrix = [
    [0.1, 0.2, 0.9],
    [0.8, 0.1, 0.1],
]
match = align(non_monotone_matrix)
used = [j for j in match if j is not None]
print(f"Non-monotone: match = {match}")
assert used != sorted(used), "BUG: non-monotone mapping (expected on baseline)"

print("\nCONFIRMED (baseline behavior): matching is thresholdless argmax — "
      "score-0 rows still match, many-to-one and non-monotone mappings allowed.")
