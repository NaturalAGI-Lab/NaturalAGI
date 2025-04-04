Okay, let's break this down.

First, I'll analyze the current implementation of the `concept_creator`, focusing on `graph_minor_finder.py`. Then, I'll need to examine the `classification` logic to understand how it currently works. Finally, I'll propose a plan to make the classification process more similar to the concept creation process.

**Analysis of `src/concept_creator/graph_minor_finder.py`:**

Based on the code you provided:

1.  **Goal:** The primary goal of `GraphMinorFinder` is to find the "maximum common minor" between an existing `concept_graph` and a new `image_graph`. This essentially means finding the largest shared structure and merging properties.
2.  **Preprocessing:** It heavily relies on `CriticalPointPreprocessor` to normalize and align critical points (Start, End, Intersection, Corner) between the two graphs *before* comparison. This seems to be a key step for robust matching.
3.  **Critical Points:** It identifies these preprocessed critical points in both graphs.
4.  **Matching:**
    *   It finds a designated `StartPoint` in both graphs to anchor the comparison.
    *   It matches critical points between the two graphs based on type and similarity (`_match_critical_points`), creating a `critical_point_mapping`. This leverages the `NodeSimilarityCalculator`. The preprocessing step ensures critical point counts match, simplifying this mapping.
5.  **Path Finding & Matching:**
    *   It explores paths *between* matched critical points in both graphs (`_find_paths_to_next_critical`).
    *   It finds the optimal pairs of paths connecting corresponding critical points using the mapping and path similarity (`_find_optimal_path_matches_with_mapping`). Path similarity considers length and node type compatibility.
6.  **Reduction & Merging:**
    *   For each matched path pair, it creates a *reduced* path in the `result_graph` (`_create_reduced_path_in_result`).
    *   It uses the *shorter* of the two paths as a template.
    *   Nodes from the template path are added to the result. Properties are merged from the corresponding nodes in both original paths (using `NodeSimilarityCalculator` to find the best match between nodes along the paths and `PropertyHandlerManager` to merge).
7.  **Output:** The final `result_graph` represents the merged concept, incorporating the common structure from the new image graph.

**Next Step: Analyze Classification Logic**

To understand how to modify the `classification` function, I need to see its current implementation. I'll read the main classification logic file.

Read file: src/classification/concept_minor_classifier.py
Okay, I understand the goal. You want to align the classification logic in `ConceptMinorClassifier` more closely with the methodology used in `GraphMinorFinder` for concept creation.

Here's the analysis and the proposed plan:

**Analysis Summary:**

1.  **`GraphMinorFinder` (Concept Creation):**
    *   **Goal:** Find the maximum common structure between two graphs and merge them.
    *   **Key Steps:** Preprocesses graphs using `CriticalPointPreprocessor`, identifies and matches critical points (`_match_critical_points`) using `NodeSimilarityCalculator`, finds paths between matched critical points (`_find_paths_to_next_critical`), matches these paths (`_find_optimal_path_matches_with_mapping`), and builds a reduced result graph by merging properties along the shorter path template (`_create_reduced_path_in_result`).
    *   **Components:** `CriticalPointPreprocessor`, `NodeSimilarityCalculator`, `PropertyHandlerManager`.

2.  **`ConceptMinorClassifier` (Current Classification):**
    *   **Goal:** Check if a concept graph is a "minor" of an image graph (concept structure exists within image, allowing contractions, properties must match).
    *   **Key Steps:** Loads concept/image, checks basic compatibility (size, labels), iterates through `StartPoint` pairs, uses a frontier-based search (`_find_concept_minor_mapping`) to map concept nodes to image nodes (allowing contractions via path finding like `_find_paths_bfs`), uses basic property checks (`_check_node_properties_match`), scores based on percentage of concept nodes mapped.
    *   **Components:** `PropertyMatcherManager`, custom search logic.

**Key Differences & Alignment Opportunity:**

*   **Preprocessing:** Concept creation uses explicit preprocessing (`CriticalPointPreprocessor`) to standardize graphs *before* matching; classification does not.
*   **Matching Strategy:** Creation focuses on matching *critical points* first and then matching the *paths* between them. Classification uses a general graph search starting from `StartPoints`.
*   **Similarity:** Creation uses `NodeSimilarityCalculator` for potentially richer node comparison. Classification uses simpler, stricter property subset checks.
*   **Goal Nuance:** Creation finds *common ground*. Classification checks for *containment* (minor). Aligning means classification might shift towards finding "how much of the concept is present" rather than a strict minor check.

**Proposed Plan:**

1.  **Integrate Preprocessing:**
    *   In `ConceptMinorClassifier._check_concept_minor_tx`, before any matching starts, apply `CriticalPointPreprocessor.preprocess_graphs` to both the loaded `concept_graph` and the `image_graph`.
    *   Use the *preprocessed* graphs for all subsequent steps within the function.

2.  **Adopt Critical Point-Centric Matching:**
    *   Replace the `StartPoint` iteration and `_find_concept_minor_mapping` call.
    *   **Identify Critical Points:** Use the preprocessor's method (`preprocessor._identify_critical_points`) on both preprocessed graphs.
    *   **Match Critical Points:** Implement a method similar to `GraphMinorFinder._match_critical_points`. This will involve:
        *   Using `NodeSimilarityCalculator.calculate_node_similarity` to compare potential critical point pairs of the same type.
        *   Creating a `critical_point_mapping: Dict[concept_cp_node, image_cp_node]`.
        *   Check if a `StartPoint` was successfully mapped. If not, it's likely a low/zero match score.
    *   **Match Paths Between Critical Points:** Implement logic similar to `_build_reduced_intersection` (but without building a new graph, just calculating the match):
        *   Iterate through the `critical_point_mapping`.
        *   Use `_find_paths_to_next_critical` (adapted from `GraphMinorFinder`) on both graphs to find paths between pairs of *mapped* critical points.
        *   Use `_find_optimal_path_matches_with_mapping` (adapted from `GraphMinorFinder`) to find the best corresponding path pairs between the concept and image graphs. This uses `_calculate_path_similarity`.

3.  **Refine Scoring:**
    *   The score should no longer be just `mapping_size / concept_size`.
    *   Develop a score based on the *matched structure*:
        *   How many critical points were matched? (Weight based on type?)
        *   How many paths between critical points were matched?
        *   What is the cumulative similarity score of matched paths/nodes?
    *   The final score should represent the proportion of the *concept's* structure (critical points and interconnecting paths) found in the *image*, weighted by similarity.

4.  **Component Reuse & Consistency:**
    *   Import and instantiate `CriticalPointPreprocessor` and `NodeSimilarityCalculator` within `ConceptMinorClassifier`.
    *   Replace calls to `_check_node_properties_match` with calls to `NodeSimilarityCalculator.calculate_node_similarity` or a compatible method derived from it, where appropriate (e.g., when comparing critical points or nodes along paths).
    *   Review `PropertyMatcherManager` vs. `PropertyHandlerManager`. Since classification isn't merging properties, the existing `PropertyMatcherManager` might be sufficient *if* its logic is compatible with the similarity calculations needed. If `NodeSimilarityCalculator` handles property comparisons internally, `PropertyMatcherManager` might become less relevant.

5.  **Refactor:**
    *   Rename methods like `_check_concept_minor_tx` to reflect the new approach (e.g., `_calculate_concept_similarity_tx`).
    *   Update docstrings to explain the new critical-point and path-matching strategy.

This plan replaces the core matching algorithm in classification with one mirroring concept creation, focusing on standardized critical points and the paths connecting them, using more sophisticated similarity measures.
