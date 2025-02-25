from pathlib import Path
from typing import Tuple, Dict
import torch
from torch_geometric.data import Batch, Data
import networkx as nx
import logging
from .gat import GAT
from .dataset_helper.mnist_data_set_helper import MNISTGraphDataset
import torch.nn.functional as F


class GATClassification:
    def __init__(self, model_path: str):
        self.device = torch.device('cpu')
        # Load the full model configuration
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=True)

        # Initialize model with saved configuration
        self.model = GAT(
            num_of_layers=checkpoint["num_of_layers"],
            num_heads_per_layer=checkpoint["num_heads_per_layer"],
            num_features_per_layer=checkpoint["num_features_per_layer"],
            add_skip_connection=checkpoint["add_skip_connection"],
            bias=checkpoint["bias"],
            dropout=checkpoint["dropout"],
        ).to(self.device)

        # Load the actual model state
        self.model.load_state_dict(checkpoint["state_dict"], strict=True)
        self.model.eval()

    def predict_for_image(self, image_graph: nx.Graph) -> int:
        """
        Predicts digit class (0-9) for a given MNIST image graph using a pre-trained GAT model
        Returns:
            int: The predicted MNIST digit (0-9).
        """

        logging.info("Predicting for image")
        node_features, edge_index = self._get_node_features_and_edge_index(image_graph)

        with torch.no_grad():  # Add no_grad context for inference
            # Pack features and edge_index into a tuple for the forward pass
            output, _ = self.model((node_features, edge_index))

            # Apply softmax to get probabilities
            probabilities = F.softmax(output, dim=1)

            # Get the predicted class (should be 0-9)
            predicted_class = probabilities.mean(dim=0).argmax().item()

            logging.info(f"Probabilities: {probabilities.mean(dim=0)}")

            return predicted_class

    def _get_node_features_and_edge_index(
        self, graph: nx.Graph
    ) -> Data:
        dataset_helper = MNISTGraphDataset()
        data = dataset_helper._convert_to_pyg_data(graph, 0)
        data.to(device=self.device)
        return data
