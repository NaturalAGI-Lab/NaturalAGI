# Makefile for Nuclio function deployment and execution
include .env
export

# Default goal
.DEFAULT_GOAL := all

# Variables
SHELL := /bin/bash
DEPLOY_SCRIPT := deploy_functions.sh
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

LOCAL_STORAGE=./tests/generated_samples
NUCLIO_STORAGE=/opt/nuclio/shared_storage

DLQ_TOPIC = dlq-topic
CONNECTOR_KAFKA_TOPIC = connector-output-topic
LINE_DETECTOR_TOPIC = line-detector-output-topic
ANGLE_POINT_DETECTOR_KAFKA_TOPIC = angle-point-detector-output-topic

TOPICS = $(CONNECTOR_KAFKA_TOPIC) $(LINE_DETECTOR_TOPIC) $(ANGLE_POINT_DETECTOR_KAFKA_TOPIC) $(DLQ_TOPIC)

# Add these variables near the top of the Makefile, after other variable definitions
OPERATION ?= train
CONCEPT_NAME ?= default_concept
SESSION_ID ?= default_session

# Phony targets
.PHONY: all deploy train post_process classify send_random_image clean help start_services create_kafka_topics list_kafka_topics send_to_connector

# Kafka-related targets
.PHONY: create_kafka_topics list_kafka_topics

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
all: start_services create_kafka_topics deploy train send_to_connector post_process

deploy:
	@echo -e "${BLUE}Deploying functions...${NC}"
	@if sh $(DEPLOY_SCRIPT) $(LINE_DETECTOR_TOPIC) $(DLQ_TOPIC) $(ANGLE_POINT_DETECTOR_KAFKA_TOPIC); then \
		echo -e "${GREEN}Deployment successful.${NC}"; \
	else \
		echo -e "${RED}Deployment failed.${NC}"; \
		exit 1; \
	fi

post_process:
	@echo -e "${BLUE}Running post-processing...${NC}"
	@if sh $(POST_PROCESSING_SCRIPT) $(SESSION_ID); then \
		echo -e "${GREEN}Post-processing completed successfully.${NC}"; \
	else \
		echo -e "${RED}Post-processing failed.${NC}"; \
		exit 1; \
	fi

classify:
	@echo -e "${BLUE}Classifying with concept_id: $(CONCEPT_ID) and image_id: $(IMAGE_ID)${NC}"
	@nuctl invoke classification --platform local --method POST \
		--content-type "application/json" \
		-b '{"concept_id": "$(CONCEPT_ID)", "image_id": "$(IMAGE_ID)"}' || \
		(echo -e "${RED}Classification failed.${NC}" && exit 1); \
	echo -e "${GREEN}Classification completed.${NC}"

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

train:
	@echo -e "${BLUE}Running training script...${NC}"
	@make send_to_connector OPERATION=train CONCEPT_NAME=$(CONCEPT_NAME)
	@echo -e "${GREEN}Training script completed.${NC}"

train_square:
	@echo -e "${BLUE}Running training script...${NC}"
	@make send_to_connector OPERATION=train CONCEPT_NAME=$(CONCEPT_NAME) NUCLIO_STORAGE=$(NUCLIO_STORAGE)/square
	@echo -e "${GREEN}Training script completed.${NC}"

train_triangle:
	@echo -e "${BLUE}Running training script...${NC}"
	@make send_to_connector OPERATION=train CONCEPT_NAME=$(CONCEPT_NAME) NUCLIO_STORAGE=$(NUCLIO_STORAGE)/triangle
	@echo -e "${GREEN}Training script completed.${NC}"


send_to_connector:
	@echo -e "${BLUE}Sending data to connector...${NC}"
	@curl -X POST http://localhost:5002 \
		-H "Content-Type: application/json" \
		-d '{"operation": "$(OPERATION)", "parameters": {"dataset_path": "$(NUCLIO_STORAGE)", "concept_name": "$(CONCEPT_NAME)"}}' || \
		(echo -e "${RED}Failed to send data to connector.${NC}" && exit 1)
	@echo -e "\n${GREEN}Data sent to connector successfully.${NC}"