# Implementation Plan

- [x] 1. Implement test mode configuration in shared/config.py
  - Add ENABLE_RABBITMQ_TEST_MODE flag at module level
  - Create is_rabbitmq_test_mode() class method for detection
  - Modify get_rabbitmq_config() to return hardcoded credentials when in test mode
  - Add warning logs when test mode is active
  - _Requirements: 1.1, 1.3, 2.1_

- [x] 2. Enhance RabbitMQ client with test mode logging
  - Add test mode detection and warning logs in get_rabbitmq_connection()
  - Improve error logging to distinguish between test and production modes
  - Add connection success logs with mode indication
  - Mask sensitive credentials in logs for security
  - _Requirements: 1.3, 5.2, 5.3_

- [ ] 3. Test RabbitMQ connection with hardcoded credentials
  - Deploy changes to media-manager service first
  - Verify connection logs show test mode activation
  - Test message publishing to enrichment_jobs queue
  - Confirm no authentication errors in logs
  - _Requirements: 1.1, 1.2, 4.2_

- [ ] 4. Implement test mode in metadata-enricher service
  - Verify metadata-enricher uses updated config
  - Test message consumption from enrichment_jobs queue
  - Test message publishing to normalization_jobs queue
  - Verify enrichment processing works end-to-end
  - _Requirements: 4.3, 5.1, 5.4_

- [ ] 5. Implement test mode in normalization-worker service
  - Verify normalization-worker uses updated config
  - Test message consumption from normalization_jobs queue
  - Test message publishing to scene_analysis_jobs queue
  - Verify normalization processing works end-to-end
  - _Requirements: 4.4, 5.1, 5.4_

- [ ] 6. Implement test mode in scene-analyzer service
  - Verify scene-analyzer uses updated config
  - Test message consumption from scene_analysis_jobs queue
  - Verify scene analysis processing completes successfully
  - Test final status update in database
  - _Requirements: 4.5, 5.1, 5.4_

- [ ] 7. Test complete pipeline end-to-end
  - Upload test video file through admin-ui interface
  - Monitor logs across all services for test mode indicators
  - Verify file progresses through all processing stages
  - Confirm final status shows completed processing
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 8. Add comprehensive logging for troubleshooting
  - Add detailed logs for message publishing with queue names and content
  - Add detailed logs for message consumption with processing status
  - Add correlation ID tracking across service boundaries
  - Add timing logs for performance monitoring
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 9. Create documentation for disabling test mode
  - Document how to set ENABLE_RABBITMQ_TEST_MODE to False
  - Document environment variable override method
  - Create commit message template for reverting changes
  - Add security notes about removing hardcoded credentials
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 10. Validate production readiness
  - Test with ENABLE_RABBITMQ_TEST_MODE = False
  - Verify system falls back to environment variables correctly
  - Confirm no test mode logs appear in production mode
  - Verify all hardcoded credentials can be easily removed
  - _Requirements: 3.1, 3.2, 3.3_