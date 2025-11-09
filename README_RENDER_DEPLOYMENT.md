# 🚀 Deploy no Render - Guia Rápido

## ⚡ Deploy em 5 Minutos

### 1. Pré-requisitos (Configure primeiro!)

**Serviços Externos Gratuitos:**
- 🗄️ **CockroachDB Cloud** → https://cockroachlabs.cloud/
- 🐰 **CloudAMQP** → https://cloudamqp.com/
- ☁️ **Cloudflare R2** → https://dash.cloudflare.com/
- 🎬 **TMDB API** → https://themoviedb.org/settings/api
- 🤖 **Google Gemini** → https://makersuite.google.com/

### 2. Deploy Automático

```bash
# 1. Fork este repositório no GitHub
# 2. Acesse https://render.com/
# 3. Clique "New" → "Blueprint"
# 4. Conecte seu repositório
# 5. Render detectará automaticamente o render.yaml
```

### 3. Configurar Variáveis de Ambiente

No dashboard do Render, configure as variáveis para cada serviço:

**Copie do seu .env:**
```bash
# Database
DB_HOST=your-cluster.cockroachlabs.cloud
DB_NAME=media_server
DB_USER=your-username
DB_PASSWORD=your-password

# Message Queue
RABBITMQ_HOST=your-instance.cloudamqp.com
RABBITMQ_USER=your-username
RABBITMQ_PASS=your-password

# Storage
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=your-bucket-name
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com

# APIs
TMDB_API_KEY=your-tmdb-api-key
GEMINI_API_KEY=your-gemini-api-key
```

### 4. Configurar UptimeRobot (Manter Serviços Vivos)

```bash
# Instalar dependências
pip install requests

# Configurar monitors
export UPTIMEROBOT_API_KEY=your-uptimerobot-api-key
python scripts/setup_uptimerobot.py
```

### 5. Verificar Deploy

```bash
# Testar todos os serviços
python scripts/verify_deployment.py
```

## 📋 Serviços Deployados

Após o deploy, você terá 7 serviços rodando:

| Serviço | Tipo | URL | Health Check |
|---------|------|-----|--------------|
| **frontend** | Static Site | `https://frontend-xxx.onrender.com` | - |
| **admin-ui** | Web Service | `https://admin-ui-xxx.onrender.com` | `/health` |
| **stream-api** | Web Service | `https://stream-api-xxx.onrender.com` | `/health` |
| **media-manager** | Web Service | `https://media-manager-xxx.onrender.com` | `/health` |
| **metadata-enricher** | Web Service | `https://metadata-enricher-xxx.onrender.com` | `/health` |
| **normalization-worker** | Web Service | `https://normalization-worker-xxx.onrender.com` | `/health` |
| **scene-analyzer** | Web Service | `https://scene-analyzer-xxx.onrender.com` | `/health` |
| **scheduler-ai** | Web Service | `https://scheduler-ai-xxx.onrender.com` | `/health` |

## 🎯 Arquitetura Final

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Admin UI      │    │   Stream API    │
│  (Static Site)  │    │  (Web Service)   │    │ (Web Service)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Media Manager   │    │Metadata Enricher │    │Normalization    │
│ (Web Service)   │◄──►│  (Web Service)   │◄──►│   Worker        │
└─────────────────┘    └──────────────────┘    │ (Web Service)   │
                                │               └─────────────────┘
                                ▼                        │
┌─────────────────┐    ┌──────────────────┐             ▼
│ Scheduler AI    │    │ Scene Analyzer   │    ┌─────────────────┐
│ (Web Service)   │◄───│  (Web Service)   │◄───│  CloudAMQP      │
└─────────────────┘    └──────────────────┘    │ (Message Queue) │
         │                       │              └─────────────────┘
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│ CockroachDB     │    │  Cloudflare R2   │
│   (Database)    │    │   (Storage)      │
└─────────────────┘    └──────────────────┘
```

## 💰 Custos (100% Gratuito!)

| Serviço | Plano Gratuito | Limite |
|---------|----------------|--------|
| **Render** | Free Tier | 750h/mês por serviço |
| **CockroachDB** | Serverless | 5GB storage |
| **CloudAMQP** | Little Lemur | 1M mensagens/mês |
| **Cloudflare R2** | Free Tier | 10GB storage |
| **TMDB API** | Free | 1000 requests/dia |
| **Google Gemini** | Free | 60 requests/min |
| **UptimeRobot** | Free | 50 monitors |

**Total: R$ 0,00/mês** 🎉

## 🔧 Troubleshooting

### Serviço não inicia
```bash
# 1. Verificar logs no Render dashboard
# 2. Confirmar variáveis de ambiente
# 3. Testar conectividade externa
curl https://your-service.onrender.com/health
```

### Workers não processam
```bash
# 1. Verificar UptimeRobot está pingando
# 2. Testar filas RabbitMQ
# 3. Verificar logs dos workers
```

### Upload/Streaming falha
```bash
# 1. Testar credenciais R2
# 2. Verificar configuração de bucket
# 3. Confirmar modo híbrido
```

## 📞 Suporte

- 📖 **Documentação completa:** `docs/RENDER_DEPLOYMENT_GUIDE.md`
- 🔧 **Scripts de automação:** `scripts/`
- 🧪 **Testes de integração:** `tests/`

---

**🎉 Parabéns! Seu sistema de mídia está rodando 100% gratuito na nuvem!**