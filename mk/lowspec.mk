# Low-spec profile: 8 GB RAM laptops, 2-4 CPU threads, little free disk, Windows via WSL2.
# Enable with `make PROFILE=lowspec <target>` or once and for all with
#   echo "PROFILE = lowspec" > local.mk
# Everything here uses ?= so any value can still be overridden on the command line.

# One instance of every function: each container costs ~300-600 MB of RAM.
INSTANCES_SKEL ?= 1
INSTANCES_CONTOUR ?= 1
INSTANCES_CLASSIFICATION ?= 1

# One partition per topic is enough for one consumer each.
PARTITIONS_CONNECTOR ?= 1
PARTITIONS_SKEL ?= 1
PARTITIONS_CONTOUR ?= 1
PARTITIONS_CLASSIFICATION ?= 1
PARTITIONS_DLQ ?= 1

# Build images one at a time: parallel pip installs freeze an 8 GB machine.
DEPLOY_PARALLELISM ?= 1

# Neo4j + Kafka with small heaps; no Nuclio dashboard, Postgres or MLflow server.
COMPOSE_FILES ?= -f docker-compose.yaml -f docker-compose.lowspec.yaml

# python:3.12-slim instead of python:3.12 saves ~800 MB of disk per build.
BASE_PYTHON_IMAGE ?= python:3.12-slim

# No MLflow server in this profile: functions skip OTLP tracing, and the training /
# evaluation scripts log runs to a local folder instead of http://localhost:5050.
EXTRA_FN_ENV ?= -e OTEL_TRACING_ENABLED=false
MLFLOW_TRACKING_URI ?= file:./mlruns
