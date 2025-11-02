# Check Point de Desenvolvimento

Este documento rastreia o progresso atual no roteiro de construção do software.

## Etapa Atual

**Etapa 2: O Diretor de Programação**

## Progresso

- [x] **scheduler_ai (Estrutura):** A estrutura inicial do microsserviço foi criada (`scheduler_ai/`, `requirements.txt`, `tests/`).
- [x] **scheduler_ai (Lógica de DB):** O serviço agora pode se conectar ao PostgreSQL, buscar as regras de agendamento da `channel_master_grid` e os itens de mídia da `media_items`.
- [x] **scheduler_ai (Motor de Agendamento):** O motor de agendamento (`engine.py`) foi criado e a primeira regra (`series_linear`) foi implementada. O serviço pode agora gerar entradas de EPG e salvar os resultados no banco de dados.
- [x] **admin_ui (Gerenciamento de Regras):** A interface de administração foi expandida com uma página (`/admin/rules`) que lista as regras de agendamento existentes no banco de dados.

---

## Histórico de Conclusões

### Etapa 1: O Pipeline de Ingestão
- [x] **PostgreSQL (Schema):** O schema do banco de dados foi definido em `database_schema.sql`.
- [x] **udev-ingest:** O script de ingestão de USB foi criado em `scripts/udev-ingest.sh`.
- [x] **admin_ui (Upload):** A interface de upload web foi criada no diretório `admin_ui`.
- [x] **media-manager:** O orquestrador do pipeline foi implementado em `media-manager/media_manager.py`.
- [x] **metadata-enricher:** O serviço de enriquecimento de metadados foi implementado em `metadata-enricher/enricher.py`.
- [x] **normalization-worker:** O worker de transcodificação foi implementado em `normalization-worker/worker.py`.
- [x] **scene-analyzer:** O worker de análise de cena foi implementado em `scene-analyzer/analyzer.py`.
- [x] **Integração do Pipeline:** Todos os serviços da Etapa 1 foram refatorados para se comunicarem de forma assíncrona usando RabbitMQ, tornando o pipeline totalmente funcional.


## Próximos Passos

1. Implementar na `admin_ui` a funcionalidade de Adicionar, Editar e Excluir regras de agendamento.
2. Implementar as regras de agendamento restantes (ex: `flexible_theme`) no `scheduler_ai`.
3. Expandir o motor de agendamento para gerar a programação para múltiplos dias.
