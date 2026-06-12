"""
Repro for Bug B: visited-set clobber in synced_traversal_generator.py lines 224-229.

The code at lines 224-229 does:

    sync_list[path_id].append(next_pair)
    if next_pair not in visited:
        visited[next_pair] = set()
    visited[next_pair].add(path_id)       # ← adds path_id to accumulated set

    visited[(next_c_critical_point, next_i_critical_point)] = {path_id}   # ← CLOBBERS!

Line 229 is IDENTICAL to lines 225-227 but replaces the accumulated set with a
single-element set. This means if two different paths have both visited next_pair,
the second one to process it will erase the first path's visit record.

Consequence: cycle detection via  `if next_pair in visited and path_id in visited[next_pair]`
(line 215) will MISS cycles for the path whose record was overwritten.  A path
that should terminate when it re-visits a node pair will instead keep traversing,
producing duplicate segments (the same subpath gets added to sync_list twice) or
an infinite BFS loop.

We trace this statically since instantiating SyncedTraversalGenerator requires
no external dependencies.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, '/Users/mlapin/Development/personal/NaturalAGI/common')

print("=== Bug B: Visited-set clobber analysis ===\n")

# Simulate the dict state manually to show the problem
visited = {}

# Path 0 visits pair (A, X)
pair_AX = ("A", "X")
path_0 = 0

if pair_AX not in visited:
    visited[pair_AX] = set()
visited[pair_AX].add(path_0)
print(f"After path 0 adds pair (A,X): visited[{pair_AX}] = {visited[pair_AX]}")

# Path 1 (a branch) also visits the same pair (A, X)
path_1 = 1
if pair_AX not in visited:
    visited[pair_AX] = set()
visited[pair_AX].add(path_1)
print(f"After path 1 adds pair (A,X): visited[{pair_AX}] = {visited[pair_AX]}")

# Baseline: line 229 then CLOBBERS the accumulated set with {path_id}
visited[pair_AX] = {path_1}
print(f"After clobber line runs:      visited[{pair_AX}] = {visited[pair_AX]}")
assert path_0 not in visited[pair_AX], "path 0's visit record was erased"
print(f"→ Path 0's visit record is GONE: cycle detection for path 0 at this "
      f"pair will fail (line 215 check `path_id in visited[next_pair]`).")

src_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "logic",
    "synced_traversal_generator.py",
)
with open(src_path) as f:
    source = f.read()
assert "visited[(next_c_critical_point, next_i_critical_point)] = {path_id}" in source, \
    "expected the clobber line to be present in baseline code"
print("Source check: clobber line PRESENT in synced_traversal_generator.py")
print("→ CONFIRMED (baseline behavior): cycle-detection records get overwritten.")
