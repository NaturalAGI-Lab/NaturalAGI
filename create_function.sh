#!/bin/bash

# Check if a function name is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <function-name> <port>"
    exit 1
fi

# Read the function name from the first argument
FUNCTION_NAME="$1"

# Read the port from the second argument
PORT="$2"

# Create a new directory for the function
mkdir "src/$FUNCTION_NAME"
cd "src/$FUNCTION_NAME"

# Create a Python file for the function
cat > nuclio_handler.py <<EOF
"""Generic Nuclio Handler Template"""
import requests
import json
import base64
import traceback
from nuclio_sdk import Event
from pydantic_settings import BaseSettings

HANDLER_NAME = "${FUNCTION_NAME}"

class Settings(BaseSettings):
    """Settings"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str
    next_nuclio: str = ""


def init_context(context):
    """Initializes Nuclio context

    Args:
        context: Nuclio context
    """

    context.logger.debug_with(
        f"Exporter initializing with:\n{Settings().model_dump()}", handler=HANDLER_NAME
    )
    setattr(context.user_data, "next_nuclio", Settings().next_nuclio)

    # Initialize and set context variables
    # Example: setattr(context.user_data, "example_variable", value)


def http_handler(context, event):
    """Handles HTTP requests"""
    try:
        # Process the event body
        # Example: data = event.body

        image_id = event.body
        image_id = image_id.decode('utf-8') if isinstance(image_id, bytes) else image_id

        # Placeholder for main functionality
        # Example: result = perform_some_operation(data)

        context.logger.info_with(f"Processed request successfully", handler=HANDLER_NAME)

        next_functions_str = context.user_data.next_nuclio

        if next_functions_str:
            next_nuclio = next_functions_str.split(";")
            context.logger.debug_with(f"Next functions: {next_nuclio}", handler=HANDLER_NAME)

            if len(next_nuclio) > 0:
                for func in next_nuclio:
                    context.logger.info_with(f"Calling {func}", handler=HANDLER_NAME)
                    requests.post(func, json=str(image_id))
        
        # Responding to the HTTP request
        context.Response(
            body=f"Response message",
            headers={},
            content_type="text/plain",
            status_code=200,
        )

    except Exception as e:
        context.logger.error_with(f"Error: {e}", handler=HANDLER_NAME)
        traceback.print_exc()

        context.Response(
            body=f"Error: {e}",
            headers={},
            content_type="text/plain",
            status_code=500,
        )


def handler(context, event):
    """Nuclio main handler"""

    context.logger.info_with(f"Received request: {event.trigger.kind}", handler=HANDLER_NAME)
    context.logger.info_with(f"{HANDLER_NAME}: Input Headers: {event.headers}", handler=HANDLER_NAME)

    if event.trigger.kind == "http":
        http_handler(context, event)
    else:
        context.logger.error_with("Unknown trigger. Only HTTP supported", handler=HANDLER_NAME)
EOF

# Create a Nuclio function configuration file with the specified port
cat > function.yaml <<EOF
apiVersion: "nuclio.io/v1"
kind: "Function"
metadata:
  name: $FUNCTION_NAME
  labels:
    nuclio.io/project-name: "default"
spec:
  httpTimeout: 1000
  handler: "nuclio_handler:handler"
  runtime: "python:3.9"
  env:
    - name: EXAMPLE_ENV_VAR
      value: "some-value"
  build:
    baseImage: "python:3.9"
    commands:
      - 'apt-get update -y --fix-missing'
      - 'apt-get install -y libgl1-mesa-glx'
      - 'pip install numpy requests pydantic-settings neo4j'
  triggers:
    default-http:
      kind: "http"
      attributes:
        port: $PORT
EOF


# Create the Dockerfile
cat > Dockerfile <<EOF
ARG ARTIFACTS_TOKEN=""
ARG NUCLIO_LABEL=1.12.5
ARG NUCLIO_ARCH=amd64
ARG NUCLIO_BASE_IMAGE=python:3.9
ARG NUCLIO_ONBUILD_IMAGE=quay.io/nuclio/handler-builder-python-onbuild:\${NUCLIO_LABEL}-\${NUCLIO_ARCH}

# Supplies processor uhttpc, used for healthcheck
FROM nuclio/uhttpc:0.0.1-amd64 as uhttpc

# Supplies processor binary, wrapper
FROM \${NUCLIO_ONBUILD_IMAGE} as processor

# From the base image
FROM \${NUCLIO_BASE_IMAGE}

# Copy required objects from the suppliers
COPY --from=processor /home/nuclio/bin/processor /usr/local/bin/processor
COPY --from=processor /home/nuclio/bin/py /opt/nuclio/
COPY --from=uhttpc /home/nuclio/bin/uhttpc /usr/local/bin/uhttpc

RUN apt-get update && apt-get install -y libgl1-mesa-glx

RUN pip install --upgrade pip
RUN pip install msgpack nuclio_sdk pydantic pydantic-settings requests opencv-python neo4j Pillow

# Readiness probe
HEALTHCHECK --interval=1s --timeout=3s CMD /usr/local/bin/uhttpc --url http://127.0.0.1:8082/ready || exit 1

# USER CONTENT
COPY . /opt/nuclio/$FUNCTION_NAME
# END OF USER CONTENT

# Run processor with configuration and platform configuration
CMD [ "processor" ]
EOF