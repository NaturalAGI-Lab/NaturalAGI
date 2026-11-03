#!/bin/zsh
# Host LAN IP changed -> Kafka advertises a dead address and every function is pinned to it.
# Recreate Kafka on the current IP, recreate topics, redeploy all functions from the working tree.
# Usage: recover_pipeline.sh [classification_instances=8]
cd "$(dirname "$0")/../.."
IP=$(ipconfig getifaddr en0); N=${1:-8}
echo "$(date +%H:%M:%S) host ip $IP — recreating kafka"
docker rm -f naturalagi-kafka-1 >/dev/null 2>&1
HOST_IP=$IP docker compose up -d kafka 2>&1 | tail -2
make create_kafka_topics 2>&1 | tail -3
echo "$(date +%H:%M:%S) redeploying all functions (classification x$N)"
make dep_all LOCAL_STORAGE=./tests/ INSTANCES_CLASSIFICATION=$N > /tmp/naturalagi_redeploy.log 2>&1
sleep 25
echo "$(date +%H:%M:%S) healthy nuclio functions: $(docker ps --format '{{.Names}} {{.Status}}' | grep nuclio-nuclio | grep -c healthy)"
docker inspect nuclio-nuclio-skeletonization --format '{{range .Config.Env}}{{println .}}{{end}}' | grep KAFKA_BOOTSTRAP
