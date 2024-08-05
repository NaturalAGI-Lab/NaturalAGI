echo "Running training with the folder path: $folder_path"

# Invoke line_detector with the training data directory
nuctl invoke line_detector --platform local --method POST \
    --body "{\"input_folder\": \"$folder_path\"}" \
    --content-type "application/json"