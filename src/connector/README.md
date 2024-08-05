# Connector

This component is designed to be the first component in the pipeline. It is responsible for receiving operation trigger and starting strategy based on the operation.

## Operation

The operation is the operation to be performed. It can be one of the following:

- `train`: Train a model
- `classify`: Classify an image


## Expected input

POST /connector
Body:
```json
// For training
{
    "operation": "train",
    "parameters": {
        "dataset_path": "/path/to/dataset",
        "concept_name": "concept_name"
    }
}

// For classification
{
    "operation": "classify",
    "parameters": {
        "image_path": "/path/to/image"
    }
}
```