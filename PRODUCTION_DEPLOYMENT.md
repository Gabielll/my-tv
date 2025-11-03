# Production Deployment Guide

This guide provides comprehensive instructions for deploying the Media Processing System to production with proper monitoring, logging, and health checks.

## Table of Contents

1. [Environment Configuration](#environment-configuration)
2. [Logging Configuration](#logging-configuration)
3. [Health Check Setup](#health-check-setup)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Deployment Checklist](#deployment-checklist)
6. [Troubleshooting](#troubleshooting)
7. [Log Analysis](#log-analysis)

## Environment Configuration

### Required Environment Variables

All services require the following environment variables for proper logging and monitoring:

#### Logging Configuration
```bash
# Logging settings
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json                   # json or text (use json for production)
LOG_OUTPUT=console                # console or file
LOG_FILE=/var/log/service.log     # Required if LOG_OUTPUT=file
SERVICE_NAME=media-manager        # Unique name for each service
ENVIRONMENT=production            # production, staging, development
SERVICE_VERSION=1.0.0             # Current service version
HOSTNAME=media-server-01          # Server hostname for log correlation
```

#### Database Configuration
```bash
# Database settings
DB_HOST=cockroachdb-cluster.internal
DB_PORT=26257
DB_NAME=media_server
DB_USER=media_app
DB_PASSWORD=secure_password_here
DB_CONNECT_TIMEOUT=10
DB_MAX_CONNECTIONS=20
DB_IDLE_TIMEOUT=300
```

#### RabbitMQ Configuration
```bash
# RabbitMQ settings
RABBITMQ_HOST=rabbitmq-cluster.internal
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=media_app
RABBITMQ_PASSWORD=secure_password_here
RABBITMQ_VIRTUAL_HOST=/media
RABBITMQ_CONNECTION_TIMEOUT=10
RABBITMQ_HEARTBEAT=600
```

#### Health Check Configuration
```bash
# Health check settings
HEALTH_CHECK_TIMEOUT=5
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_ENABLED=true
```

### Service-Specific Environment Variables

#### Admin UI
```bash
SERVICE_NAME=admin-ui
FLASK_ENV=production
FLASK_DEBUG=false
UPLOAD_FOLDER=/mnt/media/uploads
MAX_CONTENT_LENGTH=2147483648     # 2GB max file size
```

#### Media Manager
```bash
SERVICE_NAME=media-manager
MEDIA_ROOT=/mnt/media
PROCESSING_ROOT=/mnt/processing
ARCHIVE_ROOT=/mnt/archive
MAX_CONCURRENT_JOBS=5
```

#### Normalization Worker
```bash
SERVICE_NAME=normalization-worker
FFMPEG_PATH=/usr/bin/ffmpeg
TEMP_DIR=/tmp/ffmpeg
MAX_PARALLEL_JOBS=3
QUALITY_PRESET=medium
```

#### Scheduler AI
```bash
SERVICE_NAME=scheduler-ai
SCHEDULING_INTERVAL=60
MAX_QUEUE_SIZE=100
PRIORITY_ALGORITHM=weighted_round_robin
```

#### Scene Analyzer
```bash
SERVICE_NAME=scene-analyzer
MODEL_PATH=/opt/models/scene_detection
ANALYSIS_TIMEOUT=300
BATCH_SIZE=10
```

#### Stream API
```bash
SERVICE_NAME=stream-api
STREAM_ROOT=/mnt/media/streams
CHUNK_SIZE=1048576               # 1MB chunks
CACHE_TIMEOUT=3600               # 1 hour
```

## Logging Configuration

### Structured Logging Format

All services use structured JSON logging with the following format:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "service": "media-manager",
  "hostname": "media-server-01",
  "environment": "production",
  "version": "1.0.0",
  "message": "File processing completed",
  "logger": "media_manager",
  "module": "processor",
  "function": "process_file",
  "line": 145,
  "correlation_id": "req_abc123def456",
  "context": {
    "file_id": "12345",
    "filename": "video.mp4",
    "processing_time_ms": 15420,
    "output_format": "h264"
  },
  "duration_ms": 15420
}
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational messages
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical errors requiring immediate attention

### Log Rotation

Configure log rotation for file-based logging:

```bash
# /etc/logrotate.d/media-processing
/var/log/media-processing/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 app app
    postrotate
        systemctl reload media-processing-*
    endscript
}
```

## Health Check Setup

### Health Check Endpoints

Each service exposes a health check endpoint at `/health`:

```bash
# Check service health
curl -f http://localhost:5000/health

# Example healthy response (HTTP 200)
{
  "status": "healthy",
  "service": "media-manager",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "uptime_seconds": 3600,
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12.5
    },
    "rabbitmq": {
      "status": "healthy",
      "response_time_ms": 8.2
    },
    "disk_space": {
      "status": "healthy",
      "response_time_ms": 2.1
    }
  }
}

# Example unhealthy response (HTTP 503)
{
  "status": "unhealthy",
  "service": "media-manager",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "uptime_seconds": 3600,
  "checks": {
    "database": {
      "status": "unhealthy",
      "response_time_ms": 5000.0,
      "error": "Connection timeout"
    },
    "rabbitmq": {
      "status": "healthy",
      "response_time_ms": 8.2
    },
    "disk_space": {
      "status": "healthy",
      "response_time_ms": 2.1
    }
  }
}
```

### Load Balancer Health Checks

Configure your load balancer to use the health check endpoints:

```nginx
# Nginx upstream configuration
upstream media_manager {
    server media-manager-01:5000 max_fails=3 fail_timeout=30s;
    server media-manager-02:5000 max_fails=3 fail_timeout=30s;
    
    # Health check (requires nginx-plus or custom module)
    health_check uri=/health interval=30s fails=3 passes=2;
}
```

### Docker Health Checks

Health checks are configured in docker-compose.yml:

```yaml
services:
  media-manager:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Monitoring and Alerting

### Log Aggregation

#### ELK Stack Configuration

1. **Elasticsearch Index Template**:
```json
{
  "index_patterns": ["media-processing-*"],
  "template": {
    "mappings": {
      "properties": {
        "timestamp": {"type": "date"},
        "level": {"type": "keyword"},
        "service": {"type": "keyword"},
        "correlation_id": {"type": "keyword"},
        "message": {"type": "text"},
        "context": {"type": "object"},
        "duration_ms": {"type": "float"}
      }
    }
  }
}
```

2. **Logstash Configuration**:
```ruby
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] =~ /media-/ {
    json {
      source => "message"
    }
    
    date {
      match => [ "timestamp", "ISO8601" ]
    }
    
    if [level] == "ERROR" or [level] == "CRITICAL" {
      mutate {
        add_tag => [ "alert" ]
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "media-processing-%{+YYYY.MM.dd}"
  }
}
```

3. **Filebeat Configuration**:
```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/media-processing/*.log
  fields:
    service: media-processing
  fields_under_root: true
  json.keys_under_root: true
  json.add_error_key: true

output.logstash:
  hosts: ["logstash:5044"]
```

### Metrics Collection

#### Prometheus Metrics

Each service should expose metrics at `/metrics`:

```python
# Example metrics in media_manager.py
from prometheus_client import Counter, Histogram, Gauge

# Counters
files_processed_total = Counter('files_processed_total', 'Total files processed', ['service', 'status'])
errors_total = Counter('errors_total', 'Total errors', ['service', 'error_type'])

# Histograms
processing_duration = Histogram('processing_duration_seconds', 'File processing duration', ['service'])
request_duration = Histogram('request_duration_seconds', 'Request duration', ['service', 'endpoint'])

# Gauges
active_jobs = Gauge('active_jobs', 'Number of active processing jobs', ['service'])
queue_size = Gauge('queue_size', 'Size of processing queue', ['service'])
```

### Alerting Rules

#### Prometheus Alerting Rules

```yaml
# /etc/prometheus/rules/media-processing.yml
groups:
- name: media-processing
  rules:
  - alert: ServiceDown
    expr: up{job=~"media-.*"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service {{ $labels.job }} is down"
      description: "Service {{ $labels.job }} has been down for more than 1 minute"

  - alert: HighErrorRate
    expr: rate(errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in {{ $labels.service }}"
      description: "Error rate is {{ $value }} errors per second"

  - alert: DatabaseConnectionFailure
    expr: database_connection_failures_total > 0
    for: 0m
    labels:
      severity: critical
    annotations:
      summary: "Database connection failure in {{ $labels.service }}"
      description: "Service cannot connect to database"

  - alert: DiskSpaceLow
    expr: disk_free_bytes / disk_total_bytes < 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Low disk space on {{ $labels.instance }}"
      description: "Disk space is below 10% on {{ $labels.instance }}"

  - alert: QueueBacklog
    expr: queue_size > 100
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Processing queue backlog in {{ $labels.service }}"
      description: "Queue size is {{ $value }} items"
```

## Deployment Checklist

### Pre-Deployment

- [ ] Environment variables configured for all services
- [ ] Database schema updated and migrations applied
- [ ] RabbitMQ queues and exchanges configured
- [ ] SSL certificates installed and configured
- [ ] Firewall rules configured
- [ ] Load balancer configuration updated
- [ ] Monitoring and alerting configured
- [ ] Log aggregation configured
- [ ] Backup procedures verified

### Deployment Steps

1. **Database Migration**:
```bash
# Run database migrations
docker run --rm -v $(pwd):/app media-processing:latest \
  python manage.py migrate --check

# Apply migrations if needed
docker run --rm -v $(pwd):/app media-processing:latest \
  python manage.py migrate
```

2. **Service Deployment**:
```bash
# Deploy services with zero downtime
docker-compose pull
docker-compose up -d --no-deps --scale media-manager=2 media-manager-new
# Wait for health checks to pass
docker-compose stop media-manager-old
docker-compose rm media-manager-old
```

3. **Health Check Verification**:
```bash
# Verify all services are healthy
for service in admin-ui media-manager normalization-worker scheduler-ai scene-analyzer stream-api; do
  echo "Checking $service..."
  curl -f http://$service:5000/health || echo "FAILED: $service"
done
```

### Post-Deployment

- [ ] All services passing health checks
- [ ] Log aggregation receiving logs from all services
- [ ] Metrics being collected and displayed in dashboards
- [ ] Alerting rules active and notifications working
- [ ] End-to-end functionality test completed
- [ ] Performance baseline established
- [ ] Documentation updated with any changes

## Troubleshooting

### Common Issues

#### Service Won't Start

1. **Check logs**:
```bash
docker-compose logs service-name
```

2. **Verify environment variables**:
```bash
docker-compose exec service-name env | grep -E "(DB_|RABBITMQ_|LOG_)"
```

3. **Test database connectivity**:
```bash
docker-compose exec service-name python -c "
from shared.db import get_db_connection
try:
    conn = get_db_connection()
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

#### Health Check Failures

1. **Check individual dependencies**:
```bash
# Test database
curl -f http://service:5000/health | jq '.checks.database'

# Test RabbitMQ
curl -f http://service:5000/health | jq '.checks.rabbitmq'
```

2. **Check resource usage**:
```bash
# Memory usage
docker stats --no-stream

# Disk space
df -h /mnt/media
```

#### High Error Rates

1. **Check error logs**:
```bash
# Recent errors
docker-compose logs --tail=100 service-name | grep ERROR

# Error patterns
docker-compose logs service-name | grep ERROR | awk '{print $NF}' | sort | uniq -c
```

2. **Check correlation IDs**:
```bash
# Follow a specific request
docker-compose logs service-name | grep "req_abc123def456"
```

### Performance Issues

#### Slow Database Queries

1. **Enable query logging**:
```bash
# Set LOG_LEVEL=DEBUG for database module
docker-compose exec service-name python -c "
import logging
logging.getLogger('database').setLevel(logging.DEBUG)
"
```

2. **Analyze slow queries**:
```sql
-- CockroachDB slow query log
SELECT query, count, avg_latency, max_latency 
FROM crdb_internal.statement_statistics 
WHERE avg_latency > interval '100ms'
ORDER BY avg_latency DESC;
```

#### Memory Leaks

1. **Monitor memory usage**:
```bash
# Memory usage over time
docker stats --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}" --no-stream
```

2. **Check for memory leaks**:
```python
# Add to service code for debugging
import tracemalloc
tracemalloc.start()

# ... application code ...

# Get memory usage
current, peak = tracemalloc.get_traced_memory()
logger.info("Memory usage", context={
    "current_mb": current / 1024 / 1024,
    "peak_mb": peak / 1024 / 1024
})
```

## Log Analysis

### Useful Log Queries

#### Elasticsearch/Kibana Queries

1. **Error rate by service**:
```json
{
  "query": {
    "bool": {
      "must": [
        {"term": {"level": "ERROR"}},
        {"range": {"timestamp": {"gte": "now-1h"}}}
      ]
    }
  },
  "aggs": {
    "services": {
      "terms": {"field": "service"}
    }
  }
}
```

2. **Request tracing by correlation ID**:
```json
{
  "query": {
    "term": {"correlation_id": "req_abc123def456"}
  },
  "sort": [{"timestamp": {"order": "asc"}}]
}
```

3. **Performance analysis**:
```json
{
  "query": {
    "bool": {
      "must": [
        {"exists": {"field": "duration_ms"}},
        {"range": {"timestamp": {"gte": "now-1h"}}}
      ]
    }
  },
  "aggs": {
    "avg_duration": {"avg": {"field": "duration_ms"}},
    "max_duration": {"max": {"field": "duration_ms"}},
    "percentiles": {"percentiles": {"field": "duration_ms"}}
  }
}
```

### Log Analysis Scripts

#### Error Pattern Analysis

```bash
#!/bin/bash
# analyze_errors.sh - Analyze error patterns in logs

echo "Top 10 error messages in the last hour:"
docker-compose logs --since=1h | \
  grep ERROR | \
  jq -r '.message' | \
  sort | uniq -c | sort -nr | head -10

echo -e "\nError distribution by service:"
docker-compose logs --since=1h | \
  grep ERROR | \
  jq -r '.service' | \
  sort | uniq -c | sort -nr

echo -e "\nCorrelation IDs with multiple errors:"
docker-compose logs --since=1h | \
  grep ERROR | \
  jq -r '.correlation_id' | \
  sort | uniq -c | sort -nr | \
  awk '$1 > 1 {print $2}' | head -5
```

#### Performance Analysis

```bash
#!/bin/bash
# analyze_performance.sh - Analyze performance metrics

echo "Average response times by service (last hour):"
docker-compose logs --since=1h | \
  grep -E "(duration_ms|response_time_ms)" | \
  jq -r '"\(.service) \(.duration_ms // .context.response_time_ms)"' | \
  awk '{sum[$1]+=$2; count[$1]++} END {for(s in sum) printf "%s: %.2fms\n", s, sum[s]/count[s]}' | \
  sort -k2 -nr

echo -e "\nSlowest operations (>1000ms):"
docker-compose logs --since=1h | \
  jq 'select(.duration_ms > 1000) | "\(.timestamp) \(.service) \(.message) \(.duration_ms)ms"' -r | \
  head -10
```

### Dashboard Configuration

#### Grafana Dashboard Panels

1. **Service Health Overview**:
```json
{
  "title": "Service Health Status",
  "type": "stat",
  "targets": [
    {
      "expr": "up{job=~\"media-.*\"}",
      "legendFormat": "{{job}}"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "color": {
        "mode": "thresholds"
      },
      "thresholds": {
        "steps": [
          {"color": "red", "value": 0},
          {"color": "green", "value": 1}
        ]
      }
    }
  }
}
```

2. **Error Rate Trends**:
```json
{
  "title": "Error Rate by Service",
  "type": "graph",
  "targets": [
    {
      "expr": "rate(errors_total[5m])",
      "legendFormat": "{{service}}"
    }
  ],
  "yAxes": [
    {
      "label": "Errors per second",
      "min": 0
    }
  ]
}
```

3. **Response Time Distribution**:
```json
{
  "title": "Response Time Percentiles",
  "type": "graph",
  "targets": [
    {
      "expr": "histogram_quantile(0.50, rate(request_duration_seconds_bucket[5m]))",
      "legendFormat": "50th percentile"
    },
    {
      "expr": "histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m]))",
      "legendFormat": "95th percentile"
    },
    {
      "expr": "histogram_quantile(0.99, rate(request_duration_seconds_bucket[5m]))",
      "legendFormat": "99th percentile"
    }
  ]
}
```

## Security Considerations

### Log Security

- **Sensitive Data**: Ensure no passwords, tokens, or PII are logged
- **Log Access**: Restrict access to log files and aggregation systems
- **Log Retention**: Implement appropriate log retention policies
- **Log Integrity**: Use log signing or immutable storage for audit logs

### Health Check Security

- **Authentication**: Consider adding authentication to health check endpoints in production
- **Information Disclosure**: Limit information exposed in health check responses
- **Rate Limiting**: Implement rate limiting on health check endpoints

### Monitoring Security

- **Metrics Access**: Secure access to metrics endpoints
- **Alert Channels**: Use secure channels for alert notifications
- **Dashboard Access**: Implement proper authentication for monitoring dashboards

## Maintenance

### Regular Tasks

- **Log Rotation**: Ensure log rotation is working properly
- **Health Check Monitoring**: Verify health checks are functioning
- **Alert Testing**: Test alert notifications regularly
- **Performance Review**: Review performance metrics and trends
- **Capacity Planning**: Monitor resource usage and plan for scaling

### Updates and Changes

- **Configuration Changes**: Document all configuration changes
- **Service Updates**: Follow proper deployment procedures for updates
- **Monitoring Updates**: Keep monitoring and alerting rules up to date
- **Documentation**: Keep this guide updated with any changes

---

For additional support or questions about production deployment, please refer to the project documentation or contact the development team.