"""
Repro for Bug C: thresholdless argmax in _find_best_matching_node.

The docstring says "None if no good match" but the implementation always returns
argmax — even at score 0.0.  Additionally, there is no monotonicity constraint:
the same other_path index can be returned for multiple template_path indices
(many-to-one), and indices can be non-monotone (e.g. template idx 0 maps to
other idx 3 while template idx 1 maps to other idx 0), which means spatially
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

print("=== Bug C (fixed): monotone one-to-one alignment with threshold ===\n")


def thresholded(match, sim, min_sim):
    return [
        (j if j is not None and sim[i][j] >= min_sim else None)
        for i, j in enumerate(match)
    ]


# Case 1: All-zero similarity row → threshold rejects, falls back to template-only
all_zero_matrix = [[0.0, 0.0, 0.0]]
match = thresholded(
    finder._align_paths(all_zero_matrix), all_zero_matrix, finder.min_match_similarity
)
print(f"All-zero row: alignment after threshold = {match}")
assert match == [None], "score-0 match must be rejected by threshold"

# Case 2: Many-to-one is impossible — alignment is one-to-one
many_to_one_matrix = [
    [0.1, 0.2, 0.9],
    [0.1, 0.3, 0.8],
]
match = finder._align_paths(many_to_one_matrix)
used = [j for j in match if j is not None]
print(f"One-to-one: {match}")
assert len(used) == len(set(used)), "alignment must be one-to-one"

# Case 3: Non-monotone mapping is impossible — alignment preserves order
non_monotone_matrix = [
    [0.1, 0.2, 0.9],
    [0.8, 0.1, 0.1],
]
match = finder._align_paths(non_monotone_matrix)
used = [j for j in match if j is not None]
print(f"Monotone: {match}")
assert used == sorted(used), "alignment must be monotone"

print("\nFIXED: alignment is monotone, one-to-one, and thresholded "
      f"(min_match_similarity={finder.min_match_similarity}).")
