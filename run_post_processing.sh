#!/bin/bash

SESSION_ID=$1
CONCEPT_NAME=$2

nuctl invoke post_processing --platform local --method POST --body "{\"session_id\": \"${SESSION_ID}\"}"

nuctl invoke concept_creator --platform local --method POST --body "{\"session_id\": \"${SESSION_ID}\", \"concept_name\": \"${CONCEPT_NAME}\"}"