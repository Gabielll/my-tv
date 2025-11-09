# Instruções de Deploy no Render - Passo a Passo

## 🚀 Deploy Automatizado com render.yaml

Este projeto inclui um arquivo `render.yaml` que automatiza o deployment de todos os serviços no Render.

### Pré-requisitos Obrigatórios

Antes de fazer o deploy, você DEVE configurar os seguintes serviços externos:

#### 1. CockroachDB Cloud (Database)
```bash
# Acesse: https://cockroachlabs.cloud/
# Crie cluster gratuito e anote:
DB_HOST=your-cluster.cockroachlabs.cloud
DB_PORT=26257
DB_NAME=media_server
DB_USER=your-username
DB_PASSWORD=your-password
```

#### 2. CloudAMQP (Message Queue)
```bash
# Acesse: https://cloudamqp.com/
# Crie instância "Little Lemur (Free)" e anote:
RABBITMQ_HOST=your-instance.cloudamqp.com
RABBITMQ_USER=your-username
RABBITMQ_PASS=your-password
```

#### 3. Cloudflare R2 (Storage)
```bash
# Acesse: https://dash.cloudflare.com/
# Crie bucket R2 e API token, anote:
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=your-bucket-name
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
```

#### 4. APIs Externas
```bash
# TMDB API: https://themoviedb.org/settings/api
TMDB_API_KEY=your-tmdb-api-key

# Google Gemini API: https://makersuite.google.com/
GEMINI_API_KEY=your-gemini-api-key
```

## 📋 Passos do Deploy

### 1. Preparar Repositório
```bash
# Fork este repositório no GitHub
# Clone seu fork localmente
git clone https://github.com/SEU-USERNAME/REPO-NAME.git
cd REPO-NAME

# Commit o render.yaml se necessário
git add render.yaml
git commit -m "Add Render deployment configuration"
git push origin main
```

### 2. Conectar ao Render
1. Acesse https://render.com/
2. Faça login/cadastro
3. Clique "New" → "Blueprint"
4. Conecte seu repositório GitHub
5. Selecione o repositório do projeto
6. Render detectará automaticamente o `render.yaml`

### 3. Configurar Variáveis de Ambiente
**IMPORTANTE:** As variáveis marcadas com `sync: false` devem ser configuradas manualmente no dashboard do Render.

#### Para cada serviço, configure:

**admin-ui:**
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT`
- `TMDB_API_KEY`

**stream-api:**
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT`

**media-manager:**
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `RABBITMQ_HOST`, `RABBITMQ_USER`, `RABBITMQ_PASS`

**metadata-enricher:**
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `RABBITMQ_HOST`, `RABBITMQ_USER`, `RABBITMQ_PASS`
- `TMDB_API_KEY`, `GEMINI_API_KEY`

**normalization-worker:**
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `RABBITMQ_HOST`, `RABBITMQ_USER`, `RABBITMQ_PASS`

**scene-analyzer:**
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `RABBITMQ_HOST`, `RABBITMQ_USER`, `RABBITMQ_PASS`

**scheduler-ai:**
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `RABBITMQ_HOST`, `RABBITMQ_USER`, `RABBITMQ_PASS`
- `GEMINI_API_KEY`

### 4. Executar Deploy
1. Clique "Apply" no Render
2. Aguarde todos os serviços serem criados
3. Verifique se todos os builds foram bem-sucedidos
4. Teste os health endpoints de cada serviço

## 🔍 Configuração do UptimeRobot

### Por que UptimeRobot?
O Render free tier coloca serviços para "dormir" após 15 minutos de inatividade. O UptimeRobot pinga os serviços a cada 5 minutos, mantendo-os sempre ativos.

### Passos de Configuração

#### 1. Criar Conta UptimeRobot
1. Acesse https://uptimerobot.com/
2. Crie conta gratuita
3. Confirme email

#### 2. Adicionar Monitors
Para cada serviço convertido, adicione um monitor HTTP:

**Monitor 1: admin-ui**
- Monitor Type: HTTP(s)
- Friendly Name: `Media Server - Admin UI`
- URL: `https://admin-ui-XXXXX.onrender.com/health`
- Monitoring Interval: 5 minutes

**Monitor 2: media-manager**
- Monitor Type: HTTP(s)
- Friendly Name: `Media Server - Media Manager`
- URL: `https://media-manager-XXXXX.onrender.com/health`
- Monitoring Interval: 5 minutes

**Monitor 3: metadata-enricher**
- Monitor Type: HTTP(s)
- Friendly Name: `Media Server - Metadata Enricher`
- URL: `https://metadata-enricher-XXXXX.onrender.com/health`
- Monitoring Interval: 5 minutes

**Monitor 4: normalization-worker**
- Monitor Type: HTTP(s)
- Friendly Name: `Media Server - Normalization Worker`
- URL: `https://normalization-worker-XXXXX.onrender.com/health`
- Monitoring Interval: 5 minutes

**Monitor 5: scene-analyzer**
- Monitor Type: HTTP(s)
- Friendly Name: `Media Server - Scene Analyzer`
- URL: `https://scene-analyzer-XXXXX.onrender.com/health`
- Monitoring Interval: 5 minutes

**Monitor 6: scheduler-ai**
- Monitor Type: HTTP(s)
- Friendly Name: `Media Server - Scheduler AI`
- URL: `https://scheduler-ai-XXXXX.onrender.com/health`
- Monitoring Interval: 5 minutes

**Monitor 7: stream-api**
- Monitor Type: HTTP(s)
- Friendly Name: `Media Server - Stream API`
- URL: `https://stream-api-XXXXX.onrender.com/health`
- Monitoring Interval: 5 minutes

#### 3. Configurar Alertas (Opcional)
1. Vá em "Alert Contacts"
2. Adicione seu email
3. Configure para receber alertas quando serviços ficarem offline

## ✅ Verificação do Deploy

### 1. Testar Health Endpoints
```bash
# Teste cada serviço (substitua XXXXX pelo ID real)
curl https://admin-ui-XXXXX.onrender.com/health
curl https://media-manager-XXXXX.onrender.com/health
curl https://metadata-enricher-XXXXX.onrender.com/health
curl https://normalization-worker-XXXXX.onrender.com/health
curl https://scene-analyzer-XXXXX.onrender.com/health
curl https://scheduler-ai-XXXXX.onrender.com/health
curl https://stream-api-XXXXX.onrender.com/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "service": "service-name",
  "version": "1.0.0",
  "uptime": 123.45,
  "dependencies": {
    "database": "healthy",
    "rabbitmq": "healthy"
  }
}
```

### 2. Testar Funcionalidade Completa
1. **Upload de arquivo:** Acesse admin-ui e faça upload de um vídeo
2. **Processamento:** Verifique se o arquivo aparece no banco de dados
3. **Streaming:** Teste se o vídeo pode ser reproduzido via stream-api
4. **Workers:** Verifique se os workers estão processando filas

### 3. Monitorar Logs
No dashboard do Render, verifique os logs de cada serviço para:
- Erros de conexão com serviços externos
- Problemas de autenticação
- Falhas de processamento
- Performance issues

## 🚨 Troubleshooting

### Serviço não inicia
**Sintomas:** Build falha ou serviço não responde
**Soluções:**
1. Verificar logs no dashboard Render
2. Confirmar todas as variáveis de ambiente estão configuradas
3. Testar conectividade com serviços externos localmente

### Health endpoint retorna 503
**Sintomas:** UptimeRobot reporta serviço offline
**Soluções:**
1. Verificar se database/rabbitmq estão acessíveis
2. Confirmar credenciais estão corretas
3. Verificar se serviço não está em sleep mode

### Workers não processam
**Sintomas:** Arquivos ficam pendentes no banco
**Soluções:**
1. Verificar se RabbitMQ está funcionando
2. Confirmar workers estão consumindo filas
3. Verificar se UptimeRobot está pingando workers

### Problemas de storage
**Sintomas:** Upload falha ou streaming não funciona
**Soluções:**
1. Testar credenciais R2 localmente
2. Verificar configuração de bucket
3. Confirmar modo híbrido está funcionando

## 📊 Monitoramento de Recursos

### Limites do Free Tier
- **Render:** 750 horas/mês por serviço (7 serviços = suficiente)
- **CockroachDB:** 5GB storage, 1 conexão simultânea
- **CloudAMQP:** 1M mensagens/mês, 20 conexões
- **Cloudflare R2:** 10GB storage, 1M Class A ops/mês
- **TMDB API:** 1000 requests/dia
- **Gemini API:** 60 requests/minuto

### Alertas Recomendados
Configure alertas para:
- Serviços offline (UptimeRobot)
- Uso de storage próximo do limite (R2, CockroachDB)
- Rate limits atingidos (APIs)
- Filas com muitas mensagens pendentes (CloudAMQP)

## 🎯 URLs Finais

Após o deploy bem-sucedido, você terá:

- **Frontend:** `https://frontend-XXXXX.onrender.com`
- **Admin UI:** `https://admin-ui-XXXXX.onrender.com`
- **Stream API:** `https://stream-api-XXXXX.onrender.com`
- **Workers:** Rodando em background, monitorados via health endpoints

**Parabéns! Seu sistema de mídia está rodando 100% gratuito na nuvem! 🎉**