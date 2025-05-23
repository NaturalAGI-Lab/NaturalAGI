ARG ARTIFACTS_TOKEN=""
ARG NUCLIO_LABEL=1.12.5
ARG NUCLIO_ARCH=amd64
ARG NUCLIO_BASE_IMAGE=python:3.9
ARG NUCLIO_ONBUILD_IMAGE=quay.io/nuclio/handler-builder-python-onbuild:${NUCLIO_LABEL}-${NUCLIO_ARCH}

# Supplies processor uhttpc, used for healthcheck
FROM nuclio/uhttpc:0.0.1-amd64 as uhttpc

# Supplies processor binary, wrapper
FROM ${NUCLIO_ONBUILD_IMAGE} as processor

# From the base image
FROM ${NUCLIO_BASE_IMAGE}

# Copy required objects from the suppliers
COPY --from=processor /home/nuclio/bin/processor /usr/local/bin/processor
COPY --from=processor /home/nuclio/bin/py /opt/nuclio/
COPY --from=uhttpc /home/nuclio/bin/uhttpc /usr/local/bin/uhttpc

# Install system dependencies for multiprocessing and graphics
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install msgpack nuclio_sdk pydantic pydantic-settings requests opencv-python neo4j Pillow networkx scipy grakel torch torch-geometric
RUN pip install --upgrade natural-agi-common

# Create models directory
RUN mkdir -p /opt/nuclio/models

# Copy model file - make sure to add your model file to the src/classification/models directory
COPY models/*.pth /opt/nuclio/models/

# Set environment variables for better multiprocessing performance
ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV VECLIB_MAXIMUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1

# Readiness probe
HEALTHCHECK --interval=1s --timeout=3s CMD /usr/local/bin/uhttpc --url http://127.0.0.1:8082/ready || exit 1

# USER CONTENT
COPY . /opt/nuclio/$FUNCTION_NAME
# END OF USER CONTENT

# Run processor with configuration and platform configuration
CMD [ "processor" ]
