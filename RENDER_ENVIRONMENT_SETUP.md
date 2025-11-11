# Configuração de Variáveis de Ambiente no Render

## Problemas Identificados e Soluções

### 1. Media Manager - Erro de Permissão
**Problema**: `PermissionError: [Errno 13] Permission denied: '/mnt/media'`

**Solução**: As variáveis de ambiente no `render.yaml` já estão configuradas para usar `/tmp/staging` em vez de `/mnt/media`. O código agora tem fallback automático.

### 2. RabbitMQ - Erro de Autenticação
**Problema**: `ProbableAuthenticationError: ConnectionClosedByBroker: (403) 'ACCESS_REFUSED'`

**Solução**: Configure as seguintes variáveis no dashboard do Render:

## Variáveis de Ambiente Obrigatórias

### Para todos os serviços que usam RabbitMQ:
- `RABBITMQ_HOST` - URL do seu CloudAMQP (ex: `pelican.rmq.cloudamqp.com`)
- `RABBITMQ_USER` - Usuário do CloudAMQP
- `RABBITMQ_PASS` - Senha do CloudAMQP
- `RABBITMQ_VHOST` - Virtual host (geralmente o mesmo que o usuário)

### Para o banco de dados (todos os serviços):
- `DB_HOST` - Host do CockroachDB Cloud
- `DB_NAME` - Nome do banco
- `DB_USER` - Usuário do banco
- `DB_PASSWORD` - Senha do banco

### Para APIs (metadata-enricher e scheduler-ai):
- `TMDB_API_KEY` - Chave da API do TMDB
- `GEMINI_API_KEY` - Chave da API do Google Gemini

### Para storage (todos os serviços):
- `R2_ACCOUNT_ID` - ID da conta Cloudflare
- `R2_ACCESS_KEY_ID` - Chave de acesso R2
- `R2_SECRET_ACCESS_KEY` - Chave secreta R2
- `R2_BUCKET_NAME` - Nome do bucket R2
- `R2_ENDPOINT` - Endpoint do R2

## Como Configurar no Render

1. Acesse o dashboard do Render
2. Para cada serviço, vá em "Environment"
3. Adicione as variáveis necessárias
4. Clique em "Save Changes"
5. O serviço será automaticamente redeploy

## Testando o Sistema

### 1. Verificar Status dos Serviços
Acesse: `https://admin-ui-[seu-id].onrender.com/status`

### 2. Fazer Upload de Arquivo
Acesse: `https://admin-ui-[seu-id].onrender.com/`

### 3. Processar Itens Pendentes Manualmente
POST para: `https://admin-ui-[seu-id].onrender.com/process-pending`

## Troubleshooting

### Se o RabbitMQ ainda não conectar:
1. Verifique se as credenciais estão corretas
2. Confirme que o virtual host está correto
3. Teste a conexão usando um cliente AMQP

### Se o upload não funcionar:
1. Verifique os logs do media-manager
2. Confirme que o banco de dados está conectado
3. Teste o endpoint `/status` para ver o estado geral

### Se os workers não processarem:
1. Verifique se o RabbitMQ está conectado
2. Use o endpoint `/process-pending` para forçar processamento
3. Monitore os logs de cada serviço

## Logs Úteis

Para monitorar os logs no Render:
1. Acesse o dashboard do serviço
2. Vá na aba "Logs"
3. Procure por mensagens de erro ou sucesso

## Próximos Passos

1. Configure todas as variáveis de ambiente
2. Aguarde o redeploy automático
3. Teste o upload de um arquivo pequeno
4. Monitore os logs para confirmar que o pipeline está funcionando