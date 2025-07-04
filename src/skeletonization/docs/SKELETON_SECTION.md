# Graph-Based Image Skeletonization Through Growing Neural Gas Networks

## 2. Skeletonization Function

### 2.1 Introduction and Problem Statement

The skeletonization function transforms raster images into structured graph representations suitable for pattern analysis and concept recognition. This process addresses the fundamental challenge of converting pixel-based image data into mathematical graph structures while preserving essential topological and geometric characteristics.

The system combines classical morphological skeletonization with neural network-based topology learning to handle diverse image types while maintaining computational efficiency. The approach addresses limitations of traditional skeletonization algorithms that often produce fragmented or overly complex skeletal structures.

### 2.2 Theoretical Foundation

#### 2.2.1 Morphological Skeletonization

The morphological preprocessing employs binary thresholding with adaptive threshold selection:

```math
I_{\text{binary}}(x,y) = \begin{cases}
1, & \text{if } I(x,y) > \theta \\
0, & \text{otherwise}
\end{cases}
```

The system applies morphological closing operations and small object removal to eliminate noise while preserving structural elements. Skeletonization employs the medial axis transform implemented in scikit-image [1], producing thinned representations that preserve topology while reducing structural elements to single-pixel width.

#### 2.2.2 Growing Neural Gas Algorithm

The Growing Neural Gas (GNG) algorithm [2] provides the theoretical foundation for learning topological relationships from skeletal point data. GNG dynamically constructs network topologies by incrementally adding nodes and adjusting connections based on input data distribution.

Nodes adapt their positions through local learning rules:
<!-- 
```math
\Delta w_i = \epsilon_b \cdot (x - w_i) \text{ for winner node}
```

```math
\Delta w_j = \epsilon_n \cdot (x - w_j) \text{ for neighbor nodes}
``` -->

where ε_b and ε_n are learning rates for the best matching unit and its neighbors, respectively.

#### 2.2.3 Network Simplification

The network simplification employs the Ramer-Douglas-Peucker (RDP) algorithm [3] to reduce complexity while preserving essential geometric characteristics. The algorithm uses perpendicular distance criterion for point elimination.
<!-- 
```math
d = \frac{|(y_2-y_1)x_0 - (x_2-x_1)y_0 + x_2y_1 - y_2x_1|}{\sqrt{(y_2-y_1)^2 + (x_2-x_1)^2}}
``` -->

### 2.3 Algorithm Architecture

The skeletonization pipeline consists of eight sequential stages:

1. **Binary Preprocessing**: Adaptive thresholding with morphological operations
2. **Morphological Skeletonization**: Medial axis transformation
3. **Branch Pruning**: Spurious branch elimination using skan library [4]
4. **Point Extraction**: Conversion to point clouds for neural processing
5. **Neural Network Fitting**: GNG topology learning
6. **Network Simplification**: RDP-based complexity reduction
7. **Graph Construction**: NetworkX graph generation with node/edge attributes
8. **Normalization**: Coordinate normalization for scale invariance

The system employs adaptive threshold selection to balance noise reduction with structural completeness. The algorithm begins with high threshold values to minimize noise and extract only the most prominent structural features, ensuring clean skeletal representations. However, high thresholds may result in disconnected components when essential connecting structures fall below the threshold.

To address this trade-off, the system iteratively reduces the threshold value when disconnected graphs are detected, progressively incorporating previously "lost" structural details until graph connectivity is achieved. This adaptive approach ensures that the final representation captures sufficient structural information to maintain topological integrity while preserving the noise reduction benefits of initial high-threshold processing.

### 2.4 Performance Characteristics

The system demonstrates robust performance across diverse image types through:

- **Adaptive Processing**: Automatic parameter adjustment based on image characteristics
- **Error Recovery**: Comprehensive error handling with retry mechanisms
- **Scalability**: Microservice architecture supporting parallel processing
- **Quality Assurance**: Connectivity validation and geometric consistency checks

### 2.5 Integration and Output

The function integrates with the NaturalAGI pipeline through Kafka-based microservice architecture, providing asynchronous processing and fault tolerance. Output graphs include comprehensive node and edge attributes in NetworkX JSON format, supporting both geometric and topological analysis requirements.

### 2.6 Conclusion

The skeletonization function provides efficient image-to-graph transformation through the integration of morphological processing with neural network topology learning. The adaptive processing pipeline ensures consistent output quality across diverse image types while maintaining computational efficiency suitable for real-time applications.

---

## References

[1] van der Walt, S., Schönberger, J. L., Nunez-Iglesias, J., et al. (2014). scikit-image: image processing in Python. PeerJ, 2, e453.

[2] Fritzke, B. (1995). A growing neural gas network learns topologies. In Advances in neural information processing systems (pp. 625-632).

[3] Ramer, U. (1972). An iterative procedure for the polygonal approximation of plane curves. Computer graphics and image processing, 1(3), 244-256.

[4] Nunez-Iglesias, J., et al. (2018). skan: skeleton analysis in Python. Journal of Open Source Software, 3(24), 842.
