# Refactoring Plan: Two-Stage Growing Match for Graph Minor Finder

**Date:** April 4, 2024

**Goal:** Replace the current path-finding and matching logic in `GraphMinorFinder` (`_build_reduced_intersection`, `_find_optimal_path_matches_with_mapping`) with a more robust two-stage approach based on synchronized traversal and strict critical point mapping. This aims to eliminate errors where different critical point types were incorrectly matched during path construction.

**Overall Approach:**

The new algorithm will operate in two distinct stages:

1.  **Stage 1: Critical Skeleton Construction:** Build a preliminary graph containing only the *matched critical points* and edges representing direct, corresponding connectivity between them in both the concept (`G_c`) and image (`G_i`) graphs. This stage uses a BFS-like traversal starting from the matched `StartPoints` and strictly enforces the pre-computed `critical_point_mapping`. Structural mismatches at the critical point level will raise errors.
2.  **Stage 2: Substructure Reduction:** Use the critical skeleton graph generated in Stage 1 as a template. For each edge in the skeleton (representing a connection between two critical points), retrieve the actual paths from the original graphs and apply the *existing* path reduction logic (`_create_reduced_path_in_result`) to fill in the intermediate nodes and edges in the final `result_graph`.

---

## Stage 1: Critical Skeleton Construction

**Function:** `_build_critical_skeleton(self, G_c, G_i, cp_map, start_c, start_i)`

**Input:**

*   `G_c`: Preprocessed concept graph.
*   `G_i`: Preprocessed image graph.
*   `cp_map`: The strict one-to-one mapping from concept critical points to image critical points (result of `_match_critical_points`).
*   `start_c`: The StartPoint node ID in `G_c`.
*   `start_i`: The StartPoint node ID in `G_i` (where `cp_map[start_c] == start_i`).

**Output:**

*   `critical_skeleton_graph`: An `nx.Graph` where:
    *   Nodes are critical point IDs from `G_c` that have a valid match and are reachable. Node data contains merged properties from `G_c` and `G_i`.
    *   Edges `(u_c, v_c)` exist if and only if there is a path of non-critical nodes between `u_c` and `v_c` in `G_c`, AND a corresponding path between `cp_map[u_c]` and `cp_map[v_c]` in `G_i`.
    *   Edge attributes store the actual paths: `path_c` and `path_i`.

**Algorithm:**

1.  **Initialization:**
    *   `critical_skeleton_graph = nx.Graph()`
    *   `queue = collections.deque([(start_c, start_i)])`
    *   `visited_critical_pairs = {(start_c, start_i)}` # Tracks (concept_cp, image_cp) pairs added to queue/processed
    *   `all_critical_c = set(cp_map.keys())`
    *   `all_critical_i = set(cp_map.values())`
    *   **Add Start Node:** Merge properties of `start_c` and `start_i` using `self.prop_manager`. Add node `start_c` to `critical_skeleton_graph` with merged properties.

2.  **BFS Traversal Loop:** While `queue` is not empty:
    *   Dequeue `(current_c, current_i)`.
    *   `self.logger.debug(f"Skeleton Stage: Processing critical pair ({current_c}, {current_i})")`
    *   **Find Reachable Critical Neighbors:**
        *   Find all pairs `(next_c, path_c)` reachable from `current_c` in `G_c` using `_find_paths_to_next_critical(G_c, current_c, all_critical_c)`. Filter results to only include `next_c` that are in `cp_map`. Store these as `reachable_c = {next_c: path_c for next_c, path_c in paths_from_c}`.
        *   Find all pairs `(next_i, path_i)` reachable from `current_i` in `G_i` using `_find_paths_to_next_critical(G_i, current_i, all_critical_i)`. Store these as `reachable_i = {next_i: path_i for next_i, path_i in paths_from_i}`.
    *   **Match Reachable Pairs & Validate Structure:** Iterate through `next_c` in `reachable_c.keys()`:
        *   Get the expected image partner: `expected_next_i = cp_map[next_c]`.
        *   **Structural Validation:** Check if `expected_next_i` is actually reachable from `current_i` (i.e., `expected_next_i` is in `reachable_i`).
            *   If `expected_next_i` is **NOT** in `reachable_i`: This is a structural mismatch between the graphs at the critical point level. Log a detailed error and `raise ValueError(f"Structural mismatch: {next_c} reachable from {current_c}, but mapped partner {expected_next_i} not reachable from {current_i}")`.
        *   If validation passes, we have found a valid corresponding connection: `(next_c, expected_next_i)`.
    *   **Process Valid Connections:** For each validated `next_c` (and its `expected_next_i`):
        *   Let `pair = (next_c, expected_next_i)`.
        *   Retrieve `path_c = reachable_c[next_c]` and `path_i = reachable_i[expected_next_i]`.
        *   If `pair` not in `visited_critical_pairs`:
            *   `self.logger.debug(f"Skeleton Stage: Found new connection {current_c} -> {next_c} (Image: {current_i} -> {expected_next_i})")`
            *   **Add Node:** If `next_c` not in `critical_skeleton_graph`, merge properties of `next_c` and `expected_next_i` and add node `next_c`.
            *   **Add Edge:** Add edge `(current_c, next_c)` to `critical_skeleton_graph` with attributes `{'path_c': path_c, 'path_i': path_i}`.
            *   **Enqueue:** `queue.append(pair)`
            *   **Mark Visited:** `visited_critical_pairs.add(pair)`
        *   Else (`pair` already visited):
            *   `self.logger.debug(f"Skeleton Stage: Found existing connection {current_c} -> {next_c} (Image: {current_i} -> {expected_next_i})")`
            *   **Add Edge (Handles Cycles):** If edge `(current_c, next_c)` doesn't exist in `critical_skeleton_graph`, add it with attributes `{'path_c': path_c, 'path_i': path_i}`.

3.  **Return:** `critical_skeleton_graph`.

**Helper Function:** `_find_paths_to_next_critical(self, graph, start_node, all_critical_nodes)`: This function will be similar to the existing one but optimized for this stage. It needs to find all simple paths from `start_node` to any node in `all_critical_nodes` that only traverse non-critical nodes intermediately. It should return a list of tuples `(critical_endpoint, path_list)`.

---

## Stage 2: Substructure Reduction

**Function:** `_fill_skeleton_paths(self, critical_skeleton_graph, G_c, G_i, cp_map)`

**Input:**

*   `critical_skeleton_graph`: The graph produced by Stage 1.
*   `G_c`: Preprocessed concept graph.
*   `G_i`: Preprocessed image graph.
*   `cp_map`: The critical point mapping.

**Output:**

*   `result_graph`: The final common minor graph with intermediate nodes filled in.

**Algorithm:**

1.  **Initialization:**
    *   `result_graph = nx.Graph()`
    *   `self.logger.info(f"Filling paths for critical skeleton with {len(critical_skeleton_graph.nodes)} nodes and {len(critical_skeleton_graph.edges)} edges.")`
2.  **Copy Nodes:** Copy all nodes from `critical_skeleton_graph` to `result_graph`, preserving their merged properties.
    *   `for node_c, data in critical_skeleton_graph.nodes(data=True): result_graph.add_node(node_c, **data)`
3.  **Process Edges:** Iterate through each edge `(u_c, v_c, edge_data)` in `critical_skeleton_graph.edges(data=True)`:
    *   Retrieve the stored paths: `path_c = edge_data['path_c']`, `path_i = edge_data['path_i']`.
    *   Get corresponding image nodes: `u_i = cp_map[u_c]`, `v_i = cp_map[v_c]`.
    *   `self.logger.debug(f"Filling path between ({u_c}, {u_i}) and ({v_c}, {v_i})")`
    *   **Call Existing Reducer:** Call the existing path reduction function:
        ```python
        self._create_reduced_path_in_result(
            result_graph,
            G_c, G_i,
            u_c, v_c, path_c,
            u_i, v_i, path_i
        )
        ```
        *Note: Ensure `_create_reduced_path_in_result` correctly handles adding nodes/edges to the `result_graph` passed to it and doesn't rely on internal state cleared between calls.*
4.  **Return:** `result_graph`.

---

## Implementation Plan

1.  **New Functions:**
    *   `_build_critical_skeleton(...)`: Implement Stage 1 logic.
    *   `_fill_skeleton_paths(...)`: Implement Stage 2 logic.
2.  **Modify Functions:**
    *   `find_max_common_minor(...)`:
        *   Keep steps 1-4 (preprocessing, identifying critical points, finding start points, matching critical points using `_match_critical_points`).
        *   Call `_build_critical_skeleton` to get the skeleton graph.
        *   Call `_fill_skeleton_paths` with the skeleton graph to get the final `result_graph`.
        *   Return the final `result_graph`.
    *   `_find_paths_to_next_critical(...)`: May need minor adjustments to ensure it fits Stage 1 requirements perfectly.
3.  **Reuse Functions:**
    *   `_match_critical_points(...)` (from current implementation)
    *   `_create_reduced_path_in_result(...)` (from current implementation - **verify statelessness**)
    *   Strict `_check_node_type_compatibility(...)` (from previous correction)
    *   `similarity_calculator`
    *   `prop_manager`
    *   `_identify_critical_points`
    *   `_find_start_point`
4.  **Delete Functions:**
    *   `_build_reduced_intersection(...)`
    *   `_find_optimal_path_matches_with_mapping(...)`
    *   Potentially other unused helper functions related to the old path-matching logic (`_calculate_path_similarity` might still be used by `_create_reduced_path_in_result`, need to check).

---

## Advantages of this Approach

*   **Strict Critical Point Correspondence:** Stage 1 explicitly enforces the `cp_map`, preventing incorrect critical point associations.
*   **Structural Validation:** Stage 1 fails early if the connectivity between corresponding critical points differs fundamentally between the graphs.
*   **Clear Separation:** Stage 1 handles the high-level critical structure, while Stage 2 focuses on the details of the paths between them.
*   **Code Reuse:** Leverages the existing (and presumably tested) logic for reducing the paths between critical points (`_create_reduced_path_in_result`).

## Potential Challenges

*   **Statelessness of `_create_reduced_path_in_result`:** Need to verify this function doesn't depend on state from previous calls within a single `find_max_common_minor` execution. It should operate correctly solely based on the `result_graph` passed into it and the other arguments.
*   **Performance:** The `_find_paths_to_next_critical` might be called multiple times. Ensure it's reasonably efficient. Caching might be considered if it becomes a bottleneck.
*   **Error Handling:** The `ValueError` in Stage 1 is strict. Decide if alternative handling (e.g., returning an empty graph or a partially matched graph) is desirable in some cases. For now, strict failure is implemented as requested.
*   **`_find_paths_to_next_critical` correctness:** Ensure this function correctly identifies *all* simple paths between critical points traversing only non-critical nodes.
