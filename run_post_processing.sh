#!/bin/bash

SESSION_ID=$1

nuctl invoke post_processing --platform local --method POST --body "{\"session_id\": \"${SESSION_ID}\"}"

nuctl invoke concept_creator --platform local --method POST --body "{\"session_id\": \"${SESSION_ID}\"}"