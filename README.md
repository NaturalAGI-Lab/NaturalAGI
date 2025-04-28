# NaturalAGI

NaturalAGI is a research project focused on developing a natural approach to Artificial General Intelligence through image processing, pattern recognition, and concept formation. The project implements a pipeline for processing visual data, extracting structural features, and forming abstract concepts through defined reduction rules. **The core goal is to build a classification algorithm that learns from training data without using backpropagation or traditional neural network approaches.**

## Project Overview

NaturalAGI implements a cognitive architecture that processes visual input through several stages:

1. **Pre-detection** - Initial processing of images to extract structural features
2. **Contour Analysis** - Analysis of structural elements and their relationships
3. **Concept Formation** - Reduction to form abstract concepts
4. **Classification** - Matching new inputs against formed concepts

Unlike traditional machine learning approaches that rely on backpropagation and gradient descent, NaturalAGI uses structural analysis and statistical reduction to form concepts. This approach is inspired by natural cognitive processes, where learning occurs through exposure to examples and statistical pattern recognition rather than explicit error correction.

The project is implemented as a set of microservices orchestrated through a Makefile-based workflow. Each component runs as a Nuclio serverless function, communicating through Kafka topics and storing structural representations in a Neo4j graph database.

![Architecture](AGI%20Arch.jpg)

## Key Components

### 1. Skeletonization

The skeletonization component uses the Growing Neural Gas (GNG) algorithm to create skeletal representations of images. This process:
- Converts images to binary skeletons
- Applies GNG to create a neural network representation
- Simplifies the network by identifying endpoints and intersections
- Converts the result to a NetworkX graph

### 2. Contour Analysis

The contour analysis module analyzes the structural elements of images, focusing on:
- Lines and their intersections
- Geometric and topological properties
- Vector magnitude and direction
- Critical points and angle points

The contour analysis process involves:
- Extracting points from the skeletonized image
- Identifying special points (endpoints, intersections)
- Creating vectors between connected points
- Calculating geometric properties (length, direction)
- Identifying critical features (angle points, quadrant changes)

#### Graph Representation

The structural elements are represented as a graph where:
- **Nodes** represent different elements in the image:
  - **Point nodes** with specific types:
    - Regular points
    - Endpoints
    - Intersections
    - Angle points
  - **Vector nodes** with properties:
    - Length
    - Start/end coordinates (x1, y1, x2, y2)
- **Relationships** connect the elements:
  - Points are connected to vectors via `:CONNECTED_TO` relationships
  - This creates a bipartite graph structure where points connect to vectors and vectors connect to points

#### Graph Persistence

The graph representation is persisted in a Neo4j database using the `GraphPersistenceService`:
- Points are stored as nodes with labels indicating their type (`:Point`, `:EndPoint`, `:IntersectionPoint`, etc.)
- Vectors are stored as nodes (not edges) with properties for coordinates and length, etc.
- Relationships connect points to vectors (`:CONNECTED_TO`)
- All elements are tagged with `image_id` and `session_id` for tracking

This graph-based representation enables:
- Topological analysis of image structures
- Feature extraction based on graph properties
- Comparison between different images using graph similarity algorithms
- Statistical reduction for concept formation

### 3. Classification

The classification function compares input images with formed concepts using:
- Structural similarity with Maximum Common Minor Graph (MCMG) as for now

The classification process:
1. Creates a graph representation of the input image
2. Calculates similarity scores
3. Returns the most similar concept

Unlike traditional neural network classifiers, this approach doesn't require backpropagation or gradient descent. Instead, it relies on structural similarity and feature matching between the input and learned concepts.

### 4. Concept Creation

The concept creation process extracts stable structures and features across multiple images of the same type, forming abstract representations.

The process involves:
1. Running training script that create multiple graphs for each sample in the training set for that particular class
2. Running post processing script that extract the most common graph across all the graphs for that class

This statistical approach to concept formation is fundamentally different from supervised learning with backpropagation. Instead of adjusting weights to minimize error, the system identifies stable patterns across multiple examples through statistical analysis.

## System Architecture

The system is deployed as a set of microservices using:
- **Nuclio Functions** - Serverless functions for image processing
- **Kafka** - Message broker for communication between components
- **Neo4j** - Graph database for storing structural representations
- **Docker** - Containerization for deployment

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Poetry (for dependency management)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/NaturalAGI.git
   cd NaturalAGI
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

### Running the System

The system can be run by executing the following command:

```bash
make
```

For help with available commands:
```bash
make help
```

## Project Structure

```
NaturalAGI/
├── src/                      # Source code
│   ├── skeletonization/      # Image skeletonization using GNG
│   ├── contour_analysis/     # Analysis of structural elements
│   │   ├── service/          # Services for analysis and persistence
│   │   ├── logic/            # Analysis algorithms
│   │   └── model/            # Data models for structural elements
│   ├── classification/       # Concept matching
│   ├── concept_creator/      # Concept formation
│   ├── connector/            # Communication between components
│   ├── post_processing/      # Statistical reduction
│   ├── training/             # Training models
│   └── samples_generator/    # Training data generation
├── common/                   # Shared utilities
├── docs/                     # Documentation
│   ├── README.md             # Detailed project description
│   ├── FEATURES.md           # Feature extraction documentation
│   ├── SIMULATION.md         # Simulation instructions
│   └── TRAINING.md           # Training process documentation
├── scripts/                  # Utility scripts
├── tests/                    # Test suite
│   └── generated_samples/    # Storage for test samples
├── training_data/            # Training datasets
├── Makefile                  # Build automation for deployment and execution
├── docker-compose.yaml       # Docker services configuration
├── pyproject.toml            # Poetry dependency management
└── .env                      # Environment variables
```

## Documentation

- [Natural AGI Description](/docs/README.md) - Detailed project description
- [Feature Extraction](/docs/FEATURES.md) - Documentation on feature extraction
- [Simulation](/docs/SIMULATION.md) - Instructions for running the simulation
- [Training Process](/docs/TRAINING.md) - Documentation on the training process

## Technologies Used

- **Python** - Primary programming language
- **OpenCV** - Image processing
- **scikit-image** - Image analysis
- **NetworkX** - Graph representation and analysis
- **Neo4j** - Graph database for storing structural representations
- **Nuclio** - Serverless functions for processing
- **Kafka** - Message broker for component communication
- **Docker** - Containerization for deployment
