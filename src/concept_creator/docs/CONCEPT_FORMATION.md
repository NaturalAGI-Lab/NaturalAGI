# Concept Formation Algorithm

## Overview

The Concept Formation algorithm in NaturalAGI creates abstract representations of object classes by finding the "intersection graph" from all training sample graphs. This approach differs from traditional neural networks as it doesn't use backpropagation but instead relies on structural analysis and statistical reduction to identify common patterns across examples.

## Core Principles

1. A concept is the essential structural representation that is common across all training samples of a class
2. Critical points contain the most information about the structure of an object
3. The concept graph should be a minor (simplified subset) of all training sample graphs
4. Only matched properties should be preserved in the concept

## Algorithm Steps

### 1. Critical Points Identification

The first step identifies critical points in each training sample graph. Critical points are structural elements that contain significant information:

- **Intersection Points**: Where multiple vectors meet
- **Corner Points**: Where the contour changes direction significantly
- **End Points**: Terminal points of a structure
- **Start Points**: Beginning points of a structure

These points collectively define the topological structure of the object and serve as anchors for matching across samples.

### 2. Graph Matching

The core of the algorithm involves comparing graphs from different training samples by matching their critical points:

```
function find_concept_graph(training_sample_graphs):
    # Start with the first sample graph as the candidate concept
    concept_graph = training_sample_graphs[0]
    
    # Iteratively refine by comparing with each training sample
    for sample_graph in training_sample_graphs[1:]:
        # Find matching between critical points in both graphs
        point_matches = match_critical_points(concept_graph, sample_graph)
        
        # Update concept graph to keep only matched elements
        concept_graph = create_intersection_graph(concept_graph, sample_graph, point_matches)
    
    return concept_graph
```

### 3. Critical Points Matching

Critical points are matched based on:

1. **Topological similarity**: Position in the graph structure
2. **Geometric properties**: Spatial coordinates (normalized), angles, etc.
3. **Feature similarity**: Similar property values across samples
4. **Structural role**: Type of point (intersection, corner, endpoint, etc.)

```
function match_critical_points(graph1, graph2):
    matches = []
    
    # Get critical points from both graphs
    critical_points1 = get_critical_points(graph1)
    critical_points2 = get_critical_points(graph2)
    
    # Create similarity matrix between points
    similarity_matrix = calculate_similarity_matrix(critical_points1, critical_points2)
    
    # Use Hungarian algorithm or similar optimization to find optimal matching
    matches = optimize_matching(similarity_matrix)
    
    return matches
```

### 4. Creating the Intersection Graph

The intersection graph preserves only the structural elements that can be matched across samples:

```
function create_intersection_graph(graph1, graph2, point_matches):
    intersection_graph = new_empty_graph()
    
    # Add matched points to the intersection graph
    for point1, point2 in point_matches:
        # Create a new point with common properties
        new_point = create_point_with_common_properties(point1, point2)
        intersection_graph.add_node(new_point)
    
    # Add connections (vectors) between points that exist in both graphs
    for point1_a, point1_b in graph1.get_connections():
        # Find corresponding points in graph2
        if point1_a and point1_b in point_matches:
            point2_a = point_matches[point1_a]
            point2_b = point_matches[point1_b]
            
            # Check if connection exists in graph2
            if connection_exists(graph2, point2_a, point2_b):
                # Create vector with common properties
                vector = create_vector_with_common_properties(
                    graph1.get_vector(point1_a, point1_b),
                    graph2.get_vector(point2_a, point2_b)
                )
                intersection_graph.add_connection(
                    point_matches[point1_a], 
                    point_matches[point1_b], 
                    vector
                )
    
    return intersection_graph
```

### 5. Property Preservation

The algorithm preserves common properties across matched elements:

```
function create_point_with_common_properties(point1, point2):
    new_point = new_empty_point()
    
    # Compare all properties
    for property_name in get_all_properties(point1, point2):
        if property_exists_in_both(point1, point2, property_name):
            if properties_match(point1, point2, property_name):
                # Add exact property if identical
                new_point[property_name] = point1[property_name]
            else:
                # Add statistical average for numeric properties
                if is_numeric_property(property_name):
                    new_point[property_name] = average(
                        point1[property_name], 
                        point2[property_name]
                    )
                # For categorical properties, keep if they match, otherwise omit
    
    return new_point
```

### 6. Concept Refinement

The final step involves refining the concept graph to ensure it accurately represents the class:

1. **Pruning**: Remove elements that don't contribute to the structural essence
2. **Connectivity check**: Ensure the concept graph remains connected
3. **Normalization**: Standardize spatial coordinates and other features

## Implementation Details

### Graph Representation

The concept graph uses a bipartite structure where:

- **Nodes** represent points with specific types:
  - Regular points
  - Endpoints (including Start Points)
  - Intersections
  - Corner points (angle points)
- **Relationships** connect elements:
  - Points connect to vectors via `:CONNECTED_TO` relationships
  - Vectors are stored as nodes with properties

### Critical Properties

When matching and preserving properties, the algorithm prioritizes these critical features:

- **Topological features**: 
  - `intersection_points_count`
  - `endpoints_count`
  - `corner_points_count`
  - `vectors_count`
  - `cycle_count`

- **Geometric features**:
  - `normalized_x` and `normalized_y`
  - `angle`
  - `quadrant`
  - `quadrant_change_count`
  - `monotony`

- **Segment information**:
  - `segments` (e.g., "top", "bottom", "left", "right")
  - `contour_type`

### Statistical Approach

The algorithm uses statistical methods to identify the most stable elements across samples:

1. Elements that appear in most/all training samples are preserved
2. Elements with consistent properties across samples receive higher confidence scores
3. Property values in the concept graph reflect statistical measures (mean, mode) across samples

## Technical Stack

The concept formation algorithm in NaturalAGI is implemented using a set of specialized technologies and tools:

### Core Technologies

1. **Python** - Primary programming language for algorithm implementation
2. **NetworkX** - Graph manipulation library used for:
   - Creating and modifying graph structures
   - Graph analysis and traversal
   - Implementation of graph algorithms like Maximum Common Minor Graph (MCMG)

3. **Neo4j** - Graph database that:
   - Stores the structural representations of images and concepts
   - Enables efficient graph queries
   - Maintains the bipartite graph structure (points and vectors)

4. **Nuclio** - Serverless function platform that:
   - Runs the concept creator as a microservice
   - Handles API requests for concept formation
   - Enables scalable processing of multiple formation tasks

5. **Kafka** - Message broker that:
   - Coordinates communication between components
   - Triggers concept formation when training samples are processed
   - Enables asynchronous event-driven architecture

## Advantages of Graph Intersection Approach

1. **Interpretability**: The resulting concept is a concrete graph structure that can be visualized and understood
2. **Generalization**: Captures the essential structure while filtering out sample-specific variations
3. **No Backpropagation**: Learning occurs through structural analysis rather than gradient descent
4. **Data Efficiency**: Can form meaningful concepts from fewer examples compared to deep learning approaches

## Limitations and Future Improvements

1. **Sensitivity to Variations**: Large structural variations across samples may result in overly simplified concepts
2. **Matching Complexity**: Finding optimal point matches is computationally intensive
3. **Property Selection**: Determining which properties to preserve requires domain expertise

## Practical Implementation

The concept creation process is implemented in two phases:

1. **Training Data Processing**: Generate graph representations for multiple samples of each class
2. **Post-processing**: Extract the common graph structure across all graphs for a particular class

The resulting concept graph serves as a structural template for classification, where new inputs are matched against these templates to identify the most similar concept.
