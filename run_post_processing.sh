#!/bin/bash

SESSION_ID=$1
CONCEPT_NAME=$2

post_processing_body="{\"session_id\": \"${SESSION_ID}\"}"

nuctl invoke post_processing --platform local --method POST --body "${post_processing_body}"

concept_creator_body="{\"session_id\": \"${SESSION_ID}\", \"concept_name\": \"${CONCEPT_NAME}\", \"concept_id\": \"${SESSION_ID}\"}"

nuctl invoke concept_creator --platform local --method POST --body "${concept_creator_body}"