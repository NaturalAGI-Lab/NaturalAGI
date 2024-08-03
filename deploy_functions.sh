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

# Directory containing training data images
TRAINING_DATA_DIR="./tests/generated_samples"
LINE_DETECTOR_TRAINING_DATA_DIR="/tests/generated_samples"

# Check if required arguments are provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <line_detector_topic> <dlq_topic> <angle_point_detector_topic>"
    exit 1
fi

# Assign command-line arguments to variables
LINE_DETECTOR_TOPIC="$1"
DLQ_TOPIC="$2"
ANGLE_POINT_DETECTOR_TOPIC="$3"

# Kafka configuration
KAFKA_BROKERS="${HOST_IP}:29092"

nuctl deploy --path src/line_detector \
    --platform local \
    -e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
    -e DLQ_TOPIC="${DLQ_TOPIC}" \
    -e KAFKA_TOPIC="${LINE_DETECTOR_TOPIC}" \
    --volume $TRAINING_DATA_DIR:$LINE_DETECTOR_TRAINING_DATA_DIR &
line_detector_pid=$!

nuctl deploy --path src/angle_point_detector \
    --platform local \
    -e KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BROKERS}" \
    -e DLQ_TOPIC="${DLQ_TOPIC}" \
    -e KAFKA_TOPIC="${ANGLE_POINT_DETECTOR_TOPIC}" \
    --triggers '{"kafka-trigger": {"kind": "kafka-cluster", "attributes": {"initialOffset": "earliest", "topics": ["'$LINE_DETECTOR_TOPIC'"], "brokers": ["'$KAFKA_BROKERS'"], "consumerGroup": "angle-point-detector-group"}}}' \
    -e NEXT_NUCLIO=http://"$HOST_IP":5050 &
ap_detector_pid=$!

nuctl deploy --path src/contour_analysis \
    --platform local \
    --triggers '{"kafka-trigger": {"kind": "kafka-cluster", "attributes": {"initialOffset": "earliest", "topics": ["'$ANGLE_POINT_DETECTOR_TOPIC'"], "brokers": ["'$KAFKA_BROKERS'"], "consumerGroup": "contour-analysis-group"}}}' \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASS=$NEO4J_PASS &
contour_analysis_pid=$!

nuctl deploy --path src/post_processing \
   --platform local \
   -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
   -e NEO4J_USER=neo4j \
   -e NEO4J_PASS=$NEO4J_PASS &
post_processing=$!

nuctl deploy --path src/concept_creator \
   --platform local \
   -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
   -e NEO4J_USER=neo4j \
   -e NEO4J_PASS=$NEO4J_PASS &
concept_creator=$!

nuctl deploy --path src/classification \
   --platform local \
   -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
   -e NEO4J_USER=neo4j \
   -e NEO4J_PASS=$NEO4J_PASS &
classification=$!

# Wait for the deployments to complete
wait $line_detector_pid
wait $ap_detector_pid
wait $contour_analysis_pid
wait $post_processing
wait $concept_creator
wait $classification