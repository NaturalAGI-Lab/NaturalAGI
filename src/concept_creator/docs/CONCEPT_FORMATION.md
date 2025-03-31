# Concept Formation Algorithm

## Overview

The Concept Formation algorithm in NaturalAGI creates abstract representations of object classes by finding the "intersection graph" from all training sample graphs. This approach differs from traditional neural networks as it doesn't use backpropagation but instead relies on structural analysis and statistical reduction to identify common patterns across examples.

## Core Principles

1. A concept is the essential structural representation that is common across all training samples of a class
2. Critical points contain the most information about the structure of an object
3. The concept graph should be a minor (simplified subset) of all training sample graphs
4. Statistics of properties should be preserved in the concept

## Algorithm Steps

### 1. Critical Points Identification

The first step identifies critical points in each training sample graph. Critical points are structural elements that contain significant information:

- **Intersection Points**: Where multiple vectors meet
- **Corner Points**: Where the contour changes direction significantly
- **End Points**: Terminal points of a structure
- **Start Points**: Beginning point of a structure

These points collectively define the topological structure of the object and serve as anchors for matching across samples.

### 2. Creating the Intersection Graph

1.  **Initialization:** Start with the graph representation of the first training sample. This graph becomes the initial "temporary concept graph".
2.  **Iteration:** For each subsequent training sample graph:
    *   **Identify Critical Point Sequences:** Trace paths between consecutive critical points (StartPoint, EndPoint, IntersectionPoint, CornerPoint) in both the temporary concept graph and the current sample graph.
    *   **Substructure Matching:** Compare the sequence of critical points and the paths (subgraphs) between them from both graphs.
        *   Find corresponding critical points. This might involve coordinate proximity checks or topological matching.
        *   If critical points don't match exactly by type (e.g., CornerPoint vs. IntersectionPoint), apply **Type Reduction** according to defined rules (Intersection -> Corner -> Point) to see if a match can be established at a more general level. StartPoints and EndPoints cannot be reduced.
    *   **Find Maximum Common Minor:** For matched segments between critical points, identify the common structural elements (points and vectors). If one path has more intermediate points/vectors than the other, simplify the more complex path by removing intermediate elements (applying graph minor operations) until only the shared structure remains. The goal is to find the largest subgraph that is a minor of both the temporary concept's segment and the sample's segment.
    *   **Handle Mismatched Critical Points:** If a critical point exists in one graph but has no corresponding point in the other within the sequence, it's considered specific to that sample and is removed from the structure being considered for the updated concept.
    *   **Update Temporary Concept:** Modify the temporary concept graph based on the comparison:
        *   Keep only the common critical points and the common minor structures between them.
        *   Update properties (like average coordinates, vector lengths/angles) based on the statistics from the samples encountered so far that share this structure. For example, the position of a point in the concept graph could be the average position of the corresponding points in the samples.
3.  **Finalization:** After iterating through all training samples, the resulting temporary concept graph becomes the final concept graph for that object class. It represents the statistically significant common structure across all samples.

<!-- To create the intersection graph we should identify the start points of each graph. As this is iterative process we start from the first graph and make it a concept graph (temporary concept graph).
Then we get the next graph and find StartPoint for it. Then we should find the next critical point of the temporary concept graph and the next graph. We should find the maximum common minor for the given subgraphs (temporary concept graph and the next image/training sample graph).
For example: 
We have sample of number 1. We start from the StartPoint and trying to find the next CriticalPoint. That will be EndPoint (and the Vector between StartPoint and EndPoint). We do this for the temp concept and the next training sample.
Then we should match the obtained substructure between these critical points. It can be that one of the substructures has more intermediate structural elements (Vectors and Points) then the other one. In this case we should remove the extra elements from the substructure with more elements.
To do this we should use the graph minor approach.
There also can be a case when one graph has more critical points then the other one. In this case we should remove the extra critical points from the graph with more critical points.
Critical points are: IntersectionPoint, EndPoint, CornerPoint. If one graph has CornerPoint and the other one has IntersectionPoint, we can transform IntersectionPoint to CornerPoint (the same can be applied to the CornerPoint to Point. So called "type reduction"). That can be the case with samples with some noise. That's why we should use the graph minor approach to find the maximum common minor for the given subgraphs. -->

**Type reduction** is the process of reducing the type of structural element to the more general one. For example: 
- IntersectionPoint can be reduced to CornerPoint.
- CornerPoint can be reduced to Point.
- VerticalVector can be reduced to Vector.
- HorizontalVector can be reduced to Vector.

**The exception is the StartPoint and EndPoint. They can't be reduced.**

## Advantages of Graph Intersection Approach

1. **Interpretability**: The resulting concept is a concrete graph structure that can be visualized and understood
2. **Generalization**: Captures the essential structure while filtering out sample-specific variations
3. **No Backpropagation**: Learning occurs through structural analysis rather than gradient descent
4. **Data Efficiency**: Can form meaningful concepts from fewer examples compared to deep learning approaches

## Practical Implementation

The concept creation process is implemented in two phases:

1. **Training Data Processing**: Generate graph representations for multiple samples of each class
2. **Post-processing**: Extract the common graph structure across all graphs for a particular class

The resulting concept graph serves as a structural template for classification, where new inputs are matched against these templates to identify the most similar concept.
