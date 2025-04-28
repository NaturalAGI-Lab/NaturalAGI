# Maximum Common Minor Graph (MCMG) for Concept Formation

## Overview

This document explains the implementation of the Maximum Common Minor Graph (MCMG) approach in NaturalAGI for flexible and robust concept formation. The refactored implementation uses a traversal-based approach to find a structure that is minor to all training samples. The key features of this approach include:

1. Traversal-based matching starting from StartPoint nodes
2. Strict type matching (point-to-point, vector-to-vector)
3. Property intersection to preserve only common attributes
4. Edge contractions to achieve structural equivalence
5. Incremental concept formation with detailed contraction tracking

## Technical Implementation

### Core Function

The core of the implementation is the `find_max_common_minor_graph` function in the `MaximumCommonSubgraph` class:

```python
def find_max_common_minor_graph(
    graph1: nx.Graph, 
    graph2: nx.Graph, 
    node_match: Optional[Callable[[Dict, Dict], bool]] = None,
    max_contractions: int = 3,
    property_threshold: float = 0.1
) -> Tuple[nx.Graph, Dict[str, str]]
```

This function:
- Takes two input graphs and optional parameters
- Identifies StartPoint nodes as anchors for traversal
- Traverses both graphs simultaneously to find matching structures
- Applies edge contractions to achieve structural equivalence
- Preserves only the intersection of properties
- Returns the MCMG and a dictionary of contractions

### Traversal-Based Matching

The refactored approach explicitly traverses both graphs in parallel:

1. Starting from matched StartPoint nodes (or EndPoints if no StartPoints exist)
2. Using breadth-first search to explore the graphs
3. Matching nodes strictly based on their types (point-to-point, vector-to-vector)
4. Only keeping properties that are common to both graphs

This traversal approach provides better control over the matching process and ensures that the topological structure is properly preserved.

### Strict Type Matching

Type matching is enforced strictly by the `_strict_type_node_match` function:

```python
def _strict_type_node_match(node1_data: Dict, node2_data: Dict) -> bool:
    # Check if labels intersect at all
    if not node1_labels.intersection(node2_labels):
        return False
        
    # StartPoint can only match with StartPoint
    if "StartPoint" in node1_labels or "StartPoint" in node2_labels:
        return "StartPoint" in node1_labels and "StartPoint" in node2_labels
        
    # EndPoint can only match with EndPoint
    if "EndPoint" in node1_labels or "EndPoint" in node2_labels:
        return "EndPoint" in node1_labels and "EndPoint" in node2_labels
        
    # Point types match only with the same point types
    if "Point" in node1_labels and "Point" in node2_labels:
        # Critical points must match exactly with the same type
        critical_types = {"IntersectionPoint", "CornerPoint"}
        node1_critical = node1_labels.intersection(critical_types)
        node2_critical = node2_labels.intersection(critical_types)
        
        if node1_critical or node2_critical:
            return node1_critical == node2_critical
        return True  # Regular points can match
        
    # Vectors can only match with vectors
    if "Vector" in node1_labels and "Vector" in node2_labels:
        return True
        
    # No match in all other cases
    return False
```

This ensures that:
- Points match only with points of the same type
- Vectors match only with vectors
- Critical points (StartPoint, EndPoint, IntersectionPoint, CornerPoint) match only with the same type

### Property Intersection

Properties are preserved by taking the strict intersection:

```python
def _get_property_intersection(data1: Dict, data2: Dict) -> Dict:
    intersection = {}
    
    # Handle labels specifically (take set intersection)
    if "labels" in data1 and "labels" in data2:
        labels1 = set(data1["labels"] if isinstance(data1["labels"], list) else [data1["labels"]])
        labels2 = set(data2["labels"] if isinstance(data2["labels"], list) else [data2["labels"]])
        
        common_labels = labels1.intersection(labels2)
        if common_labels:
            intersection["labels"] = list(common_labels)
    
    # Handle other properties
    for key in data1:
        if key != "labels" and key in data2:
            # For numerical properties
            if isinstance(data1[key], (int, float)) and isinstance(data2[key], (int, float)):
                # Take the average value
                intersection[key] = (data1[key] + data2[key]) / 2
            # For non-numerical properties, must be exactly equal
            elif data1[key] == data2[key]:
                intersection[key] = data1[key]
    
    return intersection
```

This ensures that:
- For labels, only common types are preserved (via set intersection)
- For numerical properties, the average value is used
- For other properties, exact matching is required

### Edge Contraction Process

The refactored contraction process focuses on finding structural equivalence:

1. Identify candidate edges for contraction based on node types and topology
2. Apply contractions one at a time and re-evaluate matching
3. Keep contractions that improve the matching by increasing the number of matched nodes
4. Track all applied contractions for diagnostic purposes

## Using the Traversal-Based MCMG Approach

### Basic Usage

```python
import networkx as nx
from maximum_common_subgraph import MaximumCommonSubgraph

# Create or load your graphs
graph1 = ...  # Your first graph
graph2 = ...  # Your second graph

# Find the Maximum Common Minor Graph
mcmg, contractions = MaximumCommonSubgraph.find_max_common_minor_graph(
    graph1, graph2, max_contractions=3, property_threshold=0.1
)

# The mcmg variable now contains the common structure
# The contractions dictionary maps contracted nodes to their representatives
```

### Finding a Structure Minor to All Samples

To find a structure that is minor to multiple training samples, the approach can be applied incrementally:

```python
# Start with the first graph as the initial concept
concept_graph = graphs[0].copy()
all_contractions = {}

# Process each additional graph
for i in range(1, len(graphs)):
    # Find the common minor graph between the current concept and the next training sample
    minor, contractions = MaximumCommonSubgraph.find_max_common_minor_graph(
        concept_graph, graphs[i], max_contractions=3, property_threshold=0.1
    )
    
    # Update the concept to be the minor graph
    concept_graph = minor
    
    # Track contractions
    all_contractions.update(contractions)
```

This incremental process results in a concept graph that is structurally minor to all training samples, with only properties that are common across all samples.

## Benefits of the Traversal-Based Approach

The traversal-based MCMG approach offers several advantages:

1. **Explicit Control**: The traversal approach provides more explicit control over how graphs are matched, ensuring that structural relationships are properly preserved.

2. **Type Safety**: Strict type matching ensures that points match only with points and vectors match only with vectors, resulting in more semantically valid matches.

3. **Property Consistency**: The intersection of properties ensures that only attributes common to all samples are preserved, resulting in more robust concept representations.

4. **Structural Reduction**: Edge contractions enable finding common structure even when graphs have different granularity or level of detail.

5. **Explainability**: The process is more transparent and easier to debug, as each step of the traversal and contraction process can be inspected.

## Integration with Neo4j

The contractions are stored in the Neo4j database as relationships:

```cypher
MATCH (c:Concept)-[r:HAS_CONTRACTION]->(c)
RETURN r.from_node, r.to_node
```

This allows for tracking and visualization of how the concept was formed through edge contractions.

## Visualization

The test scripts include visualization capabilities to render graphs with color-coding for different node types:
- StartPoints (green)
- EndPoints (red)
- IntersectionPoints (purple)
- Regular Points (blue)
- Vectors (orange)

This makes it easier to understand the results of the MCMG process and the structure of the resulting concepts.

## Conclusion

The traversal-based Maximum Common Minor Graph approach provides a more controlled and semantically valid method for concept formation in NaturalAGI. By traversing graphs simultaneously, strictly enforcing type matching, and preserving only common properties, we can find a structure that is minor to all training samples. This results in more robust and meaningful concept representations for structural pattern recognition. 