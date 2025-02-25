from torch_geometric.data import Data, Dataset
import networkx as nx
import torch
from neo4j import GraphDatabase

class MNISTGraphDataset(Dataset):
    def __init__(self, root: str = '', split: str = 'train', transform=None):
        super().__init__(root, transform)
        self.split = split
        self.data_list = []
        self.label_dict = {str(i): i for i in range(10)}  # MNIST has 10 classes
        self._process()
        
    def _process(self):
        """Process the composed graphs into individual graph samples"""
        #TODO implement
    
    def _convert_to_pyg_data(self, graph: nx.Graph, label: int) -> Data:
        """Convert a NetworkX graph to PyTorch Geometric Data object"""
        # Create node ID mapping (string -> int)
        node_mapping = {node: idx for idx, node in enumerate(graph.nodes())}
        
        # Extract node features
        node_features = self._extract_node_features(graph)
        
        # Create edge index with integer IDs
        edge_list = [(node_mapping[src], node_mapping[dst]) for src, dst in graph.edges()]
        if edge_list:  # Check if graph has edges
            edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long)
        
        # Create label tensor
        label_tensor = torch.tensor(label, dtype=torch.long)
        
        # Create PyG Data object
        data = Data(
            x=node_features,
            edge_index=edge_index,
            y=label_tensor
        )
        
        return data
    
    def _extract_node_features(self, graph: nx.Graph) -> torch.Tensor:
        """Extract node features from the graph"""
        features = []
        
        for node_id, node_data in graph.nodes(data=True):
            print("Node data: ", node_data)
            x = node_data.get('x', 0)
            y = node_data.get('y', 0)
            x1 = node_data.get('x1', 0)
            x2 = node_data.get('x2', 0)
            y1 = node_data.get('y1', 0)
            y2 = node_data.get('y2', 0)
            normalized_x = node_data.get('normalized_x', 0)
            normalized_y = node_data.get('normalized_y', 0)
            relative_distance = node_data.get('relative_distance', 0)
            
            # Compute the quadrant relative to the center of the coordinate space
            if normalized_x >= 0 and normalized_y >= 0:
                quadrant = 1  # Quadrant I: top-right
            elif normalized_x < 0 and normalized_y >= 0:
                quadrant = 2  # Quadrant II: top-left
            elif normalized_x < 0 and normalized_y < 0:
                quadrant = 3  # Quadrant III: bottom-left
            else:  # normalized_x >= 0 and normalized_y < 0:
                quadrant = 4  # Quadrant IV: bottom-right
            
            # Node type features
            is_point = 1.0 if "Point" in node_data.get('labels', []) else 0.0
            is_endpoint = 1.0 if "Endpoint" in node_data.get('labels', []) else 0.0
            is_intersection_point = 1.0 if "IntersectionPoint" in node_data.get('labels', []) else 0.0
            is_corner_point = 1.0 if "CornerPoint" in node_data.get('labels', []) else 0.0
            is_vector = 1.0 if "Vector" in node_data.get('labels', []) else 0.0
            is_vertical_vector = 1.0 if "VerticalVector" in node_data.get('labels', []) else 0.0
            is_horizontal_vector = 1.0 if "HorizontalVector" in node_data.get('labels', []) else 0.0
            angle = node_data.get('angle', 0)
            angle_with_ox = node_data.get('angle_with_ox', 0)
            half_plane = 0 # TODO: add this
            quadrant = node_data.get('quadrant', 0)
            length = node_data.get('length', 0)
            length1 = node_data.get('length1', 0)
            length2 = node_data.get('length2', 0)
            
            corner_points_count = node_data.get('corner_points_count', 0)
            endpoints_count = node_data.get('endpoints_count', 0)
            intersection_points_count = node_data.get('intersection_points_count', 0)
            quadrant_change_count = node_data.get('quadrant_change_count', 0)
            vectors_count = node_data.get('vectors_count', 0)
            
            is_quadrant_change = node_data.get('is_quadrant_change', 0)
            
            monotony_result = node_data.get('monotony', 0)
            is_monotony = 1.0 if monotony_result == 'MONOTONIC' else 0.0
            
            contour_type_result = node_data.get('contour_type', 0)
            is_closed = 1.0 if contour_type_result == 'Closed' else 0.0
            
            num_cycles = node_data.get('cycle_count', 0)
            
            # Structural features
            degree = graph.degree(node_id) / 10.0  # Normalize degree
            
            # Combine features
            node_features = [
                x, y, x1, y1, x2, y2,
                quadrant,
                normalized_x, normalized_y, relative_distance,
                is_point, is_vector,
                is_endpoint, is_intersection_point, is_corner_point,
                is_vertical_vector, is_horizontal_vector,
                degree, angle, angle_with_ox, half_plane, quadrant, length, length1, length2,
                corner_points_count, endpoints_count, intersection_points_count, quadrant_change_count, is_quadrant_change, vectors_count,
                is_monotony, is_closed, num_cycles
            ]
            features.append(node_features)
        
        return torch.tensor(features, dtype=torch.float)
    
    def len(self) -> int:
        return len(self.data_list)
    
    def get(self, idx: int) -> Data:
        return self.data_list[idx]