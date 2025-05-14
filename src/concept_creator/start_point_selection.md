# Start Point Selection Strategy for Concept Creation

To ensure robust concept creation, especially when dealing with variations or noise across different graph samples representing the same concept, a specific strategy is employed to select the initial starting point for graph matching. This strategy leverages clustering of critical points (endpoints and branching points) identified in the skeleton graphs of all samples.

## Strategy Steps

1.  **Identify Critical Points:** For each sample graph belonging to the concept being created, identify all critical points based on their labels in the graph data. These include:
    *   `EndPoint`
    *   `CornerPoint`
    *   `IntersectionPoint` (often representing branching points)
    *   `StartPoint` (the initial point from contour analysis)

2.  **Cluster Critical Points:** Collect all critical points from all sample graphs. Perform cluster analysis (e.g., using k-means or DBSCAN) on these points based on their **normalized spatial coordinates** (`normalized_x`, `normalized_y`), which represent coordinates relative to the center of mass. This groups structurally similar points across different samples based on their relative positions.

3.  **Determine Structure Type:** Analyze the overall structure type based on the presence of `EndPoint` labels across the samples:
    *   **Open Structure:** At least one sample graph contains one or more nodes with the `EndPoint` label.
    *   **Closed Structure:** None of the sample graphs contain any nodes with the `EndPoint` label (e.g., a perfect circle).

4.  **Select Candidate Clusters:** Based on the structure type, filter the clusters identified in Step 2 by the primary type of critical point they contain:
    *   **Open Structure:** Only consider clusters primarily composed of points with the `EndPoint` label. The `StartPoint` might also be considered if it consistently represents an end feature across samples.
    *   **Closed Structure:** Consider clusters primarily composed of `CornerPoint` or `IntersectionPoint` labels. `EndPoint` and `StartPoint` clusters are excluded for closed structures as they indicate an open contour end.

5.  **Filter by Sample Representation:** From the candidate clusters, select only those that satisfy the *full representation* criterion: a cluster must contain at least one critical point from **each** of the original sample graphs. This ensures the chosen starting point type is present across all examples of the concept.

6.  **Select Final Start Point Cluster:** If multiple clusters satisfy the full representation criterion (Step 5), choose the cluster whose average point position is the "top-leftmost". This is determined by selecting the cluster with the minimum average `(2 * x + y)` value across its points.

7.  **Determine Start Point:** The centroid (or a representative point) of the final selected cluster represents the optimal starting point characteristic for matching graphs of this concept. When initiating the matching process for a new graph against this concept, the algorithm should start from a critical point on the new graph that is closest in type and location to this determined starting point characteristic. 