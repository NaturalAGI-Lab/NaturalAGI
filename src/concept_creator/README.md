# Concept Creator

The Concept Creator is a core component of the NaturalAGI system responsible for generating abstract concepts from multiple visual inputs. It uses graph-based representations and energy minimization techniques to extract common patterns across images.

## Overview

The concept creator takes a set of graph representations (typically derived from skeletonized images) and identifies common structural patterns between them. These patterns form the basis of "concepts" - abstract representations that capture the shared essence of multiple inputs.

The process is based on the Maximum Common Minor Graph (MCMG) approach, which allows for node contractions and flexible matching to identify structural similarities even when exact matches are not possible.

## Core Components

### Energy Minimization Concept Service

The `EnergyMinimizationConceptService` (in `energy_minimization_concept_service.py`) manages the creation of concepts using an energy minimization approach. It works by:

1. Processing images incrementally
2. Finding the maximum common minor graph between the current concept and each new image
3. Updating the concept based on these findings
4. Generating a unique concept ID
5. Storing the concept in Neo4j graph database

Key methods:

- `create_concept_incrementally`: The main entry point that processes all images in a session
- `_extract_graph_for_image`: Retrieves graph representation for a specific image
- `_generate_concept_id`: Creates a deterministic ID based on the graph structure
- `_save_concept_graph`: Stores the concept graph in the database

### Maximum Common Subgraph Algorithm

The concept creation is powered by graph matching algorithms in `maximum_common_subgraph.py`, which contains two main classes:

1. `MaximumCommonSubgraph`: Finds the largest common structure between two graphs
2. `MaximumCommonMinorGraph`: Extends this functionality to find common minors, allowing for more flexible matching via node contractions

#### MaximumCommonSubgraph

This class implements a product graph-based approach to find the maximum common subgraph:

1. It creates a product graph where nodes represent compatible pairs of nodes from the input graphs
2. Edges are added when both corresponding node pairs have edges in their original graphs
3. Finding a maximum clique in this product graph yields the maximum common subgraph
4. Properties from matched nodes are merged, keeping only matching values

#### MaximumCommonMinorGraph

This extension adds the ability to identify more complex relationships through node contractions:

1. It first finds a maximum common subgraph as a starting point
2. It then identifies potential contractions - cases where unmatched nodes in both graphs connect to the same matched node
3. Contractions are applied to grow the common structure
4. Properties are merged with special handling for different types (labels, numeric values, etc.)

The `find_max_common_minor_with_start_points` method provides optimized matching by first anchoring the match using special "StartPoint" nodes before growing the common structure.

## Workflow

The concept creation process follows these steps:

1. **Initialization**: A session ID is provided, containing multiple processed images
2. **Graph Extraction**: Each image's graph is retrieved from Neo4j
3. **Progressive Concept Building**:
   - The first image's graph becomes the initial concept
   - For each subsequent image:
     - Find the maximum common minor graph between current concept and image
     - Update the concept to this common structure
     - Track all contractions and property changes
4. **Concept Finalization**:
   - Generate a unique ID based on the final graph structure
   - Save the concept to Neo4j
   - Clean up processing data

## Technical Details

### Node Matching

Nodes are matched based on their properties, with special handling for:
- Labels (nodes must share at least one common label)
- StartPoint nodes (used for anchoring the matching process)

### Property Handling

The system uses a `PropertyHandlerManager` to process different property types:
- For labels: takes the intersection of label sets
- For numeric properties: creates range representations
- For other properties: keeps only exact matches

### Graph Contractions

The MCMG approach allows for node contractions, which enable more flexible matching:
1. Nodes A and B in graph G can be contracted if they connect to the same nodes in the matched portion
2. Nodes C and D in graph H can be contracted in a similar way
3. These contractions allow the system to identify structural similarities even when the graphs are not isomorphic

## Visualization

The system supports visualization callbacks at different stages of the process, allowing for:
- Visualization of the initial matching
- Tracking of property changes
- Visualization of contractions
- Display of the final concept

## Mathematical Background

### Maximum Common Subgraph Problem

Given two graphs $G = (V_1, E_1)$ and $H = (V_2, E_2)$, the Maximum Common Subgraph (MCS) problem seeks to find the largest graph that is isomorphic to subgraphs of both $G$ and $H$. Formally, we're looking for:

- A graph $C = (V_C, E_C)$
- Injective functions $f: V_C \rightarrow V_1$ and $g: V_C \rightarrow V_2$
- Such that for all $u,v \in V_C$, $(u,v) \in E_C$ if and only if $(f(u),f(v)) \in E_1$ and $(g(u),g(v)) \in E_2$
- And $|V_C|$ is maximized

The MCS problem is NP-hard, meaning there's no known polynomial-time algorithm to solve it exactly for all inputs.

### Product Graph Construction

The modular product graph $P$ of graphs $G$ and $H$ is defined as:

$$V_P = \{(u,v) \mid u \in V_1, v \in V_2, \text{and nodes } u \text{ and } v \text{ are compatible}\}$$

$$E_P = \{((u_1,v_1),(u_2,v_2)) \mid (u_1 \neq u_2 \text{ and } v_1 \neq v_2) \text{ and } ((u_1,u_2) \in E_1 \iff (v_1,v_2) \in E_2)\}$$

The key insight is that maximum cliques in $P$ correspond to maximum common subgraphs of $G$ and $H$. A clique is a subgraph where every pair of vertices has an edge between them.

### Graph Minor Operations

A graph $H$ is a minor of graph $G$ if $H$ can be obtained from $G$ by a sequence of:
- Vertex deletions
- Edge deletions
- Edge contractions

An edge contraction involves removing an edge $(u,v)$ and merging its endpoints into a single vertex whose edges are the union of the edges incident to $u$ and $v$.

For the Maximum Common Minor Graph problem, we find the largest graph $C$ such that $C$ is a minor of both input graphs $G$ and $H$.

### Energy Minimization

The concept creation uses energy minimization principles from the following energy function:

$$E(C) = -\alpha \cdot |V_C| - \beta \cdot |E_C| + \gamma \cdot \sum(d(p_G, p_C) + d(p_H, p_C))$$

Where:
- $|V_C|$ and $|E_C|$ are the number of vertices and edges in the common graph $C$
- $p_G$, $p_H$, and $p_C$ are corresponding properties in graphs $G$, $H$, and $C$
- $d(\cdot,\cdot)$ is a distance function between properties
- $\alpha$, $\beta$, and $\gamma$ are weighting parameters

The algorithm seeks to minimize this energy, giving preference to larger common structures (negative coefficients for size terms) while penalizing property differences.

### Computational Complexity

The time complexity of various operations:
- Product graph construction: $O(|V_1| \cdot |V_2| + |E_1| \cdot |E_2|)$
- Finding maximum clique (exact): $O(2^n)$ where $n$ is the number of vertices in the product graph
- Finding maximum clique (approximation): $O(n^2)$ using greedy algorithms
- Edge contraction operations: $O(d)$ where $d$ is the degree of the contracted vertices

For practical performance, the implementation uses approximation algorithms for large graphs and exact algorithms for smaller ones.

## Usage

The concept creator is typically used as part of the NaturalAGI pipeline, invoked via the Nuclio handler. The `nuclio_handler.py` file provides the interface for the serverless function.

Example usage in Python code:

```python
from energy_minimization_concept_service import EnergyMinimizationConceptService

# Create the service
service = EnergyMinimizationConceptService(neo4j_uri, neo4j_user, neo4j_password)

# Create a concept from a session
concept_id, concept_graph = service.create_concept_incrementally(session_id)

# The concept_id can be used to retrieve the concept later
# The concept_graph is a NetworkX graph representation of the concept
```

## Performance Considerations

- The maximum common subgraph problem is NP-hard, so approximation algorithms are used for large graphs
- The system uses a graph-based approach that scales well with moderate-sized inputs
- For very large graphs, the system uses approximation algorithms to find maximum cliques
