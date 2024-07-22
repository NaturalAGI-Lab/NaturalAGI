.DEFAULT_GOAL := run_with_training

run_with_training:
	@echo "Deploying functions..."
	sh deploy_functions.sh
	@echo "Running tests..."
	sh run_training.sh
	@echo "Done!"

post_processing:
	sh run_post_processing.sh

