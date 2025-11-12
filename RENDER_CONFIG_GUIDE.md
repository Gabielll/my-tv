# Guia de Configuração das Variáveis de Ambiente no Render

## 📋 Variáveis de Ambiente por Serviço

### 🗄️ **Database (CockroachDB) - Para TODOS os serviços**
```
DB_HOST=my-tv-media-files-10169.jxf.gcp-southamerica-east1.cockroachlabs.cloud
DB_PORT=26257
DB_NAME=defaultdb
DB_USER=my-tv
DB_PASSWORD=k0evQuExK_x1nthcvmnRYA
```

### 🐰 **RabbitMQ (CloudAMQP) - Para serviços que usam filas**
```
RABBITMQ_HOST=jaragua.lmq.cloudamqp.com
RABBITMQ_PORT=5672
RABBITMQ_USER=bgepvloi
RABBITMQ_PASS=alfnh4BZ5O6TJCrrbfDXtrLLgifzIh01
RABBITMQ_VHOST=bgepvloi
```

### ☁️ **Cloudflare R2 Storage - Para TODOS os serviços**
```
STORAGE_MODE=hybrid
R2_ACCOUNT_ID=20ca34c5d74a7965937066f5af6fb7c4
R2_ACCESS_KEY_ID=f4036dba1dfc09a756c1548c22e15ffc
R2_SECRET_ACCESS_KEY=547db3297af1325758db0afee606f218cb216e4628d5f124d93433ae38dee7c1
R2_BUCKET_NAME=my-tv-media-files
R2_ENDPOINT=https://20ca34c5d74a7965937066f5af6fb7c4.r2.cloudflarestorage.com
```

### 🎬 **APIs Externas**
```
TMDB_API_KEY=68029a904a7c65c638854ebf492c4270
GEMINI_API_KEY=AIzaSyBk-d-d2rqvfidNWO-HCJG6e_QiTs4ymP0
```

## 🎯 **Configuração por Serviço no Render**

### 1. **admin-ui**
- Database: ✅ Todas as variáveis DB_*
- Storage: ✅ Todas as variáveis R2_*
- RabbitMQ: ❌ Não precisa (não usa filas)
- APIs: ❌ Não precisa

### 2. **media-manager**
- Database: ✅ Todas as variáveis DB_*
- Storage: ✅ Todas as variáveis R2_*
- RabbitMQ: ✅ Todas as variáveis RABBITMQ_*
- APIs: ❌ Não precisa

### 3. **metadata-enricher**
- Database: ✅ Todas as variáveis DB_*
- Storage: ✅ Todas as variáveis R2_*
- RabbitMQ: ✅ Todas as variáveis RABBITMQ_*
- APIs: ✅ TMDB_API_KEY e GEMINI_API_KEY

### 4. **normalization-worker**
- Database: ✅ Todas as variáveis DB_*
- Storage: ✅ Todas as variáveis R2_*
- RabbitMQ: ✅ Todas as variáveis RABBITMQ_*
- APIs: ❌ Não precisa

### 5. **scene-analyzer**
- Database: ✅ Todas as variáveis DB_*
- Storage: ✅ Todas as variáveis R2_*
- RabbitMQ: ✅ Todas as variáveis RABBITMQ_*
- APIs: ❌ Não precisa

### 6. **scheduler-ai**
- Database: ✅ Todas as variáveis DB_*
- Storage: ✅ Todas as variáveis R2_*
- RabbitMQ: ✅ Todas as variáveis RABBITMQ_*
- APIs: ✅ GEMINI_API_KEY

### 7. **stream-api**
- Database: ✅ Todas as variáveis DB_*
- Storage: ✅ Todas as variáveis R2_*
- RabbitMQ: ❌ Não precisa
- APIs: ❌ Não precisa

## 🚀 **Como Configurar no Render Dashboard**

### Método 1: Individual (Recomendado para começar)

1. **Acesse cada serviço no Render Dashboard**
2. **Vá na aba "Environment"**
3. **Adicione as variáveis uma por uma**
4. **Clique "Save Changes"**

### Método 2: Environment Groups (Avançado)

1. **Crie 4 grupos de ambiente:**
   - `database-config`
   - `rabbitmq-config` 
   - `storage-config`
   - `apis-config`

2. **Associe os grupos aos serviços apropriados**

## ✅ **Ordem de Configuração Recomendada**

1. **Comece com admin-ui** (mais simples, só DB + Storage)
2. **Teste o upload básico**
3. **Configure media-manager** (adiciona RabbitMQ)
4. **Configure metadata-enricher** (adiciona APIs)
5. **Configure os demais workers**

## 🧪 **Como Testar**

### 1. **Após configurar admin-ui:**
```
https://admin-ui-[seu-id].onrender.com/status
```

### 2. **Após configurar media-manager:**
```
https://media-manager-[seu-id].onrender.com/health
```

### 3. **Teste completo:**
- Upload de arquivo via admin-ui
- Verificar processamento automático

## 🔧 **Troubleshooting**

### Se der erro de conexão DB:
- Verifique se o certificado SSL está sendo baixado corretamente
- Confirme que `sslmode=verify-full` está configurado

### Se RabbitMQ não conectar:
- Confirme que RABBITMQ_VHOST = RABBITMQ_USER (bgepvloi)
- Verifique se a senha está correta

### Se storage não funcionar:
- Confirme que o bucket `my-tv-media-files` existe no R2
- Verifique as permissões da chave de acesso

## 📝 **Próximos Passos**

1. Configure as variáveis no admin-ui primeiro
2. Teste o endpoint `/status`
3. Faça um upload de teste
4. Configure os demais serviços gradualmente
5. Monitore os logs para identificar problemas

---

**💡 Dica**: Comece configurando apenas o admin-ui e media-manager para testar o upload básico, depois adicione os outros serviços gradualmente.