# Maximum Common Minor Graph Approach to Concept Formation

## Overview

This document outlines a flexible approach to concept formation in NaturalAGI based on Maximum Common Minor Graph principles. The approach modifies the current concept formation process to achieve more efficient and accurate concept representation through iterative graph matching, edge contractions, and property preservation. This approach is particularly useful for classifying structural patterns such as MNIST digits, where each digit has characteristic shapes that can be represented as graphs.

## Current vs. Implemented Approach

### Current Approach
Currently, NaturalAGI processes multiple training images independently, creating graph representations for each. After all images are processed, a post-processing step performs statistical reduction to identify common features across all samples, forming a concept.

### Implemented Approach
The implemented approach changes the order of operations:

1. Build graph representations for all training images
2. Start with the first image's graph as the initial concept graph
3. For each subsequent image:
   - Find the maximum common minor graph between the current concept graph and the new image graph, beginning with matching "StartPoint" nodes as anchors
   - Update the concept graph to be this maximum common minor
   - Preserve only matching properties in the concept graph
   - Apply edge contractions to capture structural similarities even when exact structures differ
4. The final concept graph contains the common structure across all training samples with necessary contractions

This approach maintains only one concept graph that evolves with each new training sample, rather than processing all samples independently and then combining them.

## MNIST Digit Classification

When applied to MNIST digit classification, this approach creates concept graphs for each digit class by finding common structural patterns across training examples. These concept graphs capture the essential features that define each digit:

- Digit "1" might be represented as a simple vertical line with 2 endpoints (one of which is a StartPoint)
- Digit "8" would have a characteristic structure with two loops
- Digit "3" would show a pattern with multiple vectors and endpoints

The classification occurs by matching new input digits against these concept graphs using the maximum common minor approach, allowing for flexible recognition even with handwriting variations.

## Anchor-Based Traversal for Finding Maximum Common Minor Graphs

The implemented approach uses a special anchor-based traversal method for finding maximum common minor graphs:

1. **StartPoint Anchoring**: The algorithm identifies special "StartPoint" nodes in both graphs and uses them as anchors for the initial matching
2. **Growing from Anchors**: Once anchors are established, the algorithm grows the common minor outward from these points through the graph
3. **Frontier Exploration**: The algorithm maintains a "frontier" of nodes adjacent to the current match and iteratively finds the best matches to add
4. **Fallback Mechanism**: If no StartPoints are available, the algorithm falls back to a standard maximum common subgraph approach

This anchor-based approach ensures that structurally significant points are aligned first, leading to more meaningful graph matches and better concept formation.

## Property Preservation in Concept Formation

A critical aspect of the implemented approach is how node properties are preserved during concept formation:

1. **Label Intersection**: For node labels, the algorithm takes the intersection of label sets between matching nodes
2. **Exact Property Matching**: For other properties, only values that match exactly in both graphs are preserved
3. **Property Consistency**: When applying contractions, the algorithm ensures that properties remain consistent across all nodes that map to the same concept node
4. **Incremental Property Refinement**: With each new training sample, properties in the concept graph become more precise, preserving only consistent features

This ensures that the final concept graph contains only the essential, consistent properties that define the concept across all training samples.

## Graph Minors: A Flexible Approach to Structural Matching

A graph minor is a graph that can be obtained from another graph by a sequence of edge contractions, edge deletions, and vertex deletions. In our approach, we focus primarily on edge contractions, which allow us to match graphs that have different numbers of nodes but similar overall structures.

When we contract an edge, we merge its endpoints into a single vertex, preserving connections to all other nodes. This provides more flexibility in matching compared to strict subgraph isomorphism, allowing us to recognize structural similarities even when the exact number or arrangement of nodes differs.

## Technical Implementation

### 1. Incremental Concept Formation Process

The implementation follows these steps:
```
1. Extract the graph for the first image in the training set
2. Use this as the initial concept graph
3. For each subsequent image:
   - Extract its graph representation
   - Find the maximum common minor graph between the current concept and this new image
   - Update the concept to be this common minor
   - Track all contractions applied
4. Generate a deterministic concept ID based on the final graph structure
5. Store the resulting concept graph in the database
```

### 2. Maximum Common Minor with StartPoints

The core algorithm for finding the maximum common minor works as follows:

1. **Initialize**: Create empty mappings and a new graph for the maximum common minor
2. **Anchor at StartPoints**: Find all StartPoint nodes in both graphs and match them as anchors
3. **Grow the Match**: From these anchors, grow the match outward by:
   - Finding the best matches between frontier nodes based on common neighbors
   - Applying edge contractions when direct matches aren't possible
   - Maintaining property consistency during growth
4. **Return Results**: Return the maximum common minor graph along with mappings from original graph nodes to MCM nodes

### 3. Edge Contraction Strategy

The implementation uses a quality-based approach to edge contractions:

1. **Contraction Quality Scoring**: Potential contractions are scored based on:
   - Number of common neighbors they would create
   - Property similarity between the nodes being contracted
   - Structural role in the graph
2. **Prioritized Application**: Contractions with higher scores are applied first
3. **Validation**: Contractions are only applied if they maintain graph consistency

### 4. Property Handling During Contractions

When contracting edges, properties are handled carefully to maintain consistency:

- Special handling for node labels (intersection of label sets)
- Removal of properties that don't match across all nodes mapping to the same concept node
- Addition of new matching properties if they don't already exist
- Preservation of only the consistent features across samples

### 5. Node Matching

Node matching determines if two nodes should be considered equivalent based on:
- Node labels and types
- Critical point classifications (endpoints, intersections, corners)
- Common structural roles in the graph

### 6. Visualization Support

The implementation includes optional visualization callbacks that allow for:
- Visualizing each step of the concept formation process
- Highlighting StartPoint nodes used as anchors
- Tracking property changes during contractions
- Comparing pre and post-contraction graphs

## Theoretical Foundation

### Maximum Common Minor Graph for Concept Formation

The maximum common minor graph approach provides several advantages for concept formation:

1. **Structural Flexibility**: By allowing edge contractions, we can identify shared structural patterns even when the exact number of nodes or edges differs between graphs.

2. **Graceful Degradation**: Instead of requiring exact matches, the minor approach allows for partial matching with edge contractions, providing a more robust concept representation.

3. **Property Matching**: By preserving only matching properties, we ensure that the concept graph contains only the consistent features across samples, eliminating noise and variations.

4. **Simplified Structure**: Edge contractions reduce the complexity of the graph while preserving its essential topology.

### Incremental Learning

This approach implements a form of incremental learning where:

1. Each new sample contributes to refining the concept
2. The concept representation becomes more precise with each sample
3. Only one graph (the concept) is maintained throughout training
4. Edge contractions capture structural similarities despite differences in exact node counts
5. Only matching properties are preserved, ensuring consistency

### Advantages of the Implemented Approach

The anchor-based traversal approach for maximum common minor offers several advantages:

1. **Structural Significance**: By anchoring at StartPoints, the algorithm focuses on structurally significant parts first
2. **Efficient Traversal**: Growing from anchors is computationally more efficient than trying all possible matches
3. **Meaningful Contractions**: Contractions are applied based on structural and property similarity, leading to more meaningful concept graphs
4. **Incremental Refinement**: The concept becomes more refined with each new training sample
5. **Memory Efficiency**: Only one concept graph is maintained throughout the process
6. **Deterministic Results**: The approach produces deterministic concepts for the same training set

## Integration with Current System

The implementation integrates with the existing NaturalAGI system through:

1. **ConceptCreationRepository**: Interfaces with Neo4j for retrieving image graphs and storing concepts
2. **Neo4jToNetworkx/NetworkxToNeo4j**: Converters for moving between graph database and NetworkX representations
3. **Visualization Support**: Optional callbacks for visualizing each step of the concept formation process
4. **Session-based Processing**: Organizes training samples by session ID for coherent concept formation

## Conclusion

The implemented Maximum Common Minor Graph approach with anchor-based traversal provides a robust, flexible method for concept formation in NaturalAGI. By using StartPoints as anchors, growing matches through frontier exploration, and applying strategic edge contractions, the approach can effectively learn concepts from structural patterns.

For MNIST digit classification, this approach offers a natural way to learn and recognize digits based on their structural properties rather than pixel-level features, aligning with the core philosophy of NaturalAGI by emphasizing structural analysis rather than traditional neural network approaches. 