# 🔧 Troubleshooting Guide - Converted Services

## 🎯 Overview

This guide helps troubleshoot issues specific to the converted worker-to-web-service architecture deployed on Render.

## 🚨 Common Issues

### 1. Service Won't Start

**Symptoms:**
- Service fails during build or startup
- Health endpoint returns 503 or doesn't respond
- Service shows as "Deploy failed" in Render dashboard

**Diagnosis:**
```bash
# Check Render logs
# Go to Render Dashboard → Service → Logs

# Test health endpoint
curl https://your-service.onrender.com/health

# Check if service is sleeping
curl -I https://your-service.onrender.com/health
# Look for response time > 30 seconds (indicates cold start)
```

**Solutions:**
1. **Missing Environment Variables**
   ```bash
   # Verify all required env vars are set in Render dashboard
   # Check .env.example for required variables per service
   ```

2. **External Service Connectivity**
   ```bash
   # Test database connection
   psql "postgresql://user:pass@host:26257/dbname?sslmode=require"
   
   # Test RabbitMQ connection
   curl -u user:pass https://host.cloudamqp.com/api/overview
   
   # Test R2 credentials
   aws s3 ls --endpoint-url=https://account-id.r2.cloudflarestorage.com
   ```

3. **Build Dependencies**
   ```bash
   # Check if requirements.txt includes all dependencies
   # Common missing: Flask, requests, psycopg2-binary, pika
   ```

### 2. Workers Not Processing Jobs

**Symptoms:**
- Files uploaded but not processed
- Database shows items stuck in "pending" status
- RabbitMQ queues have messages but workers aren't consuming

**Diagnosis:**
```bash
# Check worker health endpoints
curl https://media-manager-xxx.onrender.com/health
curl https://metadata-enricher-xxx.onrender.com/health
curl https://normalization-worker-xxx.onrender.com/health
curl https://scene-analyzer-xxx.onrender.com/health
curl https://scheduler-ai-xxx.onrender.com/health

# Check RabbitMQ queue status
# Login to CloudAMQP dashboard → Queues
```

**Solutions:**
1. **Services Sleeping**
   ```bash
   # Ensure UptimeRobot is configured and pinging every 5 minutes
   # Check UptimeRobot dashboard for monitor status
   ```

2. **RabbitMQ Connection Issues**
   ```bash
   # Verify RABBITMQ_* environment variables
   # Check CloudAMQP connection limits (20 concurrent connections)
   # Restart services if connection pool is exhausted
   ```

3. **Database Connection Issues**
   ```bash
   # CockroachDB free tier allows only 1 concurrent connection
   # Check if multiple services are trying to connect simultaneously
   # Implement connection pooling or retry logic
   ```

### 3. File Upload/Storage Issues

**Symptoms:**
- File upload fails in admin UI
- Files uploaded but not accessible via stream API
- Storage errors in logs

**Diagnosis:**
```bash
# Test admin UI upload
curl -X POST -F "mediafiles=@test.mp4" https://admin-ui-xxx.onrender.com/upload

# Test stream API file access
curl https://stream-api-xxx.onrender.com/streams

# Check storage manager health
curl https://admin-ui-xxx.onrender.com/health | jq '.storage'
```

**Solutions:**
1. **R2 Configuration Issues**
   ```bash
   # Verify R2_* environment variables
   # Test R2 credentials locally:
   aws configure set aws_access_key_id YOUR_R2_ACCESS_KEY
   aws configure set aws_secret_access_key YOUR_R2_SECRET_KEY
   aws s3 ls --endpoint-url=https://account-id.r2.cloudflarestorage.com
   ```

2. **Storage Mode Configuration**
   ```bash
   # Ensure STORAGE_MODE is set correctly:
   # 'local' - local only (for testing)
   # 'r2' - R2 only (requires valid R2 credentials)
   # 'hybrid' - R2 with local fallback (recommended)
   ```

3. **File Permissions**
   ```bash
   # Render services run with limited permissions
   # Ensure files are written to /tmp/ directories
   # Check STAGING_DIR, NORMALIZED_DIR, STREAMS_DIR paths
   ```

### 4. Health Checks Failing

**Symptoms:**
- UptimeRobot reports service as down
- Health endpoint returns 503
- Service appears online but health check fails

**Diagnosis:**
```bash
# Test health endpoint directly
curl -v https://your-service.onrender.com/health

# Check health endpoint response format
curl https://your-service.onrender.com/health | jq '.'
```

**Solutions:**
1. **Dependency Health Checks**
   ```bash
   # Health checks test database and RabbitMQ connectivity
   # If external services are down, health check will fail
   # Verify external service status:
   # - CockroachDB Cloud dashboard
   # - CloudAMQP dashboard
   ```

2. **Health Check Timeout**
   ```bash
   # Health checks have 30-second timeout
   # If external services are slow, health check may timeout
   # Consider increasing timeout or optimizing health check logic
   ```

3. **Service-Specific Health Issues**
   ```bash
   # media-manager: Check if file observer is running
   # metadata-enricher: Check API connectivity (TMDB, Gemini)
   # normalization-worker: Check ffmpeg availability
   # scene-analyzer: Check ffmpeg availability
   # scheduler-ai: Check last run timestamp
   ```

### 5. Performance Issues

**Symptoms:**
- Slow response times
- Services timing out
- High resource usage

**Diagnosis:**
```bash
# Check service response times
time curl https://your-service.onrender.com/health

# Monitor resource usage in Render dashboard
# Check for memory or CPU limits being hit
```

**Solutions:**
1. **Cold Start Optimization**
   ```bash
   # Services sleep after 15 minutes of inactivity
   # First request after sleep takes 30+ seconds
   # UptimeRobot prevents this by pinging every 5 minutes
   ```

2. **Database Connection Optimization**
   ```bash
   # CockroachDB free tier has 1 connection limit
   # Implement connection pooling
   # Use connection timeouts
   # Close connections promptly
   ```

3. **Memory Optimization**
   ```bash
   # Render free tier has 512MB RAM limit
   # Optimize worker processes
   # Avoid loading large files into memory
   # Use streaming for file processing
   ```

## 🔍 Service-Specific Troubleshooting

### Admin UI
```bash
# Common issues:
# - File upload size limits
# - Storage manager configuration
# - Template rendering errors

# Debug steps:
curl -X POST -F "mediafiles=@test.mp4" https://admin-ui-xxx.onrender.com/upload
curl https://admin-ui-xxx.onrender.com/health | jq '.storage'
```

### Stream API
```bash
# Common issues:
# - FFmpeg not available
# - File path resolution
# - Streaming process management

# Debug steps:
curl https://stream-api-xxx.onrender.com/streams
curl https://stream-api-xxx.onrender.com/health | jq '.dependencies'
```

### Media Manager
```bash
# Common issues:
# - File observer not starting
# - Directory permissions
# - Database insertion failures

# Debug steps:
curl https://media-manager-xxx.onrender.com/health | jq '.file_observer'
# Check if staging directory is writable
```

### Metadata Enricher
```bash
# Common issues:
# - API key configuration
# - Rate limiting
# - Network connectivity

# Debug steps:
curl https://metadata-enricher-xxx.onrender.com/health | jq '.apis'
# Test TMDB API: curl "https://api.themoviedb.org/3/movie/550?api_key=YOUR_KEY"
# Test Gemini API: (see full curl command in main troubleshooting guide)
```

### Normalization Worker
```bash
# Common issues:
# - FFmpeg not available
# - File processing failures
# - Output directory permissions

# Debug steps:
curl https://normalization-worker-xxx.onrender.com/health | jq '.ffmpeg'
# Check if normalized directory is writable
```

### Scene Analyzer
```bash
# Common issues:
# - FFmpeg not available
# - Scene detection failures
# - Processing timeouts

# Debug steps:
curl https://scene-analyzer-xxx.onrender.com/health | jq '.ffmpeg'
# Check processing status and last job timestamp
```

### Scheduler AI
```bash
# Common issues:
# - Gemini API configuration
# - Scheduling logic errors
# - Database update failures

# Debug steps:
curl https://scheduler-ai-xxx.onrender.com/health | jq '.scheduling'
# Check last run timestamp and next scheduled run
```

## 📊 Monitoring and Alerting

### UptimeRobot Configuration
```bash
# Ensure all 7 services are monitored:
# 1. admin-ui
# 2. stream-api  
# 3. media-manager
# 4. metadata-enricher
# 5. normalization-worker
# 6. scene-analyzer
# 7. scheduler-ai

# Monitor configuration:
# - Interval: 5 minutes
# - Timeout: 30 seconds
# - HTTP method: GET
# - Path: /health
```

### Log Analysis
```bash
# Key log patterns to watch for:
# - "Health check failed" - Service dependencies down
# - "Connection refused" - External service connectivity issues
# - "Timeout" - Performance issues
# - "Rate limit" - API quota exceeded
# - "Permission denied" - File system issues
```

### Resource Monitoring
```bash
# Monitor these metrics:
# - Response time (should be < 5 seconds for health checks)
# - Memory usage (should be < 512MB)
# - CPU usage (should be reasonable for free tier)
# - Disk usage (temporary files in /tmp)
```

## 🚀 Performance Optimization

### Database Optimization
```bash
# CockroachDB free tier optimization:
# - Use connection pooling
# - Implement retry logic
# - Close connections promptly
# - Use prepared statements
# - Optimize queries
```

### RabbitMQ Optimization
```bash
# CloudAMQP free tier optimization:
# - Limit concurrent connections (max 20)
# - Use connection pooling
# - Implement message acknowledgments
# - Set appropriate prefetch counts
# - Monitor queue depths
```

### Storage Optimization
```bash
# Cloudflare R2 optimization:
# - Use hybrid mode for best performance
# - Implement local caching
# - Optimize file upload/download
# - Monitor Class A/B operation limits
# - Use appropriate content types
```

## 📞 Getting Help

### Render Support
- Dashboard: https://render.com/
- Documentation: https://render.com/docs
- Community: https://community.render.com/

### External Services Support
- CockroachDB: https://cockroachlabs.cloud/
- CloudAMQP: https://cloudamqp.com/
- Cloudflare R2: https://dash.cloudflare.com/
- TMDB API: https://developers.themoviedb.org/
- Google Gemini: https://ai.google.dev/

### Project-Specific Help
- Run integration tests: `python tests/test_e2e_converted_services.py`
- Verify deployment: `python scripts/verify_deployment.py`
- Check logs in Render dashboard
- Review health endpoint responses

---

**💡 Pro Tip:** Most issues with converted services are related to external service connectivity or configuration. Always check environment variables and external service status first!