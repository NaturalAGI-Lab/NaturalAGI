#!/bin/bash

echo "Cleaning up previous results"
rm -rf ./training_results/*

# Down docker
docker-compose down

# Function to get the IP address (assuming macOS, adjust for other OSes)
get_ip() {
    ipconfig getifaddr en0  # Adjust en0 if your network interface is different
}

# Function to get base64 encoded image
get_base64_image() {
    local image_path=$1
    cat $image_path | base64 | tr -d '\n'
}

# Store the IP address
HOST_IP=$(get_ip)
echo "IP address: $HOST_IP"

# Password to the Neo4j
NEO4J_PASS=111122223333

# Directory containing training data images
TRAINING_DATA_DIR="./tests/generated_samples"

# Directory containing training data images for the line detector
LINE_DETECTOR_TRAINING_DATA_DIR="/training_data/line_detector"

# Run docker compose
docker-compose up -d  # -d flag runs containers in the background

nuctl deploy --path src/line_detector \
    --platform local \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASS=$NEO4J_PASS \
    --volume $TRAINING_DATA_DIR:$LINE_DETECTOR_TRAINING_DATA_DIR \
    -e NEXT_NUCLIO=http://"$HOST_IP":5052 &
line_detector_pid=$!

nuctl deploy --path src/angle_point_detector \
    --platform local \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASS=$NEO4J_PASS \
    -e NEXT_NUCLIO=http://"$HOST_IP":5053 &
ap_detector_pid=$!

nuctl deploy --path src/vector_characteristics_definer \
    --platform local \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASS=$NEO4J_PASS \
    -e NEXT_NUCLIO=http://"$HOST_IP":5050 &
vector_characteristics_definer_pid=$!

nuctl deploy --path src/contour_analysis \
    --platform local \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASS=$NEO4J_PASS \
    -e NEXT_NUCLIO=http://"$HOST_IP":5055 &
contour_analysis_pid=$!

nuctl deploy --path src/clean_up \
    --platform local \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASS=$NEO4J_PASS &
    # -e NEXT_NUCLIO=http://"$HOST_IP":5555 &
clean_up=$!

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

# nuctl deploy --path src/qualitative_features_analysis \
#     --platform local \
#     -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
#     -e NEO4J_USER=neo4j \
#     --volume ./training_results/:/stats \
#     -e NEO4J_PASS=$NEO4J_PASS &
# qualitative_features_analysis=$!

# Wait for the deployments to complete
wait $line_detector_pid
wait $ap_detector_pid
wait $vector_characteristics_definer_pid
wait $contour_analysis_pid
wait $clean_up
wait $post_processing
wait $concept_creator
# # wait $qualitative_features_analysis