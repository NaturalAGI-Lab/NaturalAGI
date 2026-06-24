# Makefile for Nuclio function deployment and execution
include .env
export

# Default goal
.DEFAULT_GOAL := all

# Variables
SHELL := /bin/bash

# Default values for classification
CONCEPT_ID ?= default_concept
IMAGE_ID ?= default_image

# Number of instances for each service (balanced for post-IO-optimization latencies:
# skel ~40ms, contour ~50ms, classification ~243ms)
INSTANCES_SKEL ?= 4
INSTANCES_CONTOUR ?= 4
INSTANCES_CLASSIFICATION ?= 16

# Kafka partition counts per topic (2 × instances for even distribution)
PARTITIONS_CONNECTOR ?= 8
PARTITIONS_SKEL ?= 8
PARTITIONS_CONTOUR ?= 32
PARTITIONS_CLASSIFICATION ?= 1
PARTITIONS_DLQ ?= 1

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

HOST_IP := $(shell ipconfig getifaddr en0)
KAFKA_BROKERS := ${HOST_IP}:29092
NEO4J_PASS=111122223333

LOCAL_STORAGE=./datasets/
NUCLIO_STORAGE=/opt/nuclio/shared_storage/

DLQ_TOPIC = dlq-topic
CONNECTOR_KAFKA_TOPIC = connector-output-topic
SKELETONIZATION_KAFKA_TOPIC = skeletonization-output-topic
CONTOUR_ANALYSIS_KAFKA_TOPIC = contour-analysis-output-topic
CLASSIFICATION_KAFKA_TOPIC = classification-output-topic

TOPICS = $(CONNECTOR_KAFKA_TOPIC) $(DLQ_TOPIC) $(SKELETONIZATION_KAFKA_TOPIC) $(CONTOUR_ANALYSIS_KAFKA_TOPIC) $(CLASSIFICATION_KAFKA_TOPIC)

# Add these variables near the top of the Makefile, after other variable definitions
OPERATION ?= train
CONCEPT_NAME ?= default_concept
SESSION_ID ?= default_session
SUBCLASS ?= default_subclass
PARAMS ?= {}

# Energy minimization option (default: true)
USE_ENERGY_MINIMIZATION ?= true

# Phony targets
.PHONY: all deploy unpack_dataset train classify send_random_image clean docker_clean help start_services create_kafka_topics list_kafka_topics send_to_connector create_neo4j_indexes list_neo4j_indexes

# Kafka-related targets
.PHONY: create_kafka_topics list_kafka_topics

VENV := natural-agi/bin
PYTHON := $(VENV)/python
PIP := $(VENV)/pip3

COMMON_DIR := common
COMMON_VENV := $(COMMON_DIR)/.venv/bin

lib:
	@echo -e "${BLUE}Building common library...${NC}"
	@# Ensure dedicated venv exists
	@test -d $(COMMON_DIR)/.venv || python3 -m venv $(COMMON_DIR)/.venv
	@$(COMMON_VENV)/pip install -q build twine
	@# Auto-increment patch version
	@cd $(COMMON_DIR) && \
		OLD_VER=$$(grep '^version' pyproject.toml | sed 's/.*"\(.*\)"/\1/') && \
		PATCH=$$(echo $$OLD_VER | awk -F. '{print $$3}') && \
		NEW_PATCH=$$((PATCH + 1)) && \
		NEW_VER=$$(echo $$OLD_VER | awk -F. -v p=$$NEW_PATCH '{print $$1"."$$2"."p}') && \
		sed -i '' "s/version = \"$$OLD_VER\"/version = \"$$NEW_VER\"/" pyproject.toml && \
		echo -e "${BLUE}Version: $$OLD_VER → $$NEW_VER${NC}"
	@# Build and upload from common/ directory
	@rm -rf $(COMMON_DIR)/dist
	@$(COMMON_VENV)/python -m build $(COMMON_DIR) --outdir $(COMMON_DIR)/dist || { rm -rf $(COMMON_DIR)/dist; exit 1; }
	@$(COMMON_VENV)/twine upload $(COMMON_DIR)/dist/* --verbose || { rm -rf $(COMMON_DIR)/dist; exit 1; }
	@rm -rf $(COMMON_DIR)/dist
	@echo -e "${GREEN}Library built and uploaded.${NC}"
	@$(PIP) install --upgrade natural-agi-common
	@echo -e "${GREEN}Library installed in project venv.${NC}"

start_services:
	@echo -e "${BLUE}Starting Docker services...${NC}"
	@HOST_IP=${HOST_IP} docker compose up -d
	@echo -e "${GREEN}Docker services started.${NC}"
	@make create_neo4j_indexes

create_kafka_topics:
	@echo -e "${BLUE}Waiting for Kafka to be ready...${NC}"
	@until docker compose exec -T kafka kafka-topics --list --bootstrap-server ${HOST_IP}:29092 &> /dev/null; do \
		echo "Waiting for Kafka to be ready..."; \
		sleep 5; \
	done
	@echo -e "${BLUE}Creating Kafka topics...${NC}"
	@docker compose exec -T kafka kafka-topics --create --bootstrap-server ${HOST_IP}:29092 --if-not-exists --topic "${CONNECTOR_KAFKA_TOPIC}" --partitions $(PARTITIONS_CONNECTOR) --replication-factor 1 || echo "Failed to create topic: ${CONNECTOR_KAFKA_TOPIC}"
	@docker compose exec -T kafka kafka-topics --create --bootstrap-server ${HOST_IP}:29092 --if-not-exists --topic "${SKELETONIZATION_KAFKA_TOPIC}" --partitions $(PARTITIONS_SKEL) --replication-factor 1 || echo "Failed to create topic: ${SKELETONIZATION_KAFKA_TOPIC}"
	@docker compose exec -T kafka kafka-topics --create --bootstrap-server ${HOST_IP}:29092 --if-not-exists --topic "${CONTOUR_ANALYSIS_KAFKA_TOPIC}" --partitions $(PARTITIONS_CONTOUR) --replication-factor 1 || echo "Failed to create topic: ${CONTOUR_ANALYSIS_KAFKA_TOPIC}"
	@docker compose exec -T kafka kafka-topics --create --bootstrap-server ${HOST_IP}:29092 --if-not-exists --topic "${CLASSIFICATION_KAFKA_TOPIC}" --partitions $(PARTITIONS_CLASSIFICATION) --replication-factor 1 || echo "Failed to create topic: ${CLASSIFICATION_KAFKA_TOPIC}"
	@docker compose exec -T kafka kafka-topics --create --bootstrap-server ${HOST_IP}:29092 --if-not-exists --topic "${DLQ_TOPIC}" --partitions $(PARTITIONS_DLQ) --replication-factor 1 || echo "Failed to create topic: ${DLQ_TOPIC}"
	@echo -e "${GREEN}Kafka topics creation attempt completed.${NC}"

recreate_kafka_topics:
	@echo -e "${BLUE}Deleting all Kafka topics...${NC}"
	@for topic in $(TOPICS); do \
		echo "Deleting topic: $$topic"; \
		docker compose exec -T kafka kafka-topics --delete --bootstrap-server ${HOST_IP}:29092 --topic "$$topic" 2>/dev/null || echo "  Topic $$topic does not exist"; \
	done
	@echo -e "${BLUE}Waiting for topics to be fully deleted...${NC}"
	@for topic in $(TOPICS); do \
		while docker compose exec -T kafka kafka-topics --list --bootstrap-server ${HOST_IP}:29092 2>/dev/null | grep -qx "$$topic"; do \
			sleep 1; \
		done; \
	done
	@echo -e "${BLUE}Resetting consumer group offsets...${NC}"
	@for group in skeletonization-group contour-analysis-group classification-group; do \
		echo "  Deleting group $$group..."; \
		docker compose exec -T kafka kafka-consumer-groups --bootstrap-server ${HOST_IP}:29092 --group "$$group" --delete 2>/dev/null || true; \
	done
	@make create_kafka_topics

list_kafka_topics:
	@echo -e "${BLUE}Listing Kafka topics...${NC}"
	@docker compose exec kafka kafka-topics --list --bootstrap-server ${HOST_IP}:29092 || echo -e "${RED}Failed to list Kafka topics${NC}"
	@echo -e "${BLUE}Expected topics:${NC}"
	@for topic in $(TOPICS); do echo "  $$topic"; done

create_neo4j_indexes:
	@echo -e "${BLUE}Waiting for Neo4j to be ready...${NC}"
	@until docker compose exec -T neo4j cypher-shell -u neo4j -p ${NEO4J_PASS} "RETURN 1" &> /dev/null; do \
		echo "Waiting for Neo4j Bolt to be ready..."; \
		sleep 3; \
	done
	@echo -e "${BLUE}Creating Neo4j property indexes...${NC}"
	@docker compose exec -T neo4j cypher-shell -u neo4j -p ${NEO4J_PASS} < scripts/neo4j_indexes.cypher
	@echo -e "${GREEN}Neo4j indexes created.${NC}"

list_neo4j_indexes:
	@echo -e "${BLUE}Listing Neo4j indexes...${NC}"
	@docker compose exec -T neo4j cypher-shell -u neo4j -p ${NEO4J_PASS} \
		"SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state" \
		|| echo -e "${RED}Failed to list Neo4j indexes${NC}"

# Main targets
all: start_services create_kafka_topics deploy train

# Create concept: invoke concept_creator with session_id and concept_name
# Usage: make create_concept <session_id> <concept_name>
create_concept:
	$(eval SESSION_ARGS := $(wordlist 2,3,$(MAKECMDGOALS)))
	$(eval CC_SESSION_ID := $(word 1,$(SESSION_ARGS)))
	$(eval CC_CONCEPT_NAME := $(word 2,$(SESSION_ARGS)))
	@echo -e "${BLUE}Creating concept (session_id=$(CC_SESSION_ID), concept_name=$(CC_CONCEPT_NAME))...${NC}"
	@nuctl invoke concept_creator --platform local --method POST \
		--body '{"session_id": "$(CC_SESSION_ID)", "concept_name": "$(CC_CONCEPT_NAME)", "concept_id": "$(CC_SESSION_ID)"}'
	@echo -e "${GREEN}Concept creation invoked.${NC}"

# Special target to allow passing arguments to other targets
%:
	@:

# Usage: make classify IMAGE_PATH=/path/to/image.jpg [PARAMS='{"param1": "value1", "param2": "value2"}']
# Example: make classify IMAGE_PATH=/path/to/image.jpg PARAMS='{"feature_weight": 0.7, "structural_weight": 0.3}'
classify:
	@echo -e "${BLUE}Classifying image: $(IMAGE_PATH)${NC}"
	@curl -X POST http://localhost:5002 \
		-H "Content-Type: application/json" \
		-d "{\"operation\": \"classify\", \"parameters\": {\"image_path\": \"$(IMAGE_PATH)\"}}" || \
		(echo -e "${RED}Classification failed.${NC}" && exit 1)
	@echo -e "${GREEN}Classification request sent to connector.${NC}"

clean:
	@echo -e "${BLUE}Cleaning up training results...${NC}"
	@rm -rf ./training_results/*
	@echo -e "${GREEN}Cleanup completed.${NC}"

docker_clean:
	@echo -e "${BLUE}Docker cleanup — before:${NC}"
	@docker system df
	@echo ""
	@echo -e "${BLUE}Removing dangling volumes...${NC}"
	@docker volume prune -f
	@echo -e "${BLUE}Removing build cache older than 48h (keeps recent layers for fast rebuilds)...${NC}"
	@docker builder prune -f --filter "until=48h"
	@echo -e "${BLUE}Removing stale Nuclio processor images (not used by any container)...${NC}"
	@for img in $$(docker images --format '{{.Repository}}:{{.Tag}}' | grep 'nuclio/processor-'); do \
		if [ "$$(docker ps -q --filter ancestor=$$img 2>/dev/null | wc -l)" -eq 0 ]; then \
			echo "  Removing unused: $$img"; \
			docker rmi $$img 2>/dev/null || true; \
		fi; \
	done
	@echo ""
	@echo -e "${GREEN}Docker cleanup — after:${NC}"
	@docker system df

unpack_dataset:
	@if [ -d datasets/mnist_all ] && [ "$$(ls -A datasets/mnist_all 2>/dev/null)" ]; then \
		echo -e "${GREEN}Dataset already unpacked (datasets/ exists and is not empty).${NC}"; \
	elif [ -f datasets.zip ]; then \
		echo -e "${BLUE}Unpacking datasets.zip...${NC}"; \
		unzip -o datasets.zip; \
		echo -e "${GREEN}Dataset unpacked.${NC}"; \
	else \
		echo -e "${RED}datasets.zip not found. Please download it first.${NC}"; \
		exit 1; \
	fi

dashboard:
	cd src/training && streamlit run dashboard.py --server.port 8501

formation_viz:
	cd src/concept_creator && ../../natural-agi/bin/python -m streamlit run visualization/formation_viz_app.py --server.port 8502

help:
	@echo "Available targets:"
	@echo "  all                - Deploy functions, create Kafka topics, and run training (default)"
	@echo "  deploy             - Deploy Nuclio functions"
	@echo "  create_kafka_topics - Create Kafka topics"
	@echo "  list_kafka_topics  - List existing Kafka topics"
	@echo "  create_neo4j_indexes - Create property indexes in Neo4j (idempotent)"
	@echo "  list_neo4j_indexes   - List existing Neo4j indexes"
	@echo "  train              - Run training script"
	@echo "  create_concept     - Invoke concept creator (usage: make create_concept <session_id> <concept_name>)"
	@echo "  send_random_image  - Send a random image to the line detector"
	@echo "  classify           - Run classification with given concept_id and image_id"
	@echo "  clean              - Clean up training results"
	@echo "  docker_clean       - Remove dangling volumes, build cache, and stale Nuclio images"
	@echo "  unpack_dataset     - Unpack datasets.zip (skips if already unpacked)"
	@echo "  help               - Show this help message"
	@echo "  send_to_connector  - Send data to connector (OPERATION=train|classify, CONCEPT_NAME=name)"
	@echo ""
	@echo "Configuration options:"
	@echo "  INSTANCES_SKEL      - Number of skeletonization instances (default: 1)"
	@echo "  INSTANCES_CONTOUR   - Number of contour analysis instances (default: 2)"
	@echo "  INSTANCES_CLASSIFICATION - Number of classification instances (default: 5)"
	@echo "  USE_ENERGY_MINIMIZATION - Use energy minimization for concept formation (default: true)"
	@echo ""
	@echo "Example: make deploy INSTANCES_SKEL=1 INSTANCES_CONTOUR=2 INSTANCES_CLASSIFICATION=5"

train_prepared_samples_%:
	$(eval subclass := $(filter-out $@,$(MAKECMDGOALS)))
	@echo -e "${BLUE}Running training script for prepared samples class $* subclass $(subclass)...${NC}"
	@make send_to_connector OPERATION=train CONCEPT_NAME=mnist_$* SUBCLASS=$(subclass) NUCLIO_STORAGE=$(NUCLIO_STORAGE)/train/$*_$(subclass) SESSION_ID=$*_$(subclass)
	@echo -e "${GREEN}Training script completed.${NC}"

train_square:
	@echo -e "${BLUE}Running training script...${NC}"
	@make send_to_connector OPERATION=train CONCEPT_NAME=$(CONCEPT_NAME) NUCLIO_STORAGE=$(NUCLIO_STORAGE)/square
	@echo -e "${GREEN}Training script completed.${NC}"

train_triangle:
	@echo -e "${BLUE}Running training script...${NC}"
	@make send_to_connector OPERATION=train CONCEPT_NAME=$(CONCEPT_NAME) NUCLIO_STORAGE=$(NUCLIO_STORAGE)/triangle
	@echo -e "${GREEN}Training script completed.${NC}"

train_mnist_%:
	@echo -e "${BLUE}Running training script...${NC}"
	@make send_to_connector OPERATION=train CONCEPT_NAME=mnist_$* NUCLIO_STORAGE=$(NUCLIO_STORAGE)/mnist_$*/train SESSION_ID=$*
	@echo -e "${GREEN}Training script completed.${NC}"


send_to_connector:
	@echo -e "${BLUE}Sending data to connector...${NC}"
	@curl -X POST http://localhost:5002 \
		-H "Content-Type: application/json" \
		-d '{"operation": "$(OPERATION)", "parameters": {"dataset_path": "$(NUCLIO_STORAGE)", "concept_name": "$(CONCEPT_NAME)", "session_id": "$(SESSION_ID)", "subclass": "$(SUBCLASS)"}}' || \
		(echo -e "${RED}Failed to send data to connector.${NC}" && exit 1)
	@echo -e "\n${GREEN}Data sent to connector successfully.${NC}"

# Function deployment targets
.PHONY: dep_conn dep_skel dep_contour dep_concept dep_classification dep_all
.PHONY: undep_skel undep_contour undep_classification undep_all

# Common env/trigger fragments
OTEL_ENDPOINT = http://${HOST_IP}:5050

SKEL_ENV = -e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
	-e DLQ_TOPIC="${DLQ_TOPIC}" \
	-e SIMPLIFICATION_EPSILON=5 \
	-e SKELETONIZATION_THRESHOLD=160 \
	-e KAFKA_TOPIC="${SKELETONIZATION_KAFKA_TOPIC}" \
	-e OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_ENDPOINT}"

SKEL_TRIGGERS = --triggers '{"kafka-trigger": {"kind": "kafka-cluster", "attributes": {"initialOffset": "earliest", "topics": ["${CONNECTOR_KAFKA_TOPIC}"], "brokers": ["${KAFKA_BROKERS}"], "consumerGroup": "skeletonization-group"}}}'

CONTOUR_ENV = -e NEO4J_DSN=bolt://${HOST_IP}:7687 \
	-e NEO4J_USER=neo4j \
	-e NEO4J_PASS=${NEO4J_PASS} \
	-e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
	-e DLQ_TOPIC="${DLQ_TOPIC}" \
	-e KAFKA_TOPIC="${CONTOUR_ANALYSIS_KAFKA_TOPIC}" \
	-e OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_ENDPOINT}"

CONTOUR_TRIGGERS = --triggers '{"kafka-trigger": {"kind": "kafka-cluster", "attributes": {"initialOffset": "earliest", "topics": ["${SKELETONIZATION_KAFKA_TOPIC}"], "brokers": ["${KAFKA_BROKERS}"], "consumerGroup": "contour-analysis-group"}}}'

CLASS_ENV = -e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
	-e DLQ_TOPIC="${DLQ_TOPIC}" \
	-e KAFKA_TOPIC="${CLASSIFICATION_KAFKA_TOPIC}" \
	-e NEO4J_DSN=bolt://${HOST_IP}:7687 \
	-e NEO4J_USER=neo4j \
	-e NEO4J_PASS=${NEO4J_PASS} \
	-e GED_TIMEOUT=15 \
	-e OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_ENDPOINT}"

CLASS_TRIGGERS = --triggers '{"kafka-trigger": {"kind": "kafka-cluster", "attributes": {"initialOffset": "earliest", "topics": ["${CONTOUR_ANALYSIS_KAFKA_TOPIC}"], "brokers": ["${KAFKA_BROKERS}"], "consumerGroup": "classification-group"}}}'

SKEL_IMAGE = nuclio/processor-skeletonization:latest
CONTOUR_IMAGE = nuclio/processor-contour-analysis:latest
CLASS_IMAGE = nuclio/processor-classification:latest
NUCLIO_LOGGER_LEVEL ?= warning

dep_conn:
	@echo -e "${BLUE}Deploying connector...${NC}"
	@nuctl deploy --path src/connector \
		--platform local \
		--no-pull \
		--logger-level $(NUCLIO_LOGGER_LEVEL) \
		--volume "${LOCAL_STORAGE}:${NUCLIO_STORAGE}" \
		-e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
		-e DLQ_TOPIC="${DLQ_TOPIC}" \
		-e KAFKA_TOPIC="${CONNECTOR_KAFKA_TOPIC}" \
		-e OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_ENDPOINT}"
	@echo -e "${GREEN}Connector deployed.${NC}"

redep_conn:
	@echo -e "${BLUE}Redeploying connector from cached image (offline, no build)...${NC}"
	@nuctl deploy connector \
		--run-image nuclio/processor-connector:latest \
		-f src/connector/function.yaml \
		--platform local \
		--no-pull \
		--logger-level $(NUCLIO_LOGGER_LEVEL) \
		--volume "${LOCAL_STORAGE}:${NUCLIO_STORAGE}" \
		-e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
		-e DLQ_TOPIC="${DLQ_TOPIC}" \
		-e KAFKA_TOPIC="${CONNECTOR_KAFKA_TOPIC}" \
		-e OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_ENDPOINT}"
	@echo -e "${GREEN}Connector redeployed from cached image.${NC}"

dep_skel:
	@echo -e "${BLUE}Deploying skeletonization ($(INSTANCES_SKEL) instances)...${NC}"
	@echo -e "${BLUE}  Instance 1 (building image)...${NC}"
	@nuctl deploy skeletonization --path src/skeletonization \
		--platform local \
		--logger-level $(NUCLIO_LOGGER_LEVEL) \
		--volume "${LOCAL_STORAGE}:${NUCLIO_STORAGE}" \
		$(SKEL_ENV) $(SKEL_TRIGGERS)
	@if [ $(INSTANCES_SKEL) -gt 1 ]; then \
		for i in $$(seq 2 $(INSTANCES_SKEL)); do \
			echo -e "${BLUE}  Instance $$i (reusing image)...${NC}"; \
			nuctl deploy skeletonization-$$i \
				--run-image $(SKEL_IMAGE) \
				--runtime python:3.12 \
				--handler nuclio_handler:handler \
				--platform local \
				--logger-level $(NUCLIO_LOGGER_LEVEL) \
				--volume "${LOCAL_STORAGE}:${NUCLIO_STORAGE}" \
				$(SKEL_ENV) $(SKEL_TRIGGERS); \
		done; \
	fi
	@echo -e "${GREEN}Skeletonization deployed ($(INSTANCES_SKEL) instances).${NC}"

dep_contour:
	@echo -e "${BLUE}Deploying contour analysis ($(INSTANCES_CONTOUR) instances)...${NC}"
	@echo -e "${BLUE}  Instance 1 (building image)...${NC}"
	@nuctl deploy contour-analysis --path src/contour_analysis \
		--platform local \
		--logger-level $(NUCLIO_LOGGER_LEVEL) \
		$(CONTOUR_ENV) $(CONTOUR_TRIGGERS)
	@if [ $(INSTANCES_CONTOUR) -gt 1 ]; then \
		for i in $$(seq 2 $(INSTANCES_CONTOUR)); do \
			echo -e "${BLUE}  Instance $$i (reusing image)...${NC}"; \
			nuctl deploy contour-analysis-$$i \
				--run-image $(CONTOUR_IMAGE) \
				--runtime python:3.12 \
				--handler nuclio_handler:handler \
				--platform local \
				--logger-level $(NUCLIO_LOGGER_LEVEL) \
				$(CONTOUR_ENV) $(CONTOUR_TRIGGERS); \
		done; \
	fi
	@echo -e "${GREEN}Contour analysis deployed ($(INSTANCES_CONTOUR) instances).${NC}"

dep_concept:
	@echo -e "${BLUE}Deploying concept creator...${NC}"
	@nuctl deploy --path src/concept_creator \
		--platform local \
		--logger-level $(NUCLIO_LOGGER_LEVEL) \
		-e NEO4J_DSN=bolt://${HOST_IP}:7687 \
		-e NEO4J_USER=neo4j \
		-e NEO4J_PASS=${NEO4J_PASS} \
		-e USE_ENERGY_MINIMIZATION=${USE_ENERGY_MINIMIZATION}
	@echo -e "${GREEN}Concept creator deployed.${NC}"

dep_classification:
	@echo -e "${BLUE}Deploying classification ($(INSTANCES_CLASSIFICATION) instances)...${NC}"
	@echo -e "${BLUE}  Instance 1 (building image)...${NC}"
	@nuctl deploy classification --path src/classification \
		--platform local \
		--logger-level $(NUCLIO_LOGGER_LEVEL) \
		$(CLASS_ENV) $(CLASS_TRIGGERS)
	@if [ $(INSTANCES_CLASSIFICATION) -gt 1 ]; then \
		for i in $$(seq 2 $(INSTANCES_CLASSIFICATION)); do \
			echo -e "${BLUE}  Instance $$i (reusing image)...${NC}"; \
			nuctl deploy classification-$$i \
				--run-image $(CLASS_IMAGE) \
				--runtime python:3.12 \
				--handler nuclio_handler:handler \
				--platform local \
				--logger-level $(NUCLIO_LOGGER_LEVEL) \
				$(CLASS_ENV) $(CLASS_TRIGGERS); \
		done; \
	fi
	@echo -e "${GREEN}Classification deployed ($(INSTANCES_CLASSIFICATION) instances).${NC}"

clean_logs:
	@echo -e "${BLUE}Truncating all container log files...${NC}"
	@docker run --rm -v /var/lib/docker:/docker alpine sh -c "find /docker/containers -name '*-json.log' -exec truncate -s 0 {} +"
	@echo -e "${GREEN}Done.${NC}"

# Cleanup targets for multi-instance functions
undep_skel:
	@echo -e "${BLUE}Removing skeletonization instances...${NC}"
	@nuctl delete function skeletonization --platform local 2>/dev/null || true
	@for i in $$(seq 2 10); do \
		nuctl delete function skeletonization-$$i --platform local 2>/dev/null || true; \
	done
	@echo -e "${GREEN}Skeletonization instances removed.${NC}"

undep_contour:
	@echo -e "${BLUE}Removing contour analysis instances...${NC}"
	@nuctl delete function contour-analysis --platform local 2>/dev/null || true
	@for i in $$(seq 2 10); do \
		nuctl delete function contour-analysis-$$i --platform local 2>/dev/null || true; \
	done
	@echo -e "${GREEN}Contour analysis instances removed.${NC}"

undep_classification:
	@echo -e "${BLUE}Removing classification instances...${NC}"
	@nuctl delete function classification --platform local 2>/dev/null || true
	@for i in $$(seq 2 10); do \
		nuctl delete function classification-$$i --platform local 2>/dev/null || true; \
	done
	@echo -e "${GREEN}Classification instances removed.${NC}"

undep_all: undep_skel undep_contour undep_classification
	@nuctl delete function connector --platform local 2>/dev/null || true
	@nuctl delete function concept-creator --platform local 2>/dev/null || true
	@echo -e "${GREEN}All functions removed.${NC}"

dep_all: dep_conn dep_skel dep_contour dep_concept dep_classification
	@echo -e "${BLUE}Pruning dangling Docker images and volumes...${NC}"
	@docker image prune -f
	@docker volume prune -f
	@echo -e "${GREEN}All functions deployed.${NC}"

# Update the existing deploy target to use dep_all
deploy: clean_results dep_all

# Rename clean_training_results to clean_results
clean_results:
	@echo -e "${BLUE}Cleaning previous results...${NC}"
	@rm -rf ./training_results/*
	@echo -e "${GREEN}Results cleaned.${NC}"

# Add a target to deploy with energy minimization
deploy_energy_minimization:
	@echo -e "${BLUE}Deploying with energy minimization concept formation...${NC}"
	@make deploy USE_ENERGY_MINIMIZATION=true
	@echo -e "${GREEN}Deployed with energy minimization concept formation.${NC}"

# Add a target to train with energy minimization
train_energy_minimization:
	@echo -e "${BLUE}Training with energy minimization concept formation...${NC}"
	@make train USE_ENERGY_MINIMIZATION=true
	@echo -e "${GREEN}Training with energy minimization concept formation completed.${NC}"