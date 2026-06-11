"""
Repro for Bug D: dead retry loop params.

Two sub-bugs:
  D1. np.arange(0.4, 0.8) == [0.4] (single value, step defaults to 1.0)
      The outer for-loop in _determine_start_point runs exactly ONCE,
      providing no retry escalation across min_samples_coefficient values.

  D2. clustering_algorithm='optics' — StartPointPicker._cluster_points OPTICS branch
      (lines 151-154 of start_point_picker.py) calls:
          OPTICS(min_samples=max(min_samples, 2))
      The eps parameter is COMPLETELY IGNORED by the OPTICS branch.
      So the eps escalation (start_clustering_eps += eps_step) has zero effect on OPTICS.
      Only start_clustering_min_samples increments, but that is capped by max(min_samples, 2)
      which means if start_clustering_min_samples is already >= 2 the escalation has no effect
      unless the value actually grows.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, '/Users/mlapin/Development/personal/NaturalAGI/common')

import numpy as np
from src.logic.start_point_picker import StartPointPicker

print("=== Bug D1: np.arange(0.4, 0.8) produces a single-element array ===\n")
arr = np.arange(0.4, 0.8)
print(f"np.arange(0.4, 0.8) = {arr}")
print(f"length = {len(arr)}  (expected multiple values for retry escalation)")
print(f"Loop iterates over: {list(arr)}")
print(f"→ Only ONE iteration: min_samples_coefficient=0.4 → NO retry with 0.5, 0.6, 0.7\n")

print("=== Bug D2: OPTICS branch ignores eps ===\n")
# Read the OPTICS branch directly:
import inspect
source = inspect.getsource(StartPointPicker._cluster_points)
# Find the OPTICS section
lines = source.split('\n')
optics_lines = [l for l in lines if 'optics' in l.lower() or 'OPTICS' in l]
print("OPTICS branch code:")
for l in optics_lines:
    print(f"  {l}")
print()
print("The OPTICS clusterer is constructed with only min_samples=max(min_samples, 2).")
print("'eps' parameter from the method signature is NOT passed → eps escalation is a no-op for OPTICS.")
print()
print("Additionally, _cluster_points is called with n_clusters=8 (default) but OPTICS ignores n_clusters too.")
print()
print("Net effect: the inner retry loop (MAX_ITERATIONS=15) increments eps and min_samples,")
print("but since OPTICS ignores eps and clamps min_samples to max(value, 2),")
print("all 15 iterations produce IDENTICAL clustering results until min_samples grows beyond 2.")
print()
print("=== Combined effect ===")
print("The outer loop runs once (D1), the inner loop's eps escalation has no effect (D2).")
print("The only live parameter is start_clustering_min_samples, which starts at")
print(f"  int(N * 0.4) where N = number of image graphs")
print("and increments by 1 per inner iteration.")
print("With e.g. N=10: starts at 4, grows to 4,5,6,...,18 over 15 iterations.")
print("This is real escalation, but ONLY for min_samples — eps plays no role.")
