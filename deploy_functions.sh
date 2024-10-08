#!/bin/bash

echo "Cleaning up previous results"
rm -rf ./training_results/*

# Function to get the IP address (assuming macOS, adjust for other OSes)
get_ip() {
    ipconfig getifaddr en0  # Adjust en0 if your network interface is different
}

# Store the IP address
HOST_IP=$(get_ip)
echo "IP address: $HOST_IP"

# Password to the Neo4j
NEO4J_PASS=111122223333

# Kafka configuration
KAFKA_BROKERS="${HOST_IP}:29092"

# Sequential deployment of functions
nuctl deploy --path src/connector \
    --platform local \
    --volume "${LOCAL_STORAGE}":${NUCLIO_STORAGE} \
    -e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
    -e DLQ_TOPIC="${DLQ_TOPIC}" \
    -e KAFKA_TOPIC="${CONNECTOR_KAFKA_TOPIC}"

nuctl deploy --path src/skeletonization \
    --platform local \
    --volume "${LOCAL_STORAGE}":${NUCLIO_STORAGE} \
    -e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
    -e DLQ_TOPIC="${DLQ_TOPIC}" \
    --triggers '{"kafka-trigger": {"kind": "kafka-cluster", "attributes": {"initialOffset": "earliest", "topics": ["'$CONNECTOR_KAFKA_TOPIC'"], "brokers": ["'$KAFKA_BROKERS'"], "consumerGroup": "skeletonization-group"}}}' \
    -e KAFKA_TOPIC="${SKELETONIZATION_KAFKA_TOPIC}"

nuctl deploy --path src/contour_analysis \
    --platform local \
    --triggers '{"kafka-trigger": {"kind": "kafka-cluster", "attributes": {"initialOffset": "earliest", "topics": ["'$SKELETONIZATION_KAFKA_TOPIC'"], "brokers": ["'$KAFKA_BROKERS'"], "consumerGroup": "contour-analysis-group"}}}' \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
    -e DLQ_TOPIC="${DLQ_TOPIC}" \
    -e NEO4J_PASS=$NEO4J_PASS

# nuctl deploy --path src/post_processing \
#    --platform local \
#    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
#    -e NEO4J_USER=neo4j \
#    -e NEO4J_PASS=$NEO4J_PASS

# nuctl deploy --path src/concept_creator \
#    --platform local \
#    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
#    -e NEO4J_USER=neo4j \
#    -e NEO4J_PASS=$NEO4J_PASS

# nuctl deploy --path src/classification \
#    --platform local \
#    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
#    -e NEO4J_USER=neo4j \
#    -e NEO4J_PASS=$NEO4J_PASS

echo "All functions deployed sequentially"