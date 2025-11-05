# Guia de Implantação no Render

Este guia detalha o processo de implantação do projeto de servidor de mídia na plataforma Render, utilizando o plano gratuito. A implantação será feita usando Docker, com os serviços configurados para comunicação interna e conexão a um banco de dados CockroachDB externo.

## 1. Visão Geral da Implantação no Render

O Render oferece um plano gratuito que permite a criação de "Web Services" e "Static Sites". Como nosso projeto é baseado em microsserviços, vamos precisar criar vários serviços no Render. A comunicação entre eles será feita através da rede interna do Render.

**Serviços a serem criados:**

- **Web Services:**
    - `admin-ui`: A interface de administração para upload de mídia.
    - `stream-api`: O serviço que gerencia os streams de vídeo on-demand.
    - `nginx`: O servidor web que atua como proxy reverso e serve o frontend estático.
- **Background Workers (Trabalhadores em Segundo Plano):**
    - `media-manager`: Orquestra o pipeline de ingestão de mídia.
    - `metadata-enricher`: Busca metadados para a mídia.
    - `normalization-worker`: Padroniza os arquivos de vídeo.
    - `scene-analyzer`: Analisa os vídeos em busca de intervalos.
    - `scheduler-ai`: Cria a programação dos canais.

**Banco de Dados e Fila de Mensagens:**

- **Banco de Dados:** Utilizaremos um banco de dados CockroachDB externo. Você pode criar uma conta gratuita no [CockroachDB Cloud](https://www.cockroachlabs.com/cloud/).
- **Fila de Mensagens:** Utilizaremos o CloudAMQP para o RabbitMQ. Você pode criar uma conta gratuita no [CloudAMQP](https://www.cloudamqp.com/).

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
