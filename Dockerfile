# Base Dockerfile for Python services

# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Set the PYTHONPATH environment variable to allow imports from the root
ENV PYTHONPATH "${PYTHONPATH}:/app"

# Copy the shared library first to leverage Docker layer caching
COPY shared/ /app/shared/

# Declare an argument for the requirements file path
ARG REQUIREMENTS_FILE

# Copy the specific requirements file and install dependencies
COPY ${REQUIREMENTS_FILE} /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service's source code
# This is done after installing dependencies to leverage caching.
# If only the source code changes, the dependency layer will be reused.
ARG SERVICE_DIR
COPY ${SERVICE_DIR}/ /app/

# The CMD to run the application will be specified in docker-compose.yml or render.yaml
# For example: CMD ["python", "media_manager.py"]
