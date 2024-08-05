# Training

## Model training concept

### Introduction

To train any concept, we need to have a dataset prepared.

After dataset is prepared, we need to say to the system that we want to train a new concept. To do that we need to pass a parameter to the system as the type of the operation.

For training is:
```json5
{
    "operation": "train",
    "parameters" : {
        "concept_name": "triangle",
        "dataset_path": "path/to/dataset"
    }
}
```

For classification is:
```json5
{
    "operation": "classification",
    "parameters" : {
        // TBD        
    }
}
```