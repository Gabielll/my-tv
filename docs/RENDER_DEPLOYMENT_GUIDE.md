# Guia de Deploy no Render (Free Tier)

## Visão Geral

Este guia mostra como fazer deploy do projeto no Render usando apenas o free tier, convertendo todos os workers em web services.

## Pré-requisitos

1. **CockroachDB Cloud** (free tier)
2. **CloudAMQP** (free tier) 
3. **Cloudflare R2** (free tier)
4. **TMDB API Key** (gratuita)
5. **Conta no Render** (free tier)

## Configuração dos Serviços Externos

### 1. CockroachDB Cloud (Database)
**Passos detalhados:**
1. Acesse https://cockroachlabs.cloud/
2. Crie conta gratuita
3. Clique "Create Cluster" → "Serverless" → "Create cluster"
4. Anote as credenciais:
   - `DB_HOST`: hostname do cluster (ex: `free-tier123.cockroachlabs.cloud`)
   - `DB_PORT`: `26257` (padrão)
   - `DB_NAME`: nome do database (ex: `media_server`)
   - `DB_USER`: username gerado
   - `DB_PASSWORD`: password gerado
5. Execute o schema: `database_schema_cockroach.sql`

### 2. CloudAMQP (Message Queue)
**Passos detalhados:**
1. Acesse https://cloudamqp.com/
2. Crie conta gratuita
3. Clique "Create New Instance" → "Little Lemur (Free)" → "Select Region"
4. Anote as credenciais da URL AMQP:
   - URL: `amqps://username:password@hostname/vhost`
   - `RABBITMQ_HOST`: hostname (ex: `beaver.rmq.cloudamqp.com`)
   - `RABBITMQ_USER`: username da URL
   - `RABBITMQ_PASS`: password da URL

### 3. Cloudflare R2 (Storage)
**Passos detalhados:**
1. Acesse https://dash.cloudflare.com/
2. Crie conta gratuita
3. Vá em "R2 Object Storage" → "Create bucket"
4. Anote o nome do bucket: `R2_BUCKET_NAME`
5. Vá em "Manage R2 API tokens" → "Create API token"
6. Anote as credenciais:
   - `R2_ACCOUNT_ID`: Account ID (no dashboard)
   - `R2_ACCESS_KEY_ID`: Access Key ID gerado
   - `R2_SECRET_ACCESS_KEY`: Secret Access Key gerado
   - `R2_ENDPOINT`: `https://<account-id>.r2.cloudflarestorage.com`

### 4. TMDB API (Metadados de Filmes)
**Passos detalhados:**
1. Acesse https://themoviedb.org/
2. Crie conta gratuita
3. Vá em Settings → API → "Create" → "Developer"
4. Preencha formulário de aplicação
5. Anote: `TMDB_API_KEY` (API Key v3)

### 5. Google Gemini API (Inteligência Artificial)
**Passos detalhados:**
1. Acesse https://makersuite.google.com/
2. Faça login com conta Google
3. Clique "Get API key" → "Create API key"
4. Anote: `GEMINI_API_KEY`
5. **Limite gratuito:** 60 requests/minuto (suficiente para uso pessoal)

## Deploy no Render

### Serviços a Criar (7 Web Services)

#### 1. admin-ui
- **Tipo:** Web Service
- **Build Command:** `pip install -r admin_ui/requirements.txt`
- **Start Command:** `python admin_ui/app.py`
- **Dockerfile:** `admin_ui/Dockerfile`

#### 2. stream-api  
- **Tipo:** Web Service
- **Build Command:** `pip install -r stream_api/requirements.txt`
- **Start Command:** `python stream_api/app.py`
- **Dockerfile:** `stream_api/Dockerfile`

#### 3. frontend
- **Tipo:** Static Site
- **Publish Directory:** `frontend`

#### 4. media-manager (convertido de worker)
- **Tipo:** Web Service
- **Build Command:** `pip install -r media_manager/requirements.txt`
- **Start Command:** `python media_manager/app.py`
- **Health Check:** `/health`

#### 5. normalization-worker (convertido de worker)
- **Tipo:** Web Service  
- **Build Command:** `pip install -r normalization_worker/requirements.txt`
- **Start Command:** `python normalization_worker/app.py`
- **Health Check:** `/health`

#### 6. scene-analyzer (convertido de worker)
- **Tipo:** Web Service
- **Build Command:** `pip install -r scene_analyzer/requirements.txt` 
- **Start Command:** `python scene_analyzer/app.py`
- **Health Check:** `/health`

#### 7. scheduler-ai (convertido de worker)
- **Tipo:** Web Service
- **Build Command:** `pip install -r scheduler_ai/requirements.txt`
- **Start Command:** `python scheduler_ai/app.py`
- **Health Check:** `/health`

## Variáveis de Ambiente

### Configuração Completa por Serviço

#### Todas as Web Services precisam:

**Database (CockroachDB Cloud):**
```
DB_HOST=your-cluster.cockroachlabs.cloud
DB_PORT=26257
DB_NAME=media_server
DB_USER=your-username
DB_PASSWORD=your-password
```

**Message Queue (CloudAMQP) - apenas workers:**
```
RABBITMQ_HOST=your-instance.cloudamqp.com
RABBITMQ_USER=your-username
RABBITMQ_PASS=your-password
```

**Storage (Cloudflare R2) - admin_ui e stream_api:**
```
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=your-bucket-name
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
STORAGE_MODE=hybrid
```

**APIs Externas:**
```
TMDB_API_KEY=your-tmdb-api-key          # metadata_enricher
GEMINI_API_KEY=your-gemini-api-key      # scheduler_ai, metadata_enricher
```

**Configuração do Serviço:**
```
SERVICE_NAME=<service-name>             # Nome específico do serviço
SERVICE_VERSION=1.0.0
LOG_LEVEL=INFO
LOG_FORMAT=json
ENVIRONMENT=production
STAGING_DIR=/tmp/staging
```

### Variáveis por Serviço Específico

#### admin-ui
- ✅ Database: `DB_*`
- ✅ Storage: `R2_*`, `STORAGE_MODE`
- ✅ APIs: `TMDB_API_KEY`
- ❌ Message Queue: não precisa

#### stream-api
- ✅ Database: `DB_*`
- ✅ Storage: `R2_*`, `STORAGE_MODE`
- ❌ APIs: não precisa
- ❌ Message Queue: não precisa

#### media-manager
- ✅ Database: `DB_*`
- ✅ Message Queue: `RABBITMQ_*`
- ❌ Storage: não precisa (monitora local)
- ❌ APIs: não precisa

#### metadata-enricher
- ✅ Database: `DB_*`
- ✅ Message Queue: `RABBITMQ_*`
- ✅ APIs: `TMDB_API_KEY`, `GEMINI_API_KEY`
- ❌ Storage: não precisa

#### normalization-worker
- ✅ Database: `DB_*`
- ✅ Message Queue: `RABBITMQ_*`
- ❌ Storage: não precisa
- ❌ APIs: não precisa

#### scene-analyzer
- ✅ Database: `DB_*`
- ✅ Message Queue: `RABBITMQ_*`
- ❌ Storage: não precisa
- ❌ APIs: não precisa

#### scheduler-ai
- ✅ Database: `DB_*`
- ✅ Message Queue: `RABBITMQ_*`
- ✅ APIs: `GEMINI_API_KEY`
- ❌ Storage: não precisa

## UptimeRobot Configuration

Para manter os serviços vivos no free tier:

1. **Criar conta no UptimeRobot**
   - Acesse https://uptimerobot.com/
   - Crie conta gratuita (50 monitors inclusos)

2. **Configuração Automática (Recomendado)**
   ```bash
   # Configure sua API key
   export UPTIMEROBOT_API_KEY=your-api-key
   
   # Execute o script de configuração
   python scripts/setup_uptimerobot.py
   ```

3. **Configuração Manual**
   Adicione monitors HTTP para cada serviço:
   - `https://admin-ui-xxx.onrender.com/health`
   - `https://stream-api-xxx.onrender.com/health`
   - `https://media-manager-xxx.onrender.com/health`
   - `https://metadata-enricher-xxx.onrender.com/health`
   - `https://normalization-worker-xxx.onrender.com/health`
   - `https://scene-analyzer-xxx.onrender.com/health`
   - `https://scheduler-ai-xxx.onrender.com/health`
   
4. **Configurações Recomendadas**
   - Intervalo: 5 minutos
   - Timeout: 30 segundos
   - Tipo: HTTP(s)
   - Método: GET

## Passos do Deploy

1. **Fork/Clone** o repositório
2. **Configurar serviços externos** (DB, Queue, Storage, APIs)
3. **Criar cada serviço no Render** via dashboard
4. **Configurar variáveis de ambiente** para cada serviço
5. **Fazer deploy** de cada serviço
6. **Configurar UptimeRobot** para manter serviços vivos
7. **Testar** funcionalidade completa

## Limitações e Custos dos Serviços Gratuitos

### Render (Free Tier)
- **Sleep após 15min** de inatividade (resolvido com UptimeRobot)
- **750 horas/mês** por serviço (suficiente para 7 serviços)
- **Bandwidth:** 100GB/mês (adequado para uso pessoal)
- **Build time:** 500 minutos/mês (nossos builds são rápidos)

### CockroachDB Cloud (Free Tier)
- **Storage:** 5GB gratuitos
- **Requests:** 250M requests/mês
- **Conexões:** 1 conexão simultânea
- **Backup:** 1 backup automático

### CloudAMQP (Little Lemur - Free)
- **Conexões:** 20 conexões simultâneas
- **Queues:** Ilimitadas
- **Messages:** 1M mensagens/mês
- **Retention:** 28 dias

### Cloudflare R2 (Free Tier)
- **Storage:** 10GB gratuitos
- **Class A operations:** 1M/mês (PUT, LIST)
- **Class B operations:** 10M/mês (GET, HEAD)
- **Egress:** Gratuito (grande vantagem!)

### TMDB API (Free)
- **Requests:** 1000 requests/dia
- **Rate limit:** 40 requests/10 segundos
- **Dados:** Metadados completos de filmes/séries

### Google Gemini API (Free)
- **Requests:** 60 requests/minuto
- **Tokens:** 32K tokens por request
- **Modelos:** gemini-pro, gemini-pro-vision
- **Quota diária:** Generosa para uso pessoal

## Troubleshooting

### Serviço não inicia
**Sintomas:** Serviço falha no deploy ou não responde
**Soluções:**
1. Verificar logs no dashboard Render
2. Confirmar todas as variáveis de ambiente estão configuradas
3. Testar conectividade com serviços externos:
   ```bash
   # Teste CockroachDB
   psql "postgresql://user:pass@host:26257/dbname?sslmode=require"
   
   # Teste CloudAMQP
   curl -u user:pass http://host:15672/api/overview
   
   # Teste TMDB API
   curl "https://api.themoviedb.org/3/movie/550?api_key=YOUR_KEY"
   
   # Teste Gemini API
   curl -H "Content-Type: application/json" \
        -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_KEY"
   ```

### Workers param de funcionar
**Sintomas:** Health endpoints retornam erro ou workers não processam
**Soluções:**
1. Verificar health endpoints: `https://service-name.onrender.com/health`
2. Confirmar UptimeRobot está pingando (intervalo 5min)
3. Verificar logs de erro nos workers convertidos
4. Confirmar filas RabbitMQ estão sendo consumidas
5. Verificar conectividade com database

### Problemas de storage
**Sintomas:** Upload falha ou streaming não funciona
**Soluções:**
1. Testar credenciais R2:
   ```bash
   aws s3 ls --endpoint-url=https://account.r2.cloudflarestorage.com
   ```
2. Verificar configuração de bucket (público/privado)
3. Confirmar modo híbrido funcionando (fallback local)
4. Verificar logs do StorageManager

### Limites atingidos
**CockroachDB Cloud:**
- ⚠️ **1 conexão simultânea** - otimizar connection pooling
- ⚠️ **5GB storage** - monitorar uso de espaço

**CloudAMQP:**
- ⚠️ **1M mensagens/mês** - monitorar volume de processamento
- ⚠️ **20 conexões** - otimizar workers

**Cloudflare R2:**
- ⚠️ **10GB storage** - implementar limpeza automática
- ⚠️ **1M Class A ops/mês** - otimizar uploads

**APIs Externas:**
- ⚠️ **TMDB: 1000 req/dia** - implementar cache
- ⚠️ **Gemini: 60 req/min** - implementar rate limiting

### Render Free Tier
**Sintomas:** Serviços dormem após 15min
**Soluções:**
1. Configurar UptimeRobot com intervalo 5min
2. Verificar se todos os 7 serviços estão sendo monitorados
3. Confirmar 750h/mês não foram excedidas (≈31 dias × 24h)