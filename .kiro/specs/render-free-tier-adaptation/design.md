# Design Document

## Overview

Este documento detalha o design para converter workers em web services mantendo a arquitetura original intacta. A conversão permite deployment no Render gratuito usando UptimeRobot para manter os serviços ativos, substituindo apenas RabbitMQ local por CloudAMQP gratuito e CockroachDB local por CockroachDB Cloud gratuito.

## Architecture

### Current vs New Service Types
```
ANTES (Docker):                    DEPOIS (Render):
┌─────────────────┐               ┌─────────────────┐
│   admin_ui      │               │   admin-ui      │
│  (Web Service)  │      →        │  (Web Service)  │
└─────────────────┘               └─────────────────┘

┌─────────────────┐               ┌─────────────────┐
│  stream_api     │               │   stream-api    │
│  (Web Service)  │      →        │  (Web Service)  │
└─────────────────┘               └─────────────────┘

┌─────────────────┐               ┌─────────────────┐
│ media_manager   │               │ media-manager   │
│   (Worker)      │      →        │ (Web Service*)  │
└─────────────────┘               └─────────────────┘

┌─────────────────┐               ┌─────────────────┐
│metadata_enricher│               │metadata-enricher│
│   (Worker)      │      →        │ (Web Service*)  │
└─────────────────┘               └─────────────────┘

┌─────────────────┐               ┌─────────────────┐
│normalization_   │               │normalization-   │
│    worker       │      →        │   worker        │
│   (Worker)      │               │ (Web Service*)  │
└─────────────────┘               └─────────────────┘

┌─────────────────┐               ┌─────────────────┐
│ scene_analyzer  │               │ scene-analyzer  │
│   (Worker)      │      →        │ (Web Service*)  │
└─────────────────┘               └─────────────────┘

┌─────────────────┐               ┌─────────────────┐
│  scheduler_ai   │               │  scheduler-ai   │
│   (Worker)      │      →        │ (Web Service*)  │
└─────────────────┘               └─────────────────┘

* Web Service que roda lógica de worker internamente
```

### External Services Migration
```
ANTES:                             DEPOIS:
┌─────────────────┐               ┌─────────────────┐
│   CockroachDB   │               │ CockroachDB     │
│    (Local)      │      →        │ Cloud (Free)    │
└─────────────────┘               └─────────────────┘

┌─────────────────┐               ┌─────────────────┐
│    RabbitMQ     │               │   CloudAMQP     │
│    (Local)      │      →        │   (Free Tier)   │
└─────────────────┘               └─────────────────┘

┌─────────────────┐               ┌─────────────────┐
│ Local Storage   │               │ Cloudflare R2   │
│ /mnt/media/*    │      →        │ (10GB Free) +   │
│                 │               │ Local Fallback  │
└─────────────────┘               └─────────────────┘
```

## Components and Interfaces

### 1. Existing Web Services (No Changes)
- **admin-ui**: Mantém funcionalidade original
- **stream-api**: Mantém funcionalidade original  
- **frontend**: Static site, sem mudanças

### 2. Converted Worker Services

#### 2.1 media-manager (Worker → Web Service)
```python
# Estrutura do novo web service
from flask import Flask, jsonify
import threading
import time

app = Flask(__name__)

# Lógica original do worker em thread separada
def worker_logic():
    while True:
        # Código original do media_manager
        monitor_staging_directory()
        time.sleep(10)

# Thread do worker iniciada no startup
worker_thread = threading.Thread(target=worker_logic, daemon=True)
worker_thread.start()

# Endpoint de saúde para UptimeRobot
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "media-manager"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
```

#### 2.2 metadata-enricher (Worker → Web Service)
```python
# Mantém lógica original de consumir RabbitMQ
def worker_logic():
    while True:
        # Código original: consome fila, processa metadados
        consume_metadata_queue()

# Endpoint de saúde
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "metadata-enricher"})
```

#### 2.3 normalization-worker (Worker → Web Service)
```python
# Mantém lógica original de normalização
def worker_logic():
    while True:
        # Código original: consome fila, normaliza vídeos
        consume_normalization_queue()

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "normalization-worker"})
```

#### 2.4 scene-analyzer (Worker → Web Service)
```python
# Mantém lógica original de análise
def worker_logic():
    while True:
        # Código original: consome fila, analisa cenas
        consume_scene_analysis_queue()

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "scene-analyzer"})
```

#### 2.5 scheduler-ai (Worker → Web Service)
```python
# Mantém lógica original de agendamento
def worker_logic():
    while True:
        # Código original: gera EPG periodicamente
        generate_epg_schedule()
        time.sleep(3600 * 4)  # 4 horas

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "scheduler-ai"})
```

## Data Models

### Database Connection (No Changes)
- Mantém todas as tabelas e schemas existentes
- Apenas muda connection string para CockroachDB Cloud
- Todas as queries permanecem idênticas

### Message Queue (Minimal Changes)
- Mantém todas as filas e mensagens existentes
- Apenas muda connection string para CloudAMQP
- Toda a lógica de pub/sub permanece idêntica

### Storage Strategy (Cloudflare R2 + Local Fallback)
```python
# Configuração híbrida de armazenamento
class StorageManager:
    def __init__(self):
        self.mode = os.getenv('STORAGE_MODE', 'local')  # 'local', 'r2', 'hybrid'
        self.r2_client = self._init_r2_client() if self.mode in ['r2', 'hybrid'] else None
    
    def save_file(self, file_path, content):
        if self.mode == 'r2':
            return self._save_to_r2(file_path, content)
        elif self.mode == 'hybrid':
            try:
                return self._save_to_r2(file_path, content)
            except Exception:
                return self._save_locally(file_path, content)
        else:
            return self._save_locally(file_path, content)
    
    def get_file_url(self, file_path):
        if self.mode in ['r2', 'hybrid'] and self._exists_in_r2(file_path):
            return f"https://{self.bucket_name}.{self.r2_endpoint}/{file_path}"
        else:
            return f"/local/{file_path}"
```

**Cloudflare R2 Benefits:**
- 10GB gratuitos (ideal para testes)
- Compatível com S3 API
- Ótimo para vídeos grandes
- CDN global integrado
- Sem custos de egress

## Error Handling

### Web Service Wrapper Errors
- **Port binding**: Usar variável PORT do Render
- **Health check failures**: Log detalhado para debugging
- **Worker thread crashes**: Implement restart logic
- **External service connectivity**: Retry logic mantido

### Original Worker Logic (No Changes)
- Mantém todo o error handling existente
- Mantém retry logic para RabbitMQ
- Mantém database error handling
- Mantém file processing error handling

## Testing Strategy

### Unit Tests (Minimal Changes)
- Testa lógica original do worker (sem mudanças)
- Adiciona testes para endpoints /health
- Testa inicialização de threads

### Integration Tests (No Changes)
- Mantém todos os testes de integração existentes
- Testa conectividade com CloudAMQP
- Testa conectividade com CockroachDB Cloud

### Health Check Tests
- Testa resposta do endpoint /health
- Testa se worker thread está ativa
- Testa conectividade com serviços externos

## Implementation Details

### Flask App Template for Workers
```python
import os
import threading
from flask import Flask, jsonify
from shared.logging_config import configure_logging, get_logger
from shared.health_check import create_standard_health_checker

# Configuração padrão para todos os workers convertidos
def create_worker_app(service_name, worker_function):
    app = Flask(__name__)
    
    # Logging
    configure_logging(service_name)
    logger = get_logger(service_name)
    
    # Health checker
    health_checker = create_standard_health_checker(service_name)
    health_checker.create_flask_endpoint(app)
    
    # Worker thread
    worker_thread = threading.Thread(target=worker_function, daemon=True)
    worker_thread.start()
    
    logger.info(f"{service_name} web service started with worker thread")
    
    return app
```

### Environment Variables (Updated)
```bash
# CockroachDB Cloud (substitui local)
DB_HOST=<cockroachdb-cloud-host>
DB_PORT=26257
DB_NAME=<database-name>
DB_USER=<username>
DB_PASSWORD=<password>

# CloudAMQP (substitui RabbitMQ local)
RABBITMQ_HOST=<cloudamqp-host>
RABBITMQ_USER=<cloudamqp-user>
RABBITMQ_PASS=<cloudamqp-password>

# Cloudflare R2 Storage (opcional, com fallback local)
R2_ACCOUNT_ID=<cloudflare-account-id>
R2_ACCESS_KEY_ID=<r2-access-key>
R2_SECRET_ACCESS_KEY=<r2-secret-key>
R2_BUCKET_NAME=<bucket-name>
R2_ENDPOINT=<account-id>.r2.cloudflarestorage.com
STORAGE_MODE=hybrid  # 'local', 'r2', ou 'hybrid'

# Render specific
PORT=<render-assigned-port>
```

### UptimeRobot Configuration
```
Service Monitoring URLs:
- https://admin-ui.onrender.com/health
- https://stream-api.onrender.com/health  
- https://media-manager.onrender.com/health
- https://metadata-enricher.onrender.com/health
- https://normalization-worker.onrender.com/health
- https://scene-analyzer.onrender.com/health
- https://scheduler-ai.onrender.com/health

Check Interval: 5 minutes
Timeout: 30 seconds
```

## Migration Strategy

### Phase 1: External Services Setup
1. Create CockroachDB Cloud free tier account
2. Create CloudAMQP free tier account  
3. Update connection strings in environment variables
4. Test connectivity from local environment

### Phase 2: Worker Conversion
1. Convert each worker to web service one by one
2. Test locally with new web service format
3. Verify original functionality is preserved
4. Deploy to Render and test

### Phase 3: UptimeRobot Setup
1. Configure monitoring for all health endpoints
2. Test that services stay alive with pings
3. Monitor for any service restarts or issues

### Phase 4: Validation
1. Run complete end-to-end tests
2. Verify file upload → processing → streaming pipeline
3. Confirm EPG generation works correctly
4. Validate system behaves identically to original