# Experiment: Generalized Median Graph Concept Formation

**Date**: 2026-03-11 to 2026-03-18
**Baseline**: 73.0% accuracy (critical-point reduction, 7,796 images, 10 classes)
**Best result**: 55.75% accuracy (-17.25pp)
**Outcome**: Reverted to critical-point reduction (ADR-001)

---

## 1. Approach

### 1.1 Problem with Critical-Point Reduction

The existing concept formation (`CriticalPointConceptService`) is order-dependent — processing training images in a different sequence yields a different concept. It uses pairwise incremental reduction: `C₀ = G₁`, `C_{i+1} = MaxCommonMinor(Cᵢ, G_{i+1})`. Each step irreversibly discards information.

### 1.2 Generalized Median Graph (Boria et al., 2019)

The Generalized Median Graph finds the graph G that minimizes total GED to all training graphs simultaneously:

```
G = argmin Σ d(G, Gᵢ)
```

**Phase 1 — Set-Median**: Compute all-pairs GED (O(N²)), pick graph with minimum Sum of Distances. This fixes the node count.

**Phase 2 — Iterative Refinement**: Alternating descent until convergence:
- Vertex attributes: continuous → arithmetic mean, discrete → majority vote
- Edge structure: keep edge if present in ≥50% of training graphs (via node matchings)
- Recompute matchings via `nx.optimize_edit_paths` after each update

Uses **symmetric** GED costs (del=ins=0.25) unlike classification's asymmetric costs (ins=IMPOSSIBLE).

### 1.3 GMG-BCU Extension (Blumenthal et al., 2021)

Extends Boria with greedy node insertion/deletion to allow variable concept size. Per iteration: (1) update attributes, (2) update edges, (3) try deletion, (4) if no deletion try insertion, (5) recompute matchings. Each operation only proceeds if it strictly reduces total SOD.

---

## 2. Results

| Run | Description | Accuracy | Notes |
|-----|-------------|----------|-------|
| **Baseline** | Critical-point reduction | **73.0%** | 7,796 images, 10 classes |
| run_20260312 | First median graph, CMA-ES params | **55.75%** | 7,814 images, full test |
| run_20260318a | + node deletion (greedy multi) | **36.59%** | Edge cascade destroyed concept 8_1 |
| run_20260318b | + deletion fix (1/iter), 2.0s timeout | **44.19%** | |
| run_20260318c | + 2.0s match timeout, fast set-median | **51.60%** | Best tuned result |
| run_20260318d | + edge threshold 0.3 | **51.65%** | 50% sample |
| run_20260318e | + retrained broken concepts | **44.61%** | 50% sample, degraded |

### Per-Class Comparison (Baseline vs Best Median Graph at 55.75%)

| Class | Baseline Recall | Median Graph Recall | Delta |
|-------|----------------|---------------------|-------|
| 0 | 82.8% | 77.1% | -5.7 |
| 1 | 92.7% | 96.6% | +3.9 (but 30.6% precision — attractor) |
| 2 | 63.2% | 28.6% | -34.6 |
| 3 | 81.3% | 11.2% | -70.1 |
| 4 | 55.0% | 14.7% | -40.3 |
| 5 | 62.1% | 18.2% | -43.9 |
| 6 | 71.4% | 80.6% | +9.2 |
| 7 | 43.1% | 64.7% | +21.6 |
| 8 | 76.1% | 73.4% | -2.7 |
| 9 | 63.7% | 70.4% | +6.7 |

Improved: classes 6, 7, 9 (open/angular structures). Collapsed: classes 2, 3, 4, 5 (absorbed by low-complexity attractors).

### Concept Complexities (nodes+edges)

| Concept | Baseline | Median (first) | Median + node ops | Median (edge 0.3) |
|---------|----------|----------------|-------------------|--------------------|
| 0_1 | 13 | 24 | 24 | 24 |
| 1_1 | 13 | 13 | 13 | 13 |
| 1_3 | 5 | 5 | 5 | 5 |
| 2_1 | 13 | 17 | 17 | 17 |
| 2_2 | 24 | 32 | 32 | 33 |
| 3_1 | 13 | 29 | 29 | 29 |
| 4_1 | 16 | 24 | 19 | 24 |
| 4_2 | 17 | 17 | 17 | 17 |
| 6_1 | 20 | 28 | 26 | 28 |
| 7_1 | 9 | 9 | 9 | 9 |
| 8_1 | — | 31 | 16 | 27 |
| 9_2 | 16 | 20 | 21 | 20 |

---

## 3. Root Causes

### 3.1 Low-Complexity Attractor Problem

Concept 1_3 (complexity=3) won **2,173 false positives** (63.1% of all scored errors). With Boria normalization `1 - GED/(GED + max(n1,n2))`, low-complexity concepts get inflated similarity — the denominator is small. Concepts 1_3 + 7_1 combined: **2,848 FPs (82.7% of scored errors)**.

98.6% of misclassifications had GED margin < 5% between winner and runner-up.

### 3.2 Inconsistent GED Matchings on Cyclic Graphs

Digits with closed loops (0, 6, 8, 9) suffered from GED matching ambiguity. Node correspondences for cyclic graphs shift depending on traversal start position, causing edges present in ALL training graphs to get low support scores. This breaks edge voting — legitimate edges are removed, disconnecting concept structures.

### 3.3 Hyperparameter Mismatch

All runs used CMA-ES parameters tuned for critical-point-reduction concepts (78.42% accuracy on old concepts). The high normalizers (spatial: 3.1-3.75, angle: 279) nullify feature-based discrimination, making GED cost dominated by structural insertion/deletion. This disproportionately favors small concepts.

---

## 4. Tuning Attempts

### 4.1 Node Deletion (GMG-BCU)

Greedy multi-deletion used stale matchings — concept 8_1 lost 4 nodes + 11 edges in one iteration (15→11 nodes, 16→5 edges). Fixed to 1 deletion per iteration. Did not improve accuracy — doesn't solve the matching quality problem.

### 4.2 GED Timeout

`nx.optimize_graph_edit_distance` is an anytime generator, but each yield can take minutes for 12+ node graphs. Timeout only checks between yields. Anytime iteration on set-median (528 pairs × 2s) blocked for 17+ minutes. Resolution: first-yield for set-median ranking (fast) + 2.0s timeout for matching extraction (accurate).

### 4.3 Edge Support Threshold

Reduced from 0.5 (majority) to 0.3. Preserved more edges in closed structures but didn't improve classification accuracy (51.65% on 50% sample).

---

## 5. Literature Context

| Paper | Approach | Why relevant |
|-------|----------|-------------|
| Boria et al. (2019) | Iterative alternating minimization | Implemented — the core algorithm |
| Blumenthal et al. (2021) | GMG-BCU: variable node count | Implemented — node insertion/deletion extension |
| Ferrer et al. (2021) | LP-based median graph | More scalable, more complex |
| Mukherjee et al. (2009) | Edit grid + LP relaxation | O(N^4 K) prohibitive |
| Holder et al. (1994) | SUBDUE: MDL substructure discovery | Alternative: concept = most compressive subgraph |
| Han et al. (2011) | Probabilistic supergraph via EM | Alternative: nodes/edges with confidence scores |

Consensus: graph concept formation should optimize a global objective. GED is the standard distance. Approximation is necessary.

---

## 6. Ideas for Future Work

1. **Dedicated hyperparameter tuning** for median-graph concepts (current params tuned for old approach)
2. **Cycle-aware GED**: rotational normalization for closed-structure digits before matching
3. **Hybrid concept creation**: median graph for open structures (1-5, 7), critical-point reduction for closed structures (0, 6, 8, 9)
4. **Weighted set-median**: weight pairwise GED by graph size similarity
5. **Range-aware classification tuning**: calibrate cost of "within range" vs "outside range" for range-typed attributes
6. **Remove concept 1_3**: the 3-node attractor absorbs 63% of errors regardless of concept formation method

---

## References

1. Boria, N. et al. (2019). "Generalized Median Graph via Iterative Alternate Minimizations." arXiv:1906.11009
2. Blumenthal, D.B. et al. (2021). "Scalable generalized median graph estimation (GMG-BCU)." Information Systems 100. Code: github.com/dbblumenthal/gedlib
3. Ferrer, M. et al. (2021). "Scalable generalized median graph estimation." Information Systems 100
4. Mukherjee, L. et al. (2009). "Generalized Median Graphs." J. Combinatorial Optimization 17(1)
5. Holder, L.B. et al. (1994). "Substructure Discovery Using MDL." JAIR Vol. 2
6. Han, L. et al. (2011). "Information-Theoretic Generative Graph Prototypes." SIMBAD 2011, LNCS 7005
