# Simulation software

## How to run the simulation

Currently, the simulation is running in a local environment and has 3 stages:
1. Deployment of the nuclio functions and the graph database
2. Running the training script that is sending the data to the pre-detectors
3. Running the statistical reduction on the generated training data

### Deployment of the nuclio functions and the graph database

```bash
sh deploy_functions.sh
```

### Running the training script

```bash
sh run_training.sh
```

### Running the statistical reduction

```bash
sh run_post_processing.sh
```
