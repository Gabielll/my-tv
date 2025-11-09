# Design Document

## Overview

This design creates individual Dockerfiles for each of the 5 microservices (media_manager, metadata_enricher, normalization_worker, scene_analyzer, scheduler_ai) to enable independent deployment on Render. The design follows a consistent pattern while accommodating service-specific requirements, particularly FFMPEG dependencies for video processing services.

## Architecture

### Service Categories

**Standard Services (Python-only):**
- media_manager
- metadata_enricher  
- scheduler_ai

**FFMPEG-enabled Services (Video processing):**
- normalization_worker
- scene_analyzer

### Dockerfile Structure Pattern

All Dockerfiles follow this consistent structure:
1. Base image selection (python:3.9-slim)
2. FFMPEG installation (if required)
3. Working directory setup (/app)
4. Environment variable configuration (PYTHONPATH)
5. Shared code copying
6. Requirements installation
7. Service code copying
8. Command definition

## Components and Interfaces

### Base Image Strategy

**Standard Base Image:**
```dockerfile
FROM python:3.9-slim
```

**FFMPEG-enabled Base Image:**
```dockerfile
FROM python:3.9-slim
RUN apt-get update && apt-get install -y ffmpeg
```

### Directory Structure

Each service Dockerfile will be located at:
- `media_manager/Dockerfile`
- `metadata_enricher/Dockerfile`
- `normalization_worker/Dockerfile`
- `scene_analyzer/Dockerfile`
- `scheduler_ai/Dockerfile`

### Shared Dependencies

All services depend on the `shared/` directory which contains:
- Database utilities (db.py)
- Configuration management (config.py)
- Health check utilities (health_check.py)
- Logging configuration (logging_config.py)
- Storage management (storage_manager.py)
- Worker app template (worker_app_template.py)

### Service-Specific Requirements

Each service has its own `requirements.txt` file:
- **media_manager**: watchdog, psycopg2-binary, pika, flask
- **metadata_enricher**: Flask, psycopg2-binary, pika, requests, python-dotenv, boto3
- **normalization_worker**: psycopg2-binary, pika, flask
- **scene_analyzer**: psycopg2-binary, pika, flask
- **scheduler_ai**: psycopg2-binary, flask

## Data Models

### Dockerfile Template Structure

**Standard Service Template:**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
ENV PYTHONPATH "${PYTHONPATH}:/app"
COPY shared/ /app/shared/
COPY {service}/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY {service}/ /app/{service}/
CMD ["python", "{service}/app.py"]
```

**FFMPEG Service Template:**
```dockerfile
FROM python:3.9-slim
RUN apt-get update && apt-get install -y ffmpeg
WORKDIR /app
ENV PYTHONPATH "${PYTHONPATH}:/app"
COPY shared/ /app/shared/
COPY {service}/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY {service}/ /app/{service}/
CMD ["python", "{service}/app.py"]
```

## Error Handling

### Build Optimization

- Use `--no-cache-dir` flag for pip installations to reduce image size
- Copy shared dependencies first to leverage Docker layer caching
- Copy requirements before service code to optimize rebuild times
- Use slim base images to minimize attack surface and size

### Dependency Management

- Each service uses its own requirements.txt file
- Shared dependencies are copied to all containers
- FFMPEG is only installed where needed (normalization_worker, scene_analyzer)
- System packages are cleaned up after installation to reduce image size

## Testing Strategy

### Build Verification

1. **Individual Service Builds**: Each Dockerfile should build successfully in isolation
2. **Dependency Resolution**: All Python dependencies should install without conflicts
3. **Runtime Verification**: Each service should start and respond to health checks
4. **Shared Code Access**: Services should be able to import from shared modules

### Integration Testing

1. **Multi-service Deployment**: All services should deploy together on Render
2. **Inter-service Communication**: Services should communicate via RabbitMQ and database
3. **Resource Constraints**: Images should fit within Render's deployment limits
4. **Performance Testing**: Container startup times should be acceptable

### Validation Checklist

- [ ] All 5 Dockerfiles build without errors
- [ ] FFMPEG services can process video files
- [ ] Standard services start without FFMPEG dependencies
- [ ] Shared modules are accessible from all services
- [ ] Environment variables are properly set
- [ ] Services respond to health check endpoints
- [ ] Images are optimized for size and security