#!/bin/bash

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

# Path to the image
IMAGE_PATH="/Users/mlapin/Development/personal/NaturalAGI/tests/test-data/triangle_comp.png"

# Get base64 encoded image
BASE64_IMAGE=$(get_base64_image $IMAGE_PATH)

# Run docker compose
docker-compose up -d  # -d flag runs containers in the background

# Deploy Nuclio functions in parallel
nuctl deploy --path src/image_exporter \
    --platform local \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASS=$NEO4J_PASS \
    -e NEXT_NUCLIO=http://"$HOST_IP":8080 &
image_exporter_pid=$!

nuctl deploy --path src/line_detector \
    --platform local \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASS=$NEO4J_PASS \
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
    -e NEO4J_PASS=$NEO4J_PASS &
contour_analysis_pid=$!

# Wait for the deployments to complete
wait $image_exporter_pid
wait $line_detector_pid
wait $ap_detector_pid
wait $vector_characteristics_definer_pid
wait $contour_analysis_pid

# Invoke image_exporter
nuctl invoke image-exporter --platform local --method POST \
    --body "{\"image\": \"$BASE64_IMAGE\"}" \
    --content-type "application/json"
