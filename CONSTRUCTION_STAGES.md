# Etapas de Construção do Software

Este documento detalha as três principais etapas para a construção do servidor de mídia, conforme descrito no `ARCHITECTURE.md`.

## Etapa 1: O Pipeline de Ingestão (A "Fábrica de Conteúdo")

**Objetivo:** Implementar o pipeline assíncrono completo que transforma arquivos de mídia brutos (de qualquer fonte) em ativos 100% processados, catalogados e analisados dentro do Banco de Dados Central.

**Componentes-Chave:**
- PostgreSQL (Definição de Schema)
- `udev-ingest` (Absorvedor Offline)
- `admin-ui` (Portal de Ingestão Web)
- `media-manager` (O "Bibliotecário")
- `metadata-enricher` (O "Curador")
- `normalization-worker` (O "Estagiário")
- `scene-analyzer` (O "Editor")

**Critério de Conclusão:**
Um arquivo de vídeo colocado no USB ou enviado via Web UI resulta automaticamente em:
- Uma entrada completa na tabela `media_items`.
- Entradas correspondentes na tabela `cue_points`.
- Um arquivo de vídeo normalizado em `/mnt/media/normalized/`.
- O arquivo original movido para a biblioteca final.

## Etapa 2: O Diretor de Programação (O "Cérebro Criativo")

**Objetivo:** Implementar o microsserviço que consome os ativos catalogados na Etapa 1 e aplica a lógica de negócios para gerar la grade de programação virtual (EPG).

**Componentes-Chave:**
- `scheduler-ai` (O "Diretor")
- `admin-ui` (Expansão: "Sala de Direção")

**Critério de Conclusão:**
Após a execução do `scheduler-ai`, a tabela `epg_virtual` está 100% populada com a programação futura, respeitando as regras definidas na `channel_master_grid`.

## Etapa 3: Consumo On-Demand e Acesso (O "Player")

**Objetivo:** Implementar o "front-end" de consumo e o "cérebro" on-demand que inicia os streams de forma dinâmica, permitindo ao usuário assistir à programação criada na Etapa 2.

**Componentes-Chave:**
- `stream-api` (O "Cérebro On-Demand")
- `nginx` (O "Porteiro")
- Player Web (Cliente HTML/JS)

**Critério de Conclusão:**
A aplicação está 100% funcional. O usuário pode assistir ao EPG da Etapa 2, com streams (`ffmpeg`) iniciados e encerrados dinamicamente.
