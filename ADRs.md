# Architecture Decision Records

New entries appended using the format in [ADR.template.md](ADR.template.md).

---

## ADR-001: Median Graph concept formation — experiment and revert

**Date**: 2026-03-11 to 2026-03-18 | **Status**: Reverted

**Context**: The pairwise concept formation (`CriticalPointConceptService`) was order-dependent and lossy. The Generalized Median Graph (Boria et al. 2019) was implemented as a replacement — it considers all training graphs simultaneously, minimizing total GED. Extended with GMG-BCU node deletion/insertion (Blumenthal et al. 2021). Tested across 6 classification runs.

**Result**: Best accuracy **55.75%** vs **73.0% baseline** (-17.25pp). Root causes: (1) low-complexity concepts act as GED attractors, (2) GED matchings on cyclic graphs are inconsistent — breaking edge voting for closed-structure digits

**Decision**: Revert to critical-point reduction. Full report: `experiments/median-graph-concept-formation/`.
