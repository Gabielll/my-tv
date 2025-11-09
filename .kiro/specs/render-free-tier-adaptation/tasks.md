# Implementation Plan

- [ ] 1. Setup external services and update configuration
  - Create CockroachDB Cloud free tier account and database
  - Create CloudAMQP free tier instance
  - Create Cloudflare R2 bucket for media storage
  - Update shared/config.py to include R2 and external service configurations
  - Test connectivity to all external services from local environment
  - _Requirements: 1.1, 4.3, 4.4_

- [x] 2. Create storage manager for Cloudflare R2 integration
  - Create shared/storage_manager.py with hybrid storage support (R2 + local fallback)
  - Implement S3-compatible client for Cloudflare R2
  - Add storage configuration methods to shared/config.py
  - Write unit tests for storage manager functionality
  - _Requirements: 1.1, 4.3_

- [x] 3. Create Flask app template for worker conversion
  - Create shared/worker_app_template.py with standard Flask wrapper
  - Implement health check endpoint integration
  - Add worker thread management and error handling
  - Create logging integration for worker web services
  - Write unit tests for Flask app template
  - _Requirements: 1.1, 3.1, 3.2, 3.3_

- [x] 4. Convert media_manager from worker to web service
  - Create media_manager/app.py using Flask app template
  - Move existing media_manager.py logic to worker_function
  - Add /health endpoint and thread management
  - Update requirements.txt to include Flask dependencies
  - Test locally that monitoring functionality works identically
  - _Requirements: 1.1, 2.1, 3.1_

- [x] 5. Convert metadata_enricher from worker to web service
  - Create metadata_enricher/app.py using Flask app template
  - Move existing metadata enrichment logic to worker_function
  - Maintain RabbitMQ queue consumption in background thread
  - Add /health endpoint with queue connectivity status
  - Test locally that metadata processing works identically
  - _Requirements: 1.1, 2.2, 3.1_

- [x] 6. Convert normalization_worker from worker to web service
  - Create normalization_worker/app.py using Flask app template
  - Move existing video normalization logic to worker_function
  - Maintain RabbitMQ queue consumption for video processing jobs
  - Add /health endpoint with processing status information
  - Test locally that video normalization works identically
  - _Requirements: 1.1, 2.3, 3.1_

- [x] 7. Convert scene_analyzer from worker to web service
  - Create scene_analyzer/app.py using Flask app template
  - Move existing scene analysis logic to worker_function
  - Maintain RabbitMQ queue consumption for analysis jobs
  - Add /health endpoint with analysis status information
  - Test locally that scene analysis works identically
  - _Requirements: 1.1, 2.4, 3.1_

- [x] 8. Convert scheduler_ai from worker to web service
  - Create scheduler_ai/app.py using Flask app template
  - Move existing EPG generation logic to worker_function
  - Maintain periodic scheduling (4-hour intervals) in background thread
  - Add /health endpoint with last schedule generation timestamp
  - Test locally that EPG generation works identically
  - _Requirements: 1.1, 2.5, 3.1_

- [x] 9. Update render.yaml configuration for Render deployment
  - Remove all worker service definitions from render.yaml
  - Convert worker services to web service definitions
  - Add environment variables for CockroachDB Cloud, CloudAMQP, and R2
  - Configure health check paths for all converted services
  - Set appropriate start commands for each Flask app
  - _Requirements: 1.1, 3.1, 4.4_

- [x] 10. Update docker-compose.yml for local development
  - Remove local CockroachDB and RabbitMQ services
  - Update environment variables to point to external services
  - Change worker services to web services with port mappings
  - Update health check commands for converted services
  - Test complete local environment with external services
  - _Requirements: 1.1, 4.4_

- [x] 11. Integrate storage manager into existing services
  - Update admin_ui/app.py to use StorageManager for file uploads
  - Update media_manager to use StorageManager for file operations
  - Update stream_api/app.py to serve files from R2 when available
  - Modify file path handling throughout the system for hybrid storage
  - Test file upload, processing, and streaming with R2 integration
  - _Requirements: 2.1, 2.2, 4.3_

- [x] 12. Create integration tests for converted architecture
  - Write end-to-end tests for complete file processing pipeline
  - Test all converted web services maintain original functionality
  - Create tests for external service connectivity (DB, Queue, Storage)
  - Test health endpoints respond correctly for UptimeRobot monitoring
  - Verify streaming works with files stored in Cloudflare R2
  - _Requirements: 2.1, 2.2, 3.1, 5.1, 5.2, 5.3, 5.4_

- [x] 13. Deploy to Render and configure UptimeRobot monitoring
  - Deploy all converted web services to Render using updated render.yaml
  - Configure environment variables in Render dashboard
  - Set up UptimeRobot monitoring for all /health endpoints
  - Test that services stay alive with UptimeRobot pings
  - Verify complete system functionality in Render environment
  - _Requirements: 1.1, 3.1, 3.2, 3.3_

- [x] 14. Update documentation and cleanup
  - Update README.md with new deployment instructions for Render
  - Update docs/DEPLOY_GUIDE_RENDER.md with Cloudflare R2 setup
  - Document UptimeRobot configuration steps
  - Create troubleshooting guide for converted services
  - Remove any obsolete worker-specific documentation
  - _Requirements: 4.4, 5.4_