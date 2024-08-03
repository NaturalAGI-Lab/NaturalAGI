# Makefile for Nuclio function deployment and execution

# Default goal
.DEFAULT_GOAL := all

# Variables
SHELL := /bin/bash
DEPLOY_SCRIPT := deploy_functions.sh
TRAINING_SCRIPT := run_training.sh
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

DLQ_TOPIC = dlq-topic
LINE_DETECTOR_KAFKA_TOPIC = line-detector-output-topic
ANGLE_POINT_DETECTOR_KAFKA_TOPIC = angle-point-detector-output-topic

TOPICS = $(LINE_DETECTOR_KAFKA_TOPIC) $(DLQ_TOPIC) $(ANGLE_POINT_DETECTOR_KAFKA_TOPIC)

# Phony targets
.PHONY: all deploy train post_process classify send_random_image clean help start_services create_kafka_topics list_kafka_topics

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
all: start_services create_kafka_topics deploy train post_process

deploy:
	@echo -e "${BLUE}Deploying functions...${NC}"
	@if sh $(DEPLOY_SCRIPT) $(LINE_DETECTOR_KAFKA_TOPIC) $(DLQ_TOPIC) $(ANGLE_POINT_DETECTOR_KAFKA_TOPIC); then \
		echo -e "${GREEN}Deployment successful.${NC}"; \
	else \
		echo -e "${RED}Deployment failed.${NC}"; \
		exit 1; \
	fi

train:
	@echo -e "${BLUE}Running training...${NC}"
	@if sh $(TRAINING_SCRIPT); then \
		echo -e "${GREEN}Training completed successfully.${NC}"; \
	else \
		echo -e "${RED}Training failed.${NC}"; \
		exit 1; \
	fi

post_process:
	@echo -e "${BLUE}Running post-processing...${NC}"
	@if sh $(POST_PROCESSING_SCRIPT); then \
		echo -e "${GREEN}Post-processing completed successfully.${NC}"; \
	else \
		echo -e "${RED}Post-processing failed.${NC}"; \
		exit 1; \
	fi

send_random_image:
	@echo -e "${BLUE}Selecting a random image and sending to line detector...${NC}"
	@RANDOM_IMAGE=$$(find ./tests/generated_samples -type f | sort -R | head -n 1); \
	if [ -z "$$RANDOM_IMAGE" ]; then \
		echo -e "${RED}No images found in ./tests/generated_samples${NC}"; \
		exit 1; \
	fi; \
	IMAGE_NAME=$$(basename "$$RANDOM_IMAGE"); \
	echo -e "${BLUE}Selected image: $$IMAGE_NAME${NC}"; \
	RESPONSE=$$(nuctl invoke line_detector --platform local --method POST --content-type "application/json" --body '{"image_path": "'"$$RANDOM_IMAGE"'"}'); \
	echo -e "${GREEN}Image sent to line detector. Check the logs for the image_id.${NC}"

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
	@echo "  all                - Deploy functions, create Kafka topics, run training, and post-process (default)"
	@echo "  deploy             - Deploy Nuclio functions"
	@echo "  create_kafka_topics - Create Kafka topics"
	@echo "  list_kafka_topics  - List existing Kafka topics"
	@echo "  train              - Run training script"
	@echo "  post_process       - Run post-processing script"
	@echo "  send_random_image  - Send a random image to the line detector"
	@echo "  classify           - Run classification with given concept_id and image_id"
	@echo "  clean              - Clean up training results"
	@echo "  help               - Show this help message"