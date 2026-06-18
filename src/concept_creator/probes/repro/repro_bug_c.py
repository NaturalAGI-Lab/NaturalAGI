"""
Bug C (FIXED): monotone 1:1 intra-segment alignment.

Previously, _find_best_matching_node did thresholdless per-row argmax, which
allowed many-to-one mappings and non-monotone sequences. This script verifies
the fixed behavior: align_monotone_one_to_one ensures every alignment pair is
distinct (1:1), indices are monotone in both axes (no crossing pairs), and
score-0 shorter-side nodes still match exactly once (cardinality fixed at min).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, '/Users/mlapin/Development/personal/NaturalAGI/common')

import logging
logging.basicConfig(level=logging.WARNING)

from src.logic.sequence_aligner import align_monotone_one_to_one

V = ["Vector"]

print("=== Bug C (fixed): monotone 1:1 intra-segment alignment ===\n")

# Case 1: All-zero similarity row → still matched (cardinality fixed at min=1),
# but now exactly one monotone 1:1 pair, never a many-to-one collapse.
all_zero = [[0.0, 0.0, 0.0]]
pairs = align_monotone_one_to_one(all_zero, [V], [V, V, V])
print(f"All-zero row: pairs = {pairs}")
assert pairs == [(0, 0)], "fixed: single monotone match even at score 0"

# Case 2: Former many-to-one matrix → now 1:1 (distinct columns).
many = [[0.1, 0.2, 0.9],
        [0.1, 0.3, 0.8]]
pairs = align_monotone_one_to_one(many, [V, V], [V, V, V])
cols = [j for _, j in pairs]
print(f"Was many-to-one: pairs = {pairs}")
assert len(cols) == len(set(cols)), "fixed: no column reused"

# Case 3: Former non-monotone matrix → now monotone (strictly increasing).
non_monotone = [[0.1, 0.2, 0.9],
                [0.8, 0.1, 0.1]]
pairs = align_monotone_one_to_one(non_monotone, [V, V], [V, V, V])
rows = [i for i, _ in pairs]
cols = [j for _, j in pairs]
print(f"Was non-monotone: pairs = {pairs}")
assert rows == sorted(rows) and cols == sorted(cols), "fixed: monotone in both axes"

print("\nCONFIRMED (fixed behavior): intra-segment matching is monotone and 1:1; "
      "score-0 shorter-side nodes are matched exactly once, no crossings, no collapse.")
