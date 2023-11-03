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
IMAGE_PATH="/Users/mlapin/Development/personal/NaturalAGI/tests/test-data/test-image.bmp"

# Get base64 encoded image
BASE64_IMAGE=$(get_base64_image $IMAGE_PATH)

# Run docker compose
docker-compose up -d  # -d flag runs containers in the background

# Deploy image_exporter
nuctl deploy --path src/image_exporter \
    --platform local \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASS=$NEO4J_PASS \
    -e NEXT_NUCLIO=http://"$HOST_IP":8080

# Deploy line_detection function
nuctl deploy --path src/line_detector \
    --platform local \
    -e NEO4J_DSN=bolt://"$HOST_IP":7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASS=$NEO4J_PASS \
    --http-trigger-service-type 8080

# Wait for deployments to complete (adjust sleep time as needed)
sleep 30

# Invoke image_exporter
nuctl invoke image-exporter --platform local --method POST \
    --body "{\"image\": \"$BASE64_IMAGE\"}" \
    --content-type "application/json"
