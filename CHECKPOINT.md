# Check Point de Desenvolvimento

Este documento rastreia o progresso atual no roteiro de construção do software.

## Etapa Atual

**Etapa 3: O Consumo On-Demand (Concluída)**

## Progresso
- [x] **stream-api (Estrutura):** Criar a estrutura inicial do microsserviço `stream-api` para lidar com as solicitações de streaming.
- [x] **FFmpeg (Integração):** Integrar o `ffmpeg` para iniciar dinamicamente os processos de transcodificação e streaming.
- [x] **Frontend (Player):** Desenvolver um player de vídeo no frontend para consumir o stream HLS/DASH.
- [x] **Nginx (Configuração):** Configurar o Nginx para orquestrar o tráfego entre o player, a API e os arquivos de stream.

---

## Histórico de Conclusões

### Etapa 2: O Diretor de Programação
- [x] **scheduler_ai (Regras Adicionais):** A regra `flexible_theme` foi implementada no motor de agendamento.
- [x] **scheduler_ai (Expansão do Motor):** O motor de agendamento foi expandido para gerar programação para múltiplos dias (7 dias).
- [x] **admin-ui (Gerenciamento de Regras):** A interface básica para visualização das regras de agendamento foi criada no `admin-ui`.

### Etapa 1: O Pipeline de Ingestão
- [x] **PostgreSQL (Schema):** O schema do banco de dados foi definido em `database_schema.sql`.
- [x] **udev-ingest:** O script de ingestão de USB foi criado em `scripts/udev-ingest.sh`.
- [x] **admin-ui (Upload):** A interface de upload web foi criada no diretório `admin-ui`.
- [x] **media-manager:** O orquestrador do pipeline foi implementado em `media-manager/media_manager.py`.
- [x] **metadata-enricher:** O serviço de enriquecimento de metadados foi implementado em `metadata-enricher/enricher.py`.
- [x] **normalization-worker:** O worker de transcodificação foi implementado em `normalization-worker/worker.py`.
- [x] **scene-analyzer:** O worker de análise de cena foi implementado em `scene-analyzer/analyzer.py`.
- [x] **Integração do Pipeline:** Todos os serviços da Etapa 1 foram refatorados para se comunicarem de forma assíncrona usando RabbitMQ, tornando o pipeline totalmente funcional.

## Próximos Passos

O desenvolvimento principal está concluído. Os próximos passos podem incluir a adição de mais regras de agendamento, melhorias na interface do usuário ou a implementação de monitoramento.

---

## Convenções de Código

- **Nomenclatura de Diretórios de Microsserviços:** Para garantir que os microsserviços Python possam ser importados como pacotes (especialmente para fins de teste), todos os diretórios de serviço devem usar o formato `snake_case` (ex: `media_manager`) em vez de `kebab-case` (ex: `media-manager`). Esta refatoração foi aplicada a todos os serviços existentes.
