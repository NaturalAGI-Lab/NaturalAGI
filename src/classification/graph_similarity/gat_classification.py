import torch
from torch_geometric.data import Batch
import networkx as nx
import logging
from .gat import GAT
from .dataset_helper.mnist_data_set_helper import MNISTGraphDataset


def predict_for_image(image_graph: nx.Graph) -> int:
    """
    Predicts digit class (0-9) for a given MNIST image graph using a pre-trained GAT model
    Returns:
        int: The predicted MNIST digit (0-9).
    """

    # For inference we don't need the true label. Use a dummy label (e.g., 0).
    logging.info("Predicting for image")
    dummy_label = 0
    dataset_helper = MNISTGraphDataset()
    data = dataset_helper._convert_to_pyg_data(image_graph, dummy_label)

    model = GAT(
        num_of_layers=3,
        num_heads_per_layer=[8, 8, 1],
        num_features_per_layer=[25, 64, 64, 10],
        add_skip_connection=True,
        bias=True,
        dropout=0.1,
        log_attention_weights=False,
    ).to("cpu")

    model_path = "/opt/nuclio/models/gat_mnist_20250218_230249.pth"
    try:
        # Load the saved file. If the file contains a meta-dictionary with a "state_dict" key,
        # extract it; otherwise, use the loaded object directly.
        loaded_obj = torch.load(model_path, map_location=torch.device("cpu"))
        if isinstance(loaded_obj, dict) and "state_dict" in loaded_obj:
            state_dict = loaded_obj["state_dict"]
        else:
            state_dict = loaded_obj

        # Optionally, if your saved state dict keys contain unwanted prefixes,
        # you can remove them. For example, if they start with "module.", uncomment:
        # new_state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
        # state_dict = new_state_dict

        # Load the state dict with strict=False to allow missing/extra keys.
        missing_keys, unexpected_keys = model.load_state_dict(state_dict, strict=False)
        if missing_keys:
            logging.warning(f"Missing keys when loading state_dict: {missing_keys}")
        if unexpected_keys:
            logging.warning(f"Unexpected keys in state_dict: {unexpected_keys}")
    except FileNotFoundError:
        logging.error(f"Model file not found at {model_path}")
        raise
    except Exception as e:
        logging.error(f"Error loading model: {str(e)}")
        raise

    model.eval()
    with torch.no_grad():
        # Forward pass: extract output logits (and ignore attention weights if returned)
        out = model((data.x, data.edge_index))
        # If the model returns a tuple, take the first element as logits
        if isinstance(out, tuple):
            logits = out[0]
        else:
            logits = out
        
        # If logits has predictions for multiple nodes (2D), average them across the nodes
        if logits.dim() == 2:
            logits = logits.mean(dim=0)
        
        # Now, logits is expected to be a 1D tensor (with num_classes elements).
        # Use argmax without a dim argument.
        pred = logits.argmax().item()
        logging.info(f"Predicted class: {pred}")
        logging.info(f"Logits: {logits}")
        return pred
