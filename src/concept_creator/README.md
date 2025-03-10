# Concept Creator

The Concept Creator component is responsible for creating abstract concept representations from training samples. It analyzes multiple samples of the same class to identify common structural patterns and forms a concept graph that represents the essential features of that class.

## Algorithms

The Concept Creator supports two different concept formation algorithms:

### 1. Graph Intersection Approach

This is the default algorithm that creates a concept by finding the intersection of all training sample graphs. 

**Key characteristics:**
- Identifies critical points (intersections, corners, endpoints) across samples
- Matches points based on topological, geometric, and feature similarity
- Preserves only the structural elements and properties common to all samples
- Maintains connectivity of the concept graph
- Emphasizes structural similarity and exact feature matches

**When to use:**
- When samples have consistent structural properties
- When the essential concept can be represented as a common subset of all training graphs
- When you need a more precise, deterministic representation

### 2. Energy Minimization Approach

This algorithm uses an incremental approach based on Maximum Common Minor Graph (MCMG) optimization.

**Key characteristics:**
- Processes samples incrementally, refining the concept with each new sample
- Uses graph minor operations (edge contractions) to find structural matches
- Optimizes for maximum common structure through energy minimization
- Can handle more variations across samples

**When to use:**
- When samples have more structural variations
- When you need a more flexible matching approach
- When the concept needs to generalize across diverse examples

## API Usage

The Concept Creator exposes a simple API endpoint that accepts POST requests:

```json
{
  "session_id": "training_session_123",
  "concept_id": "optional_concept_id",
  "algorithm": "graph_intersection"  // or "energy_minimization"
}
```

### Parameters:

- `session_id` (required): The ID of the session containing training samples
- `concept_id` (optional): Custom ID for the concept, auto-generated if not provided
- `algorithm` (optional): The algorithm to use for concept formation:
  - `"graph_intersection"` (default): The intersection-based approach
  - `"energy_minimization"`: The incremental MCMG approach

### Response:

```json
{
  "concept_id": "concept_abc123",
  "session_id": "training_session_123",
  "algorithm": "graph_intersection",
  "nodes_count": 42,
  "edges_count": 65,
  "execution_time_seconds": 3.25
}
```

## Implementation Details

### Graph Intersection Implementation

The graph intersection approach is implemented in `concept_formation.py` and follows these steps:

1. **Critical Points Identification**: Extract critical points (intersection points, corner points, endpoints, start points) from each graph
2. **Point Matching**: Calculate similarity between points based on their topological, geometric, and segment properties
3. **Intersection Graph Creation**: Create a new graph containing only matching elements from all samples
4. **Property Preservation**: Keep only properties that are common across matched elements
5. **Concept Refinement**: Remove isolated nodes and ensure the resulting graph is connected

### Energy Minimization Implementation

The energy minimization approach is implemented in `energy_minimization_concept_service.py` and uses:

1. **Maximum Common Minor Graph**: An extended version of the maximum common subgraph algorithm
2. **Incremental Refinement**: Process samples one-by-one, refining the concept with each new sample
3. **Graph Minor Operations**: Edge contractions to handle structural variations
4. **Optimization**: Energy minimization to find the best matches

## Integration

The Concept Creator is deployed as a Nuclio serverless function that:

1. Receives HTTP requests for concept creation
2. Processes training samples stored in Neo4j
3. Creates the concept using the specified algorithm
4. Stores the resulting concept graph back to Neo4j
5. Optionally triggers downstream functions for further processing

## Usage Examples

### Example: Using the Graph Intersection Algorithm

```bash
curl -X POST http://nuclio-concept-creator:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "digit_5_training",
    "algorithm": "graph_intersection"
  }'
```

### Example: Using the Energy Minimization Algorithm

```bash
curl -X POST http://nuclio-concept-creator:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "digit_5_training",
    "algorithm": "energy_minimization"
  }'
```

## Testing and Development

For testing and development, you can use the `test_concept_formation.py` script:

```bash
python test_concept_formation.py graph_sample1.json graph_sample2.json
```

This will:
1. Load the provided JSON graph files
2. Create a concept using the graph intersection approach
3. Visualize both the input graphs and the resulting concept graph 