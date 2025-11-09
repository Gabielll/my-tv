# 🚀 Guia de Deploy no Render - Arquitetura Convertida

**⚠️ NOTA:** Este guia está obsoleto. Para deployment atual, use:
- **[README_RENDER_DEPLOYMENT.md](README_RENDER_DEPLOYMENT.md)** - Guia rápido de 5 minutos
- **[RENDER_DEPLOYMENT_INSTRUCTIONS.md](RENDER_DEPLOYMENT_INSTRUCTIONS.md)** - Instruções detalhadas
- **[docs/RENDER_DEPLOYMENT_GUIDE.md](docs/RENDER_DEPLOYMENT_GUIDE.md)** - Guia completo

---

## 📋 Nova Arquitetura (Todos Web Services)

O projeto foi convertido para usar **apenas Web Services** no Render, eliminando a necessidade de workers em background. Todos os serviços agora têm endpoints HTTP e health checks.

**Serviços Deployados (8 Web Services):**

- **Frontend Services:**
    - `frontend`: Site estático com player web
    - `admin-ui`: Interface de administração para upload de mídia
    - `stream-api`: Serviço que gerencia streams de vídeo on-demand

- **Processing Services (Convertidos de Workers):**
    - `media-manager`: Orquestra pipeline de ingestão (agora web service)
    - `metadata-enricher`: Busca metadados TMDB + Gemini AI (agora web service)
    - `normalization-worker`: Padroniza arquivos de vídeo (agora web service)
    - `scene-analyzer`: Analisa vídeos para intervalos (agora web service)
    - `scheduler-ai`: Cria programação com IA (agora web service)

**Serviços Externos (100% Gratuitos):**

- **Banco de Dados:** CockroachDB Cloud (5GB gratuitos)
- **Fila de Mensagens:** CloudAMQP (1M mensagens/mês gratuitas)
- **Storage:** Cloudflare R2 (10GB gratuitos)
- **APIs:** TMDB (1000 req/dia) + Google Gemini (60 req/min)
- **Monitoramento:** UptimeRobot (50 monitors gratuitos)

## 2. Passos para a Implantação

### Passo 1: Preparar os Serviços Externos

#### a) Banco de Dados CockroachDB

1.  **Crie uma conta no CockroachDB Cloud:** Acesse o site e crie uma conta gratuita.
2.  **Crie um cluster:** Siga as instruções para criar um novo cluster.
3.  **Obtenha a string de conexão:** Após a criação do cluster, vá para a seção "Connection info" e copie a string de conexão. Ela será algo como:
    ```
    postgresql://user:password@host:port/database?sslmode=verify-full
    ```
4.  **Execute o schema do banco de dados:** Use a string de conexão para se conectar ao banco de dados e execute o conteúdo do arquivo `database_schema_cockroach.sql` para criar as tabelas necessárias.

#### b) Fila de Mensagens RabbitMQ (CloudAMQP)

1.  **Crie uma conta no CloudAMQP:** Acesse o site e crie uma conta gratuita.
2.  **Crie uma nova instância:** Escolha o plano gratuito "Little Lemur".
3.  **Obtenha os detalhes de conexão:** Após a criação da instância, você terá acesso ao `URL` de conexão, que contém o nome de usuário, senha e host.
    - **Exemplo de URL:** `amqps://user:password@long-uuid.rmq.cloudamqp.com/vhost`

### Passo 2: Configurar o Repositório no Render

1.  **Crie uma conta no Render:** Se você ainda não tiver uma, crie uma conta no [Render](https://render.com/).
2.  **Conecte sua conta do GitHub ou GitLab:** Conecte sua conta para que o Render possa acessar seu repositório.
3.  **Crie um novo "Blueprint":** No dashboard do Render, clique em "New" e selecione "Blueprint".
4.  **Selecione o repositório:** Escolha o repositório do projeto.
5.  **Configure os serviços:** O Render detectará o arquivo `render.yaml` e listará os serviços a serem criados.

### Passo 3: Configurar as Variáveis de Ambiente

O `render.yaml` usa placeholders para as variáveis de ambiente. Você precisará definir os valores para esses placeholders no dashboard do Render.

1.  **Vá para a seção "Environment":** Para cada serviço, vá para a aba "Environment".
2.  **Adicione as variáveis de ambiente:**
    - `DB_HOST`: O host do seu cluster CockroachDB.
    - `DB_PORT`: A porta do seu cluster (geralmente 26257).
    - `DB_NAME`: O nome do seu banco de dados.
    - `DB_USER`: O seu nome de usuário do CockroachDB.
    - `DB_PASSWORD`: A sua senha do CockroachDB.
    - `RABBITMQ_HOST`: O host da sua instância CloudAMQP.
    - `RABBITMQ_USER`: O seu nome de usuário do CloudAMQP.
    - `RABBITMQ_PASS`: A sua senha do CloudAMQP.

### Passo 4: Implantar os Serviços

1.  **Clique em "Create New Services":** Após configurar as variáveis de ambiente, clique em "Create New Services" para iniciar a implantação.
2.  **Aguarde a conclusão:** O Render começará a construir e implantar cada um dos serviços. Você pode acompanhar o progresso na aba "Events".

## 3. Acessando a Aplicação

- **URL Pública:** O serviço `nginx` terá uma URL pública (ex: `https://meu-projeto.onrender.com`). Acesse essa URL para ver o player web.
- **Admin UI:** O serviço `admin-ui` também terá uma URL pública (ex: `https://admin-ui-meu-projeto.onrender.com`). Use esta URL para fazer o upload de novas mídias.

## 4. Limitações do Plano Gratuito do Render

- **Serviços podem "dormir":** Os serviços no plano gratuito podem "dormir" após um período de inatividade. A primeira requisição a um serviço "adormecido" pode levar alguns segundos para ser respondida.
- **Recursos limitados:** Os recursos de CPU e memória são limitados, o que pode afetar o desempenho da transcodificação de vídeo.
- **Armazenamento efêmero:** O armazenamento de arquivos é efêmero, o que significa que os arquivos de mídia enviados para a `admin-ui` serão perdidos quando o serviço for reiniciado. Para uma solução de produção, você precisaria usar um serviço de armazenamento persistente, como o Amazon S3.
