# Makefile for Nuclio function deployment and execution
include .env
export

# Default goal
.DEFAULT_GOAL := all

# Variables
SHELL := /bin/bash
POST_PROCESSING_SCRIPT := run_post_processing.sh

# Default values for classification
CONCEPT_ID ?= default_concept
IMAGE_ID ?= default_image

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

HOST_IP := $(shell ipconfig getifaddr en0)
KAFKA_BROKERS := ${HOST_IP}:29092
NEO4J_PASS=111122223333

LOCAL_STORAGE=./tests/
NUCLIO_STORAGE=/opt/nuclio/shared_storage

DLQ_TOPIC = dlq-topic
CONNECTOR_KAFKA_TOPIC = connector-output-topic
LINE_DETECTOR_TOPIC = line-detector-output-topic
ANGLE_POINT_DETECTOR_KAFKA_TOPIC = angle-point-detector-output-topic
SKELETONIZATION_KAFKA_TOPIC = skeletonization-output-topic
CONTOUR_ANALYSIS_KAFKA_TOPIC = contour-analysis-output-topic
CLASSIFICATION_KAFKA_TOPIC = classification-output-topic

TOPICS = $(CONNECTOR_KAFKA_TOPIC) $(LINE_DETECTOR_TOPIC) $(ANGLE_POINT_DETECTOR_KAFKA_TOPIC) $(DLQ_TOPIC) $(SKELETONIZATION_KAFKA_TOPIC) $(CONTOUR_ANALYSIS_KAFKA_TOPIC) $(CLASSIFICATION_KAFKA_TOPIC)

# Add these variables near the top of the Makefile, after other variable definitions
OPERATION ?= train
CONCEPT_NAME ?= default_concept
SESSION_ID ?= default_session
SUBCLASS ?= default_subclass

# Phony targets
.PHONY: all deploy train post_process classify send_random_image clean help start_services create_kafka_topics list_kafka_topics send_to_connector

# Kafka-related targets
.PHONY: create_kafka_topics list_kafka_topics

lib:
	@echo -e "${BLUE}Building common library...${NC}"
	@python setup.py sdist bdist_wheel
	@pip install twine
	@twine upload dist/* --verbose
	@rm -rf dist
	@echo -e "${GREEN}Library built and uploaded.${NC}"

start_services:
	@echo -e "${BLUE}Starting Docker services...${NC}"
	@HOST_IP=${HOST_IP} docker compose up -d
	@echo -e "${GREEN}Docker services started.${NC}"

create_kafka_topics:
	@echo -e "${BLUE}Waiting for Kafka to be ready...${NC}"
	@until docker compose exec -T kafka kafka-topics --list --bootstrap-server ${HOST_IP}:29092 &> /dev/null; do \
		echo "Waiting for Kafka to be ready..."; \
		sleep 5; \
	done
	@echo -e "${BLUE}Creating Kafka topics...${NC}"
	@for topic in $(TOPICS); do \
		echo "Creating topic: $$topic"; \
		docker compose exec -T kafka kafka-topics --create --bootstrap-server ${HOST_IP}:29092 --if-not-exists --topic "$$topic" --partitions 1 --replication-factor 1 || echo "Failed to create topic: $$topic"; \
	done
	@echo -e "${GREEN}Kafka topics creation attempt completed.${NC}"

list_kafka_topics:
	@echo -e "${BLUE}Listing Kafka topics...${NC}"
	@docker compose exec kafka kafka-topics --list --bootstrap-server ${HOST_IP}:29092 || echo -e "${RED}Failed to list Kafka
	@echo -e "${BLUE}Expected topics:${NC}"
	@cat $(TOPICS)

# Main targets
all: start_services create_kafka_topics deploy train

# Post-process target: Runs the post-processing script with provided arguments
# Usage: make post_process <arg1> <arg2> ...
# Example: make post_process 2b8ffbca-5dd1-419a-b689-0bb27fbbaa42 mnist-1
post_process:
	@echo -e "${BLUE}Running post-processing...${NC}"
	@if sh $(POST_PROCESSING_SCRIPT) $(filter-out $@,$(MAKECMDGOALS)); then \
		echo -e "${GREEN}Post-processing completed successfully.${NC}"; \
	else \
		echo -e "${RED}Post-processing failed.${NC}"; \
		exit 1; \
	fi

# Special target to allow passing arguments to other targets
%:
	@:

# Usage: make classify IMAGE_PATH=/path/to/image.jpg [PARAMS='{"param1": "value1", "param2": "value2"}']
# Example: make classify IMAGE_PATH=/path/to/image.jpg PARAMS='{"feature_weight": 0.7, "structural_weight": 0.3}'
classify:
	@echo -e "${BLUE}Classifying image: $(IMAGE_PATH)${NC}"
	@curl -X POST http://localhost:5002 \
		-H "Content-Type: application/json" \
		-d "{\"operation\": \"classify\", \"parameters\": $(PARAMS)}" || \
		(echo -e "${RED}Classification failed.${NC}" && exit 1)
	@echo -e "${GREEN}Classification request sent to connector.${NC}"

clean:
	@echo -e "${BLUE}Cleaning up...${NC}"
	@rm -rf ./training_results/*
	@echo -e "${GREEN}Cleanup completed.${NC}"

help:
	@echo "Available targets:"
	@echo "  all                - Deploy functions, create Kafka topics, run training, send data to connector, and post-process (default)"
	@echo "  deploy             - Deploy Nuclio functions"
	@echo "  create_kafka_topics - Create Kafka topics"
	@echo "  list_kafka_topics  - List existing Kafka topics"
	@echo "  train              - Run training script"
	@echo "  post_process       - Run post-processing script"
	@echo "  send_random_image  - Send a random image to the line detector"
	@echo "  classify           - Run classification with given concept_id and image_id"
	@echo "  clean              - Clean up training results"
	@echo "  help               - Show this help message"
	@echo "  send_to_connector  - Send data to connector (OPERATION=train|classify, CONCEPT_NAME=name)"

train_prepared_samples_%:
	@echo -e "${BLUE}Running training script for prepared samples class $* subclass $*...${NC}"
	$(eval subclass := $(filter-out $@,$(MAKECMDGOALS)))
	@make send_to_connector OPERATION=train CONCEPT_NAME=mnist_$* SUBCLASS=$(subclass) NUCLIO_STORAGE=$(NUCLIO_STORAGE)/prepared_samples/$*_$(subclass) SESSION_ID=$*_$(subclass)
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
.PHONY: dep_conn dep_skel dep_contour dep_post dep_concept dep_all

dep_conn:
	@echo -e "${BLUE}Deploying connector...${NC}"
	@nuctl deploy --path src/connector \
		--platform local \
		--volume "${LOCAL_STORAGE}:${NUCLIO_STORAGE}" \
		-e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
		-e DLQ_TOPIC="${DLQ_TOPIC}" \
		-e KAFKA_TOPIC="${CONNECTOR_KAFKA_TOPIC}"
	@echo -e "${GREEN}Connector deployed.${NC}"

dep_skel:
	@echo -e "${BLUE}Deploying skeletonization...${NC}"
	@nuctl deploy --path src/skeletonization \
		--platform local \
		--volume "${LOCAL_STORAGE}:${NUCLIO_STORAGE}" \
		-e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
		-e DLQ_TOPIC="${DLQ_TOPIC}" \
		-e SIMPLIFICATION_EPSILON=10 \
		-e SKELETONIZATION_THRESHOLD=200 \
		--triggers '{"kafka-trigger": {"kind": "kafka-cluster", "attributes": {"initialOffset": "earliest", "topics": ["${CONNECTOR_KAFKA_TOPIC}"], "brokers": ["${KAFKA_BROKERS}"], "consumerGroup": "skeletonization-group"}}}' \
		-e KAFKA_TOPIC="${SKELETONIZATION_KAFKA_TOPIC}"
	@echo -e "${GREEN}Skeletonization deployed.${NC}"

dep_contour:
	@echo -e "${BLUE}Deploying contour analysis...${NC}"
	@nuctl deploy --path src/contour_analysis \
		--platform local \
		--triggers '{"kafka-trigger": {"kind": "kafka-cluster", "attributes": {"initialOffset": "earliest", "topics": ["${SKELETONIZATION_KAFKA_TOPIC}"], "brokers": ["${KAFKA_BROKERS}"], "consumerGroup": "contour-analysis-group"}}}' \
		-e NEO4J_DSN=bolt://${HOST_IP}:7687 \
		-e NEO4J_USER=neo4j \
		-e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
		-e DLQ_TOPIC="${DLQ_TOPIC}" \
		-e KAFKA_TOPIC="${CONTOUR_ANALYSIS_KAFKA_TOPIC}" \
		-e NEO4J_PASS=${NEO4J_PASS}
	@echo -e "${GREEN}Contour analysis deployed.${NC}"

dep_post:
	@echo -e "${BLUE}Deploying post processing...${NC}"
	@nuctl deploy --path src/post_processing \
		--platform local \
		-e NEO4J_DSN=bolt://${HOST_IP}:7687 \
		-e NEO4J_USER=neo4j \
		-e NEO4J_PASS=${NEO4J_PASS}
	@echo -e "${GREEN}Post processing deployed.${NC}"

dep_concept:
	@echo -e "${BLUE}Deploying concept creator...${NC}"
	@nuctl deploy --path src/concept_creator \
		--platform local \
		-e NEO4J_DSN=bolt://${HOST_IP}:7687 \
		-e NEO4J_USER=neo4j \
		-e NEO4J_PASS=${NEO4J_PASS}
	@echo -e "${GREEN}Concept creator deployed.${NC}"

dep_classification:
	@echo -e "${BLUE}Deploying classification...${NC}"
	@export NUCLIO_TEST_MODE=true
	@nuctl deploy --path src/classification \
		--platform local \
		--replicas 3 \
		--platform-config '{"attributes": {"platformConfig": {"kind": "local", "attributes": {"enableReplicasOnLocal": true}}}}' \
		--triggers '{"kafka-trigger": {"kind": "kafka-cluster", "attributes": {"initialOffset": "earliest", "topics": ["${CONTOUR_ANALYSIS_KAFKA_TOPIC}"], "brokers": ["${KAFKA_BROKERS}"], "consumerGroup": "classification-group"}}}' \
		-e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
		-e DLQ_TOPIC="${DLQ_TOPIC}" \
		-e KAFKA_TOPIC="${CLASSIFICATION_KAFKA_TOPIC}" \
		-e NEO4J_DSN=bolt://${HOST_IP}:7687 \
		-e NEO4J_USER=neo4j \
		-e NEO4J_PASS=${NEO4J_PASS} \
		-e GED_TIMEOUT=5 \
		-e FEATURE_WEIGHT=0.6 \
		-e STRUCTURAL_WEIGHT=0.4
	@echo -e "${GREEN}Classification deployed.${NC}"

dep_all: dep_conn dep_skel dep_contour dep_post dep_concept dep_classification
	@echo -e "${GREEN}All functions deployed.${NC}"

# Update the existing deploy target to use dep_all
deploy: clean_results dep_all

# Rename clean_training_results to clean_results
clean_results:
	@echo -e "${BLUE}Cleaning previous results...${NC}"
	@rm -rf ./training_results/*
	@echo -e "${GREEN}Results cleaned.${NC}"