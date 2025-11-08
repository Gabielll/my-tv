# Guia de Implantação no Render (Nível Gratuito)

Este guia detalha como implantar a aplicação de microsserviços no Render, utilizando o nível gratuito.

## Visão Geral

A arquitetura original foi projetada para um ambiente Docker com serviços dedicados. No entanto, o nível gratuito do Render possui algumas limitações:
- **Não há Workers:** Não podemos usar serviços do tipo "worker". Todos os nossos serviços de backend serão executados como "Web Services".
- **Sem Banco de Dados ou Filas:** Não há serviços gerenciados de banco de dados (como PostgreSQL) ou filas de mensagens (como RabbitMQ) no nível gratuito. Precisaremos usar serviços externos.

Para contornar essas limitações, usaremos:
- **CockroachDB (Free Tier):** Para nosso banco de dados.
- **CloudAMQP (Free Tier):** Para nossa fila de mensagens.

## Pré-requisitos

Antes de começar, você precisará de:
1. Uma conta no [Render](https://render.com/).
2. Uma conta no [CockroachDB Cloud](https://www.cockroachlabs.com/cockroachdb/).
3. Uma conta no [CloudAMQP](https://www.cloudamqp.com/).

## Passo a Passo da Implantação

### 1. Configure os Serviços Externos

#### a. CockroachDB

1. Crie um cluster gratuito no CockroachDB Cloud.
2. Na aba "Connection info", selecione "Connection string" e anote os detalhes (usuário, senha, host, porta, nome do banco de dados).

#### b. CloudAMQP

1. Crie uma instância gratuita "Little Lemur" no CloudAMQP.
2. No painel da instância, anote os detalhes da conexão (AMQP URL).

### 2. Implante os Serviços no Render

No painel do Render, crie os seguintes serviços:

#### a. Serviços de Backend (Web Services)

Para cada um dos serviços de backend abaixo, crie um novo "Web Service" no Render e configure-o da seguinte forma:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** O comando de inicialização específico de cada serviço (veja a tabela abaixo).

| Serviço               | Nome no Render        | Comando de Inicialização                |
| --------------------- | --------------------- | --------------------------------------- |
| `admin_ui`            | `admin-ui`            | `gunicorn --bind 0.0.0.0:$PORT admin_ui.app:app` |
| `stream_api`          | `stream-api`          | `gunicorn --bind 0.0.0.0:$PORT stream_api.main:app` |
| `media_manager`       | `media-manager`       | `python media_manager/media_manager.py`       |
| `metadata_enricher`   | `metadata-enricher`   | `python metadata_enricher/metadata_enricher.py` |
| `normalization_worker`| `normalization-worker`| `python normalization_worker/normalization_worker.py` |
| `scene_analyzer`      | `scene-analyzer`      | `python scene_analyzer/scene_analyzer.py`     |
| `scheduler_ai`        | `scheduler-ai`        | `python scheduler_ai/scheduler.py`        |

**Variáveis de Ambiente:**

Para cada um desses serviços, configure as seguintes variáveis de ambiente no Render, usando os valores que você anotou do CockroachDB e CloudAMQP:
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `RABBITMQ_HOST`
- `RABBITMQ_USER`
- `RABBITMQ_PASS`

#### b. Frontend (Static Site)

1. Crie um novo "Static Site" no Render.
2. Aponte para o seu repositório Git.
3. Configure as seguintes opções:
   - **Publish Directory:** `frontend`
   - **Build Command:** (deixe em branco)

### 3. Conecte o Nginx (Opcional, mas Recomendado)

Se você estiver usando o Nginx como um proxy reverso, precisará implantá-lo como um Web Service e configurar as regras de proxy para apontar para os seus outros Web Services. No entanto, para uma implantação mais simples no nível gratuito, você pode acessar os serviços diretamente por suas URLs do Render.

## Nomes dos Serviços no Render

Para manter a consistência, use os seguintes nomes ao criar seus serviços no Render:
- `admin-ui`
- `stream-api`
- `media-manager`
- `metadata-enricher`
- `normalization-worker`
- `scene-analyzer`
- `scheduler-ai`
- `frontend` (Static Site)
