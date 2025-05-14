# Plan: Unifying Classification Algorithm with Concept Creator Logic (Revised)

## 1. Goal

To update the classification algorithm in the `@classification` module to use the same core graph matching and reduction techniques as the `@concept_creator` module, with the following key distinctions for classification:
    1. The **concept graph** (used as the reference for classification) is **not modified or reduced**.
    2. The **image graph** *is* reduced using the same logic as in concept creation.
    3. A pre-check is introduced: if the concept graph is inherently more complex than the image graph (even before image reduction), the concept is skipped as a potential match.
    4. The process must yield a **similarity score** indicating how well the image graph (after reduction) matches the concept graph.

## 2. Background & Current State Analysis

*   **`@concept_creator` Module (Key files identified):**
    *   **Graph Reduction:** Likely within `src/concept_creator/src/reduction_strategy/` (needs further listing).
    *   **Critical Graph Alignment & Matching Strategy:** Potentially in `src/concept_creator/src/synced_graph_algorithm.py` and orchestrated by files in `src/concept_creator/src/logic/`.
    *   **Node Similarity:** `src/concept_creator/src/node_similarity_calculator.py` (needs comparison with the `classification` version).
    *   **Graph Preprocessing:** `src/concept_creator/src/critical_point_preprocessor.py` (needs comparison).
    *   **Utilities:** Potentially in `src/concept_creator/src/utils/` for complexity or other graph operations.
*   **`@classification` Module (Current):**
    *   Primary classification logic in `src/classification/concept_minor_classifier.py`.
    *   Comparison/similarity in `src/classification/graph_comparator.py` and `src/classification/node_similarity_calculator.py`.
    *   Preprocessing in `src/classification/critical_point_preprocessor.py`.

## 3. Proposed Unified Classification Workflow

The following steps will be implemented within the `@classification` module, leveraging and adapting logic primarily from `@concept_creator`:

### Step 1: Load Graphs
*   **Input:** Image graph (`G_image`), Concept graph (`G_concept`). These are assumed to be "critical graphs" as per your requirement.

### Step 2: Complexity Pre-Check
*   **Action:** Calculate a complexity metric for `G_image` and `G_concept`.
    *   The definition of "complexity" needs to be established (e.g., number of nodes + number of edges, or a more sophisticated structural measure relevant to your graphs).
    *   A function like `calculate_graph_complexity(graph) -> int_or_float` will be needed. This could be a new utility or an existing one.
*   **Condition:** If `complexity(G_concept) > complexity(G_image)`, then `G_concept` cannot be matched by reducing `G_image`.
*   **Outcome:** Skip `G_concept` for further matching; return a very low/zero similarity score or an indication of no match.

### Step 3: Reduce Image Graph
*   **Action:** Apply the graph reduction algorithm (to be sourced from `@concept_creator`) to `G_image`.
    *   Let the result be `G_image_reduced`.
    *   **Crucially, `G_concept` is NOT reduced or modified in any way.**
*   **Consideration:** The reduction logic from `@concept_creator` must be applicable such that it only transforms `G_image`.

### Step 4: Align Critical Graphs
*   **Action:** Align the `G_image_reduced` with `G_concept`.
    *   This step will use the critical graph alignment logic, presumably from `@concept_creator`.
    *   The goal is to establish the best possible correspondence between the nodes and edges of `G_image_reduced` and `G_concept`.

### Step 5: Isomorphism Check (Post-Reduction of Image)
*   **Action:** Determine if `G_image_reduced` can be isomorphic to `G_concept`.
    *   This checks if the structure of the reduced image graph is compatible with the concept graph's structure.
*   **Outcome:** If they cannot be isomorphic, this suggests a fundamental structural mismatch. Return a low/zero similarity score or indicate no match. This step helps to quickly discard incompatible concepts.

### Step 6: Detailed Matching & Similarity Score Calculation
*   **Action:** Based on the alignment (Step 4) and assuming a positive isomorphism check (Step 5), perform a detailed comparison using the "matching strategy" adapted from `@concept_creator`.
    *   This strategy needs to be enhanced or wrapped to quantify the match and produce a similarity score.
    *   Factors contributing to the score could include:
        *   Proportion of `G_concept` nodes/edges successfully matched in `G_image_reduced`.
        *   Similarity of attributes for matched nodes/edges (if applicable).
        *   Penalties for unmatched essential parts of `G_concept`.
        *   Penalties for unmatched parts in `G_image_reduced` if they contradict the concept.
*   **Output:** A numerical similarity score (e.g., normalized between 0.0 and 1.0).

## 4. Key Modules/Functions to Develop or Adapt (Refined)

*   **`classification.concept_classifier` (Likely refactoring `concept_minor_classifier.py`):**
    *   Orchestrates the new workflow.
*   **`common.graph_utils.complexity` (Potentially New or from `@concept_creator/src/utils/`):**
    *   `calculate_graph_complexity(graph) -> float`
*   **`common.graph_utils.reduction` (Adapting from `@concept_creator/src/reduction_strategy/`):**
    *   `reduce_image_graph_for_concept_matching(image_graph) -> Graph`
*   **`common.graph_utils.alignment_and_matching` (Adapting from `@concept_creator/src/synced_graph_algorithm.py` and potentially `logic/`):**
    *   `align_and_match_graphs(reduced_image_graph, concept_graph) -> Tuple[AlignmentMapping, IsomorphismStatus, RawMatchDetails]`
*   **`common.graph_utils.isomorphism` (Potentially part of `alignment_and_matching` or separate if logic exists):**
    *   `check_structural_isomorphism(graph1, graph2) -> bool` (May be integrated into the main matching algorithm).
*   **`classification.similarity_calculator` (Potentially new, or evolving `graph_comparator.py`, using output from `align_and_match_graphs`):**
    *   `calculate_match_similarity(raw_match_details, reduced_image_graph_complexity, concept_graph_complexity) -> float`
*   **`common.graph_utils.node_similarity` (Consolidating/choosing between the two existing `node_similarity_calculator.py` files):**
    *   A unified `calculate_node_similarity(node1, node2, context) -> float`
*   **`common.graph_utils.preprocessing` (Consolidating/choosing between the two `critical_point_preprocessor.py` files):**
    *   A unified `preprocess_graph_for_matching(graph) -> CriticalGraph`

## 5. Refactoring Strategy

*   **Prioritize Understanding `@concept_creator`:** Deep dive into `reduction_strategy/`, `synced_graph_algorithm.py`, and `logic/`.
*   **Compare Duplicates:** Carefully compare the `node_similarity_calculator.py` and `critical_point_preprocessor.py` files from both modules to decide on a single source of truth or a merged version.
*   **Identify and Relocate Core Algorithms:** Move the fundamental graph reduction, alignment, and matching algorithms from `@concept_creator` to a shared location (e.g., `NaturalAGI/common/graph_algorithms/` or extend `common/graph_utils/`).
*   **Adapt for Classification:** Ensure shared algorithms can be invoked such that:
    *   Only the image graph is reduced.
    *   The concept graph remains unchanged.
    *   A similarity score is produced as the final output for classification.

## 6. Open Questions & Considerations

*   **Defining "Graph Complexity":** Check `src/concept_creator/src/utils/` or algorithms for existing metrics.
*   **"Matching Strategy" in `synced_graph_algorithm.py`:** How is it defined? How easily can it be adapted to output a score?
*   **Nature of "Critical Graphs":** How are they defined/created by the `critical_point_preprocessor.py` files?

## 7. Next Steps (If this plan is approved)

1.  **Explore Key `@concept_creator` Components:**
    *   I will list the contents of `src/concept_creator/src/reduction_strategy/`.
    *   Then, I will read the contents of (or key functions from):
        *   Files within `src/concept_creator/src/reduction_strategy/`.
        *   `src/concept_creator/src/synced_graph_algorithm.py`.
        *   `src/concept_creator/src/node_similarity_calculator.py` (and its counterpart in `classification`).
        *   `src/concept_creator/src/critical_point_preprocessor.py` (and its counterpart in `classification`).
        *   Potentially files in `src/concept_creator/src/logic/` and `src/concept_creator/src/utils/` based on relevance.
2.  **Detailed Code Review of `classification` module:**
    *   `src/classification/concept_minor_classifier.py`.
    *   `src/classification/graph_comparator.py`.
3.  **Finalize Definitions & Refactoring Plan:** Based on the detailed code review.
4.  **Implementation.**
5.  **Testing.**