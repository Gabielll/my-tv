# Guia de Desenvolvimento Local

## Visão Geral

Este guia mostra como executar o projeto localmente usando serviços externos (CockroachDB Cloud, CloudAMQP, Cloudflare R2) em vez de serviços locais.

## Pré-requisitos

1. **Docker e Docker Compose** instalados
2. **Serviços externos configurados:**
   - CockroachDB Cloud (free tier)
   - CloudAMQP (free tier)
   - Cloudflare R2 (free tier)
   - TMDB API Key (gratuita)
   - Google Gemini API Key (gratuita)

## Configuração

### 1. Configurar Variáveis de Ambiente

Copie o arquivo de exemplo:
```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```bash
# External Database (CockroachDB Cloud)
DB_HOST=your-cluster.cockroachlabs.cloud
DB_PORT=26257
DB_NAME=media_server
DB_USER=your-username
DB_PASSWORD=your-password

# External Message Queue (CloudAMQP)
RABBITMQ_HOST=your-instance.cloudamqp.com
RABBITMQ_USER=your-username
RABBITMQ_PASS=your-password

# External Storage (Cloudflare R2)
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=your-bucket-name
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
STORAGE_MODE=hybrid

# External APIs
TMDB_API_KEY=your-tmdb-api-key
GEMINI_API_KEY=your-gemini-api-key
```

### Como Obter as Credenciais

#### CockroachDB Cloud (Database)
1. Acesse https://cockroachlabs.cloud/
2. Crie cluster "Serverless" gratuito
3. Anote: `DB_HOST`, `DB_USER`, `DB_PASSWORD`

#### CloudAMQP (Message Queue)
1. Acesse https://cloudamqp.com/
2. Crie instância "Little Lemur" gratuita
3. Extraia da URL AMQP: `amqps://user:pass@host/vhost`

#### Cloudflare R2 (Storage)
1. Acesse https://dash.cloudflare.com/
2. Ative "R2 Object Storage" → Crie bucket
3. Gere API tokens em "Manage R2 API tokens"

#### TMDB API (Metadados)
1. Acesse https://themoviedb.org/
2. Settings → API → "Create" → Developer
3. Anote API Key v3

#### Google Gemini API (IA)
1. Acesse https://makersuite.google.com/
2. "Get API key" → "Create API key"
3. **Limite:** 60 requests/minuto (gratuito)

### 2. Inicializar Database

Execute o schema no seu CockroachDB Cloud:
```bash
# Conecte ao seu cluster e execute:
# database_schema_cockroach.sql
```

## Executando o Projeto

### Iniciar todos os serviços:
```bash
docker-compose up -d
```

### Verificar status dos serviços:
```bash
docker-compose ps
```

### Ver logs de um serviço específico:
```bash
docker-compose logs -f media_manager
```

## Serviços e Portas

| Serviço | Porta | Endpoint | Descrição |
|---------|-------|----------|-----------|
| admin_ui | 8000 | http://localhost:8000 | Interface de administração |
| stream-api | 8001 | http://localhost:8001 | API de streaming |
| media_manager | 8002 | http://localhost:8002/health | Monitoramento de arquivos |
| metadata_enricher | 8003 | http://localhost:8003/health | Enriquecimento de metadados |
| normalization_worker | 8004 | http://localhost:8004/health | Normalização de vídeo |
| scene_analyzer | 8005 | http://localhost:8005/health | Análise de cenas |
| scheduler_ai | 8006 | http://localhost:8006/health | Geração de EPG |
| nginx | 80 | http://localhost | Proxy reverso |

## Health Checks

Todos os workers convertidos têm endpoints de health check:

```bash
# Verificar se todos os serviços estão saudáveis
curl http://localhost:8002/health  # media_manager
curl http://localhost:8003/health  # metadata_enricher
curl http://localhost:8004/health  # normalization_worker
curl http://localhost:8005/health  # scene_analyzer
curl http://localhost:8006/health  # scheduler_ai
```

## Desenvolvimento

### Rebuild de um serviço específico:
```bash
docker-compose build media_manager
docker-compose up -d media_manager
```

### Executar testes:
```bash
docker-compose exec media_manager python -m pytest
```

### Acessar shell de um container:
```bash
docker-compose exec media_manager bash
```

## Troubleshooting

### Serviço não inicia
**Sintomas:** Container falha ao iniciar ou sai imediatamente
**Soluções:**
1. Verificar logs detalhados:
   ```bash
   docker-compose logs service_name
   docker-compose logs --tail=50 service_name
   ```
2. Verificar variáveis de ambiente no `.env`:
   ```bash
   # Verificar se todas as variáveis estão definidas
   grep -v '^#' .env | grep -v '^$'
   ```
3. Testar conectividade com serviços externos:
   ```bash
   # Teste CockroachDB
   psql "postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME?sslmode=require"
   
   # Teste CloudAMQP (se tiver curl no container)
   docker-compose exec media_manager curl -u $RABBITMQ_USER:$RABBITMQ_PASS http://$RABBITMQ_HOST:15672/api/overview
   ```

### Problemas de conectividade
**Sintomas:** Timeouts, connection refused, DNS errors
**Soluções:**
1. Verificar credenciais dos serviços externos:
   - CockroachDB: testar string de conexão
   - CloudAMQP: verificar URL AMQP completa
   - R2: testar credenciais com AWS CLI
2. Verificar firewall/rede local
3. Testar APIs externas:
   ```bash
   # Teste TMDB API
   curl "https://api.themoviedb.org/3/movie/550?api_key=$TMDB_API_KEY"
   
   # Teste Gemini API
   curl -H "Content-Type: application/json" \
        -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$GEMINI_API_KEY"
   ```

### Workers não processam
**Sintomas:** Health checks OK mas não processa arquivos/filas
**Soluções:**
1. Verificar health endpoints detalhadamente:
   ```bash
   curl -s http://localhost:8002/health | jq .  # media_manager
   curl -s http://localhost:8003/health | jq .  # metadata_enricher
   ```
2. Verificar logs dos workers em tempo real:
   ```bash
   docker-compose logs -f media_manager metadata_enricher
   ```
3. Verificar filas RabbitMQ:
   - Acessar CloudAMQP dashboard
   - Verificar se mensagens estão sendo consumidas
4. Testar upload de arquivo:
   ```bash
   # Upload via admin_ui
   curl -F "mediafiles=@test.mp4" http://localhost:8000/upload
   ```

### Problemas de Storage (R2)
**Sintomas:** Upload falha ou arquivos não aparecem
**Soluções:**
1. Verificar modo de storage:
   ```bash
   # Verificar logs do StorageManager
   docker-compose logs admin_ui | grep -i storage
   ```
2. Testar fallback local:
   ```bash
   # Temporariamente usar apenas local
   echo "STORAGE_MODE=local" >> .env
   docker-compose restart admin_ui
   ```
3. Verificar credenciais R2:
   ```bash
   # Instalar AWS CLI e testar
   aws configure set aws_access_key_id $R2_ACCESS_KEY_ID
   aws configure set aws_secret_access_key $R2_SECRET_ACCESS_KEY
   aws s3 ls --endpoint-url=$R2_ENDPOINT
   ```

### Problemas de Performance
**Sintomas:** Lentidão, timeouts, alta CPU/memória
**Soluções:**
1. Monitorar recursos:
   ```bash
   docker stats
   docker-compose top
   ```
2. Verificar limites dos serviços gratuitos:
   - **CockroachDB:** 1 conexão simultânea
   - **CloudAMQP:** 20 conexões máx
   - **APIs:** Rate limits (TMDB: 40 req/10s, Gemini: 60 req/min)
3. Otimizar configuração:
   ```bash
   # Reduzir workers se necessário
   docker-compose up --scale normalization_worker=1
   ```

### Problemas Específicos por Serviço

#### media_manager
- **Problema:** Não detecta arquivos novos
- **Solução:** Verificar permissões do volume `/mnt/media`

#### metadata_enricher
- **Problema:** Não enriquece metadados
- **Solução:** Verificar TMDB_API_KEY e GEMINI_API_KEY

#### normalization_worker
- **Problema:** Falha na normalização de vídeo
- **Solução:** Verificar se FFmpeg está disponível no container

#### scene_analyzer
- **Problema:** Análise de cenas falha
- **Solução:** Verificar logs de FFmpeg blackdetect

#### scheduler_ai
- **Problema:** Não gera EPG
- **Solução:** Verificar GEMINI_API_KEY e conectividade

## Diferenças da Versão Anterior

### ✅ Novo (Web Services)
- Todos os workers agora são web services com Flask
- Health endpoints para monitoramento
- Portas expostas para cada serviço
- Serviços externos (DB, Queue, Storage)

### ❌ Removido (Workers Locais)
- Serviços locais CockroachDB e RabbitMQ
- Workers sem interface web
- Dependências entre serviços locais

### 🔄 Mantido
- Funcionalidade idêntica dos workers
- Processamento em background
- Volumes de mídia compartilhados
- Nginx como proxy reverso