# Implementation Plan

- [x] 1. Create Dockerfile for media_manager service
  - Write Dockerfile using standard Python base image template
  - Configure proper PYTHONPATH and working directory
  - Copy shared dependencies and service-specific requirements
  - Set up command to run media_manager/app.py
  - _Requirements: 1.1, 1.4, 2.1, 2.3, 3.1, 3.3, 4.2_

- [x] 2. Create Dockerfile for metadata_enricher service  
  - Write Dockerfile using standard Python base image template
  - Include all metadata_enricher specific dependencies (boto3, requests, python-dotenv)
  - Configure shared code access and proper Python path
  - Set up command to run metadata_enricher/app.py
  - _Requirements: 1.1, 1.4, 2.1, 2.3, 3.1, 3.3, 4.2_

- [x] 3. Create Dockerfile for scheduler_ai service
  - Write Dockerfile using standard Python base image template  
  - Configure minimal dependencies for scheduler service
  - Set up shared code copying and Python environment
  - Set up command to run scheduler_ai/app.py
  - _Requirements: 1.1, 1.4, 2.1, 2.3, 3.1, 3.3, 4.2_

- [x] 4. Create Dockerfile for normalization_worker service
  - Write Dockerfile using FFMPEG-enabled base image template
  - Install FFMPEG system dependencies for video processing
  - Configure shared code access and service requirements
  - Set up command to run normalization_worker/app.py
  - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.3, 3.1, 3.4, 4.2_

- [x] 5. Create Dockerfile for scene_analyzer service
  - Write Dockerfile using FFMPEG-enabled base image template
  - Install FFMPEG system dependencies for video analysis
  - Configure shared code copying and Python environment
  - Set up command to run scene_analyzer/app.py  
  - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.3, 3.1, 3.4, 4.2_

- [x] 6. Verify all Dockerfiles follow consistent patterns
  - Review all 5 Dockerfiles for structural consistency
  - Ensure proper file copying order (shared, requirements, service code)
  - Validate environment variable configuration across all services
  - Confirm command definitions use correct service paths
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 4.1, 4.3_

- [x] 7. Test Docker builds for all services
  - Write test script to build each Dockerfile individually
  - Verify successful builds without errors for all 5 services
  - Check that FFMPEG services include video processing capabilities
  - Validate that standard services build with minimal dependencies
  - _Requirements: 1.1, 1.3, 1.4, 3.1, 3.2, 4.1, 4.3_