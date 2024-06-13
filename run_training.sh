# Get folder path from the command line argument
# if [ $# -eq 0 ]; then
#     echo "Please provide the folder path as a command line argument."
#     exit 1
# fi

folder_path="/training_data/line_detector"

echo "Running training with the folder path: $folder_path"

# Invoke line_detector with the training data directory
nuctl invoke line_detector --platform local --method POST \
    --body "{\"input_folder\": \"$folder_path\"}" \
    --content-type "application/json"