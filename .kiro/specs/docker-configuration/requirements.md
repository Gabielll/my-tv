# Requirements Document

## Introduction

This feature involves creating individual Dockerfiles for each microservice in the system to enable proper containerized deployment on Render. Currently, the system has generic Dockerfiles but needs service-specific Dockerfiles that properly handle dependencies, shared code, and service-specific requirements for each of the 5 microservices: media_manager, metadata_enricher, normalization_worker, scene_analyzer, and scheduler_ai.

## Requirements

### Requirement 1

**User Story:** As a DevOps engineer, I want individual Dockerfiles for each microservice, so that each service can be deployed independently on Render with its specific dependencies and configurations.

#### Acceptance Criteria

1. WHEN deploying to Render THEN each microservice SHALL have its own Dockerfile in its respective directory
2. WHEN building a Docker image THEN the Dockerfile SHALL include the shared code directory for common functionality
3. WHEN a service requires FFMPEG THEN the Dockerfile SHALL install FFMPEG dependencies (normalization_worker and scene_analyzer)
4. WHEN a service does not require FFMPEG THEN the Dockerfile SHALL use the lightweight Python base image (media_manager, metadata_enricher, scheduler_ai)
5. WHEN building any service THEN the Dockerfile SHALL set the correct PYTHONPATH to include the app directory

### Requirement 2

**User Story:** As a developer, I want consistent Docker build patterns across all services, so that maintenance and debugging are simplified.

#### Acceptance Criteria

1. WHEN creating any Dockerfile THEN it SHALL follow the same base structure and pattern
2. WHEN copying files THEN the Dockerfile SHALL copy shared dependencies first, then service-specific requirements, then service code
3. WHEN setting the working directory THEN it SHALL be set to /app for all services
4. WHEN defining the command THEN it SHALL execute the service's app.py file using Python

### Requirement 3

**User Story:** As a system administrator, I want optimized Docker images, so that deployment is fast and resource-efficient.

#### Acceptance Criteria

1. WHEN installing Python packages THEN the Dockerfile SHALL use --no-cache-dir flag to reduce image size
2. WHEN using a base image THEN it SHALL use python:3.9-slim for optimal size and compatibility
3. WHEN copying files THEN the Dockerfile SHALL copy only necessary files to minimize image size
4. WHEN installing system packages THEN it SHALL only install required dependencies (FFMPEG where needed)

### Requirement 4

**User Story:** As a deployment engineer, I want proper service isolation, so that each service can be built and deployed independently without conflicts.

#### Acceptance Criteria

1. WHEN building a service image THEN it SHALL only include that service's specific code and dependencies
2. WHEN a service has specific requirements.txt THEN the Dockerfile SHALL use that service's requirements file
3. WHEN deploying multiple services THEN each SHALL have its own isolated container environment
4. WHEN updating a service THEN only that service's container SHALL need to be rebuilt