# Check Point de Desenvolvimento

Este documento rastreia o progresso atual no roteiro de construção do software.

## Etapa Atual

**Etapa 1: O Pipeline de Ingestão**

## Progresso

- [x] **PostgreSQL (Schema):** O schema do banco de dados foi definido em `database_schema.sql`.
- [x] **udev-ingest:** O script de ingestão de USB foi criado em `scripts/udev-ingest.sh`.
- [x] **admin-ui (Upload):** A interface de upload web foi criada no diretório `admin-ui`.
- [x] **media-manager:** O orquestrador do pipeline foi implementado em `media-manager/media_manager.py`.
- [x] **metadata-enricher:** O serviço de enriquecimento de metadados foi implementado em `metadata-enricher/enricher.py`.
- [x] **normalization-worker:** O worker de transcodificação foi implementado em `normalization-worker/worker.py`.
- [x] **scene-analyzer:** O worker de análise de cena foi implementado em `scene-analyzer/analyzer.py`.
- [x] **Integração do Pipeline:** Todos os serviços da Etapa 1 foram refatorados para se comunicarem de forma assíncrona usando RabbitMQ, tornando o pipeline totalmente funcional.

## Próximos Passos

1. Iniciar a **Etapa 2: O Diretor de Programação**.
2. Implementar a interface no `admin-ui` para gerenciar as regras na `channel_master_grid`.
3. Implementar o serviço `scheduler-ai` para gerar o EPG.
