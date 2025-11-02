# ARCHITECTURE.md

## 1. Visão Geral do Projeto

O objetivo é construir um servidor de mídia privado e eficiente, capaz de simular canais de TV 24/7.
O conceito central é a Eficiência On-Demand. O sistema não executará streams de vídeo 24/7. Em vez disso, ele é dividido em duas fases operacionais:
- **Fase Offline (Agendamento):** Um "Diretor" (scheduler-ai) gera uma programação virtual (EPG) e a salva no banco de dados. O servidor permanece 100% ocioso.
- **Fase Online (Consumo):** Quando o primeiro espectador "sintoniza" um canal, um "Cérebro On-Demand" (stream-api) consulta o EPG, calcula o ponto exato da programação e inicia um processo ffmpeg dinamicamente a partir desse ponto.

Quando o último espectador desconecta, o processo ffmpeg é encerrado ("Reaper"), e o servidor retorna a 0% de uso de CPU.

## 2. Os Componentes (Atores da Arquitetura)

O sistema é composto pelos seguintes microsserviços e sistemas de armazenamento:

### Servidores / Aplicações

- **nginx (O Porteiro):** O único serviço exposto à rede (LAN/WAN). Recebe 100% do tráfego. Atua como proxy reverso para as APIs e servidor de arquivos estáticos (HLS).
- **admin-ui (Servidor Web):** O portal de administração (/admin) para upload de mídia via web e edição manual de metadados.
- **udev-ingest (Script Linux):** O "Absorvedor" offline. Detecta a conexão de dispositivos USB e copia automaticamente o conteúdo.
- **media-manager (Serviço - O "Bibliotecário"):** Monitora a pasta de "staging" e orquestra o pipeline de ingestão (chama o Curador, enfileira jobs).
- **metadata-enricher (Serviço/IA - O "Curador"):** Identifica mídia (séries/filmes) analisando nomes de arquivo/pasta, busca metadados ricos (sinopse, tags) em APIs externas (ex: TMDB) e preenche o BD.
- **normalization-worker (Serviço - O "Estagiário"):** Um worker (via Fila) que recebe jobs de transcodificação. Converte vídeos para um formato padrão (H.264/AAC) para garantir compatibilidade.
- **scene-analyzer (Serviço - O "Editor"):** Um worker (via Fila) que recebe jobs de análise. Executa ffmpeg (ex: blackdetect) para encontrar "breaks" comerciais e salva os cue_points no BD.
- **scheduler-ai (Cron/Serviço - O "Diretor"):** Roda periodicamente (ex: 4h da manhã). Lê as regras de negócio (channel_master_grid) e os ativos (media_items) para gerar a programação futura (epg_virtual).
- **stream-api (Servidor Web - O "Cérebro On-Demand"):** Inicia e para os processos ffmpeg quando um usuário "sintoniza" ou "dessintoniza". Calcula o offset de início do stream.
- **Player Web (Cliente):** O aplicativo HTML/JS (rodando no navegador do usuário) que reproduz o stream HLS e envia "heartbeats" para a stream-api.

### Armazenamento / Mensageria

- **PostgreSQL (O "Cérebro Central"):** Armazena todo o estado do aplicativo:
    - `media_items`: Metadados, last_played_time, play_count.
    - `cue_points`: Os "breaks" detectados.
    - `channel_master_grid`: As regras de programação (configuradas manualmente).
    - `epg_virtual`: A programação futura (gerada pelo scheduler-ai).
- **RabbitMQ (Fila/Opcional):** (Recomendado) Desacopla o media-manager dos workers (Normalização e Análise).

## 3. Fluxo 1: Pipeline de Ingestão (Da Mídia ao BD)

Este fluxo é assíncrono e transforma um arquivo bruto em um ativo catalogado.
**Entrada (Duas Portas):**
- **Porta A (Offline):** Usuário pluga um Pendrive USB. O `udev-ingest` (Script) copia o arquivo para `/mnt/media/staging_ingest/`.
- **Porta B (Online):** Usuário acessa o `admin-ui` (/admin) e faz Upload. O servidor web salva o arquivo em `/mnt/media/staging_ingest/`.

**Orquestração (O "Bibliotecário"):**
- O `media-manager` detecta um novo arquivo em `/staging_ingest/`.

**Curadoria (O "Curador"):**
- O `media-manager` chama o `metadata-enricher`.
- O `metadata-enricher` analisa o nome/pasta (ex: "Power Rangers S01E01"), chama a API do TMDB e salva os metadados ricos no PostgreSQL (tabela `media_items`).
- Se falhar (internet offline ou comercial), marca como `status: 'needs_review'`.

**Processamento (Fila):**
- O `media-manager` publica um "Job de Normalização" no RabbitMQ.
- O `normalization-worker` ("Estagiário") recebe o job, executa ffmpeg (transcodificação) e salva o novo arquivo em `/mnt/media/normalized/`.
- Ao terminar, o `normalization-worker` publica um "Job de Análise" no RabbitMQ.
- O `scene-analyzer` ("Editor") recebe o job, executa ffmpeg (blackdetect) no arquivo normalizado e salva os `cue_points` no PostgreSQL.

**Conclusão:**
- O `media-manager`, ao ver que todos os jobs terminaram, move o arquivo original de `/staging_ingest/` para sua pasta final (ex: `/mnt/media/series/Power Rangers/`).
**Resultado do Fluxo 1:** O arquivo está 100% processado, catalogado, analisado e pronto para o "Diretor".

## 4. Fluxo 2: Programação e Stream (Do BD à Tela)

Este fluxo tem duas partes: o agendamento (feito 1x por dia) e o streaming (feito sob demanda).

### Parte A: O Agendamento (Periódico/Offline)

- **O "Diretor" Acorda:** Um Cron executa o `scheduler-ai` (ex: 4h da manhã).
- **Leitura das Regras:** O `scheduler-ai` lê a `channel_master_grid` do PostgreSQL (Quais são meus blocos âncora? Quais as regras de rotação?).
- **Leitura dos Ativos:** O `scheduler-ai` lê `media_items` e `cue_points` (Quais episódios eu tenho? Onde estão os breaks? O que tocou recentemente?).
- **Criação do Plano:** O "Diretor" aplica as regras (Temáticas, de Rotação, de Continuidade) e gera a grade de programação completa para os próximos dias.
- **Salvamento do Plano:** O `scheduler-ai` escreve essa grade final na tabela `epg_virtual` do PostgreSQL.
**Resultado da Parte A:** A programação está pronta. O servidor está 100% ocioso (0% CPU).

### Parte B: O Streaming (On-Demand)

- **O Usuário Sintoniza:** O Usuário abre o Player Web. O `nginx` entrega o `index.html`.
- **O Pedido de Play:** O Player Web faz a chamada: `GET /play/jetix_2000/canal.m3u8`.
- **A "Porta" (Nginx):** O `nginx` (baseado na `location /play/`) encaminha (proxy) o pedido para a `stream-api` (ex: `localhost:8001`).
- **O "Cérebro On-Demand" (stream-api):**
    - A `stream-api` acorda.
    - Ela verifica seu estado interno: "O stream 'jetix_2000' já está rodando?" (Não).
    - Ela consulta o PostgreSQL (tabela `epg_virtual`): "O que deveria estar passando no canal 'jetix_2000' agora (ex: 20:30:05)?"
    - Ela encontra o item (ex: Ep. 12 de Power Rangers, `start_time_virtual`: 20:25:00).
    - Ela calcula o offset: `offset = 5 minutos e 5 segundos (305s)`.
    - Ela gera o `ffconcat` (arquivo de texto) para este item e todos os futuros.
    - Ela inicia o `ffmpeg` (via `subprocess`) usando `-ss 305` (o offset) e o `ffconcat`, com `-c copy` (alta eficiência), mandando a saída HLS para `/mnt/media/streams/hls/jetix_2000/`.
    - Ela salva o PID do `ffmpeg` em seu estado interno e redireciona o Usuário para o arquivo `.m3u8` estático.
- **O Streaming (Nginx):**
    - O Player Web agora pede: `GET /hls/jetix_2000/live.m3u8`.
    - O `nginx` (baseado na `location /hls/`) simplesmente serve esse arquivo estático.
    - O Player Web começa a pedir os segmentos: `seg001.ts`, `seg002.ts`...
- **O "Heartbeat":**
    - Enquanto assiste, o Player Web envia um `POST /heartbeat/jetix_2000` para o `nginx` -> `stream-api` a cada 30 segundos.
    - A `stream-api` atualiza o "last_heartbeat" do canal.
- **O "Ceifador" (Reaper):**
    - Se o Usuário fechar a aba, o "heartbeat" para.
    - Um processo interno na `stream-api` ("The Reaper") nota que o canal 'jetix_2000' não tem heartbeat há 90 segundos.
    - Ele mata o processo `ffmpeg` (usando o PID salvo) e limpa os arquivos HLS.
**Resultado da Parte B:** O servidor volta a 0% de CPU, pronto para o próximo espectador.

## 5. Roteiro de Construção e Fatiamento de Microsserviços

### 1. Visão Geral e Estratégia de Construção

Este documento detalha o roteiro de construção (roadmap) para a implementação completa da arquitetura de microsserviços. Para garantir uma fundação robusta e permitir o desenvolvimento orientado a testes (TDD), a construção será "fatiada" em três (3) Etapas principais. A estratégia adotada é a de "core-to-interface" (do núcleo para a interface), onde construímos primeiro os sistemas de processamento de dados (Ingestão) antes de construir os sistemas de consumo de dados (Streaming).

A arquitetura é dividida em dois fluxos primários:
- **Fluxo de Ingestão (Da Mídia ao BD):** Transforma arquivos brutos em ativos catalogados.
- **Fluxo de Programação e Stream (Do BD à Tela):** Transforma ativos catalogados em um stream de vídeo.

O Fluxo de Ingestão é um pré-requisito fundamental para o Fluxo de Programação. Portanto, ele será nossa primeira etapa de construção.

### 2. Etapa 1: O Pipeline de Ingestão (A "Fábrica de Conteúdo")

**Objetivo:** Implementar o pipeline assíncrono completo que transforma arquivos de mídia brutos (de qualquer fonte) em ativos 100% processados, catalogados e analisados dentro do Banco de Dados Central.

**Componentes-Chave desta Etapa:**
- PostgreSQL (Definição de Schema)
- udev-ingest (Absorvedor Offline)
- admin-ui (Portal de Ingestão Web)
- media-manager (O "Bibliotecário")
- metadata-enricher (O "Curador")
- normalization-worker (O "Estagiário")
- scene-analyzer (O "Editor")

**Dependências Fundamentais (Passo Zero):**
Antes de qualquer serviço, o "Cérebro Central" (PostgreSQL) deve ser modelado. As especificações de schema para as tabelas `media_items` (incluindo metadata JSONB, `last_played_time`, `play_count`), `cue_points`, `channel_master_grid` e `epg_virtual` devem ser definidas e versionadas.

**Fluxo de Trabalho Técnico (TDD):**
- **Unificação de Staging (As Entradas):**
    - Serão implementadas as duas "portas" de entrada.
    - O `udev-ingest` (script bash/udev) será testado para detectar um USB, montar e copiar (rsync) os arquivos para `/mnt/media/staging_ingest/`.
    - O `admin-ui` (servidor web) será testado para receber um upload HTTP e salvar o arquivo no mesmo local: `/mnt/media/staging_ingest/`.
- **Workers de Processamento (TDD Isolado):**
    - O `metadata-enricher` será desenvolvido e testado isoladamente. Os testes unitários devem validar a lógica de parsing de nome (para filmes e séries) e testes de integração devem simular (mock) chamadas à API do TMDB, validando a geração correta do JSONB de metadados.
    - O `normalization-worker` será testado para receber um caminho de arquivo e produzir um arquivo de saída em `/mnt/media/normalized/` que corresponda exatamente às especificações de codec (H.264, AAC) e resolução.
    - O `scene-analyzer` será testado para receber um arquivo normalizado, executar a detecção de breaks (ex: blackdetect) e inserir corretamente os `cue_points` no PostgreSQL.
- **Orquestração (O "Bibliotecário"):**
    - O `media-manager` será implementado para monitorar a pasta de staging.
    - Testes validarão que, ao detectar um arquivo, ele chama (1º) o `metadata-enricher`.
    - Se for usada uma fila (ex: RabbitMQ), testes validarão a publicação dos jobs "Normalização" e "Análise".
    - Testes validarão que, após a conclusão bem-sucedida de todos os jobs, o `media-manager` move o arquivo original de `/staging_ingest/` para seu local final (ex: `/mnt/media/series/...`).

**Critério de Conclusão da Etapa 1:**
Um arquivo de vídeo (ex: `Power.Rangers.S01E01.mkv`) colocado no USB ou enviado via Web UI resulta automaticamente em:
- Uma entrada completa na tabela `media_items` (com sinopse, tags, etc.).
- Entradas correspondentes na tabela `cue_points`.
- Um arquivo de vídeo normalizado em `/mnt/media/normalized/`.
- O arquivo original movido para a biblioteca final.
O sistema de "consumo" (streaming) ainda não existe.

### 3. Etapa 2: O Diretor de Programação (O "Cérebro Criativo")

**Objetivo:** Implementar o microsserviço que consome os ativos catalogados na Etapa 1 e aplica a lógica de negócios para gerar a grade de programação virtual (EPG).

**Componentes-Chave desta Etapa:**
- scheduler-ai (O "Diretor")
- admin-ui (Expansão: "Sala de Direção")

**Dependências Fundamentais:**
- Etapa 1 concluída (o `media_items` e `cue_points` devem estar populados).
- Schema da `channel_master_grid` e `epg_virtual` definido (feito na Etapa 1).

**Fluxo de Trabalho Técnico (TDD):**
- **Interface de Regras (A "Sala de Direção"):**
    - O `admin-ui` será expandido. Será criada a interface (CRUD) que permite ao usuário (você) definir as regras e "âncoras" do canal na tabela `channel_master_grid`.
    - Testes devem validar a inserção de uma regra de "bloco âncora", como o exemplo de `series_linear` (Power Rangers às 17h).
- **Motor de Regras (O "Diretor"):**
    - O `scheduler-ai` será implementado como um processo (ex: cron diário).
    - **Leitura:** Testes validarão que o serviço lê corretamente (1) as regras da `channel_master_grid` e (2) os ativos de `media_items`.
    - **Lógica de Continuidade (TDD):** Implementar a lógica `series_linear`. O teste deve:
        - Simular o estado `current_episode: 12` na `program_config`.
        - Validar que o `scheduler-ai` agenda o episódio 12.
        - Validar que ele atualiza o estado para `current_episode: 13` na `channel_master_grid`.
        - Validar que ele atualiza o `last_played_time` e `play_count` do episódio 12 no `media_items`.
    - **Lógica de Rotação (TDD):** Implementar a lógica `flexible_theme`. O teste deve validar a consulta SQL que seleciona mídias com base em tags (ex: 'halloween') e `last_played_time` (anti-repetição).
    - **Escrita:** Testes validarão que, ao final do processo, a grade completa é escrita corretamente na tabela `epg_virtual`.

**Critério de Conclusão da Etapa 2:**
Após a execução do `scheduler-ai`, a tabela `epg_virtual` está 100% populada com a programação futura (ex: próximos 3 a 7 dias), respeitando as regras definidas na `channel_master_grid`. O sistema de streaming (Etapa 3) ainda não consome esses dados. O servidor permanece 100% ocioso (0% CPU).

### 4. Etapa 3: Consumo On-Demand e Acesso (O "Player")

**Objetivo:** Implementar o "front-end" de consumo e o "cérebro" on-demand que inicia os streams de forma dinâmica, permitindo ao usuário assistir à programação criada na Etapa 2.

**Componentes-Chave desta Etapa:**
- stream-api (O "Cérebro On-Demand")
- nginx (O "Porteiro")
- Player Web (Cliente HTML/JS)

**Dependências Fundamentais:**
- Etapa 2 concluída (a `epg_virtual` está populada).
- Etapa 1 concluída (os arquivos em `/mnt/media/normalized/` existem).

**Fluxo de Trabalho Técnico (TDD):**
- **O "Cérebro On-Demand" (stream-api):**
    - **Endpoint de Gatilho (TDD):** Implementar o endpoint principal (ex: `GET /play/<canal>/canal.m3u8`).
    - **Teste de Lógica (Primeiro Espectador):** Um teste deve simular uma chamada a este endpoint. O teste deve validar que a `stream-api`:
        - Consulta a `epg_virtual` para o horário atual (`NOW()`).
        - Encontra o item correto (ex: Ep. 12, `start_time`: 20:25:00).
        - Calcula o offset corretamente (ex: `NOW()` (20:30:05) - `start_time` (20:25:00) = 305 segundos).
        - Gera o `ffconcat`.
        - Inicia o subprocesso `ffmpeg` com os argumentos corretos (`-ss 305`, `-c copy`).
        - Salva o PID do `ffmpeg` em seu estado interno.
    - **Teste de Lógica (Espectador Simultâneo):** Um teste deve simular uma segunda chamada ao mesmo endpoint (enquanto o primeiro está ativo). O teste deve validar que nenhum novo processo `ffmpeg` é criado e que o segundo usuário é redirecionado para o stream existente.
- **Lifecycle (Heartbeat e Reaper):**
    - Implementar o endpoint `POST /heartbeat/<canal>`.
    - Implementar o processo "Reaper" (Ceifador).
    - **Testar o "Reaper":** Simular um stream ativo cujo `last_heartbeat` não é atualizado. Validar que, após o timeout (ex: 90s), o "Reaper" identifica o processo (usando o PID salvo) e o encerra.
- **O Cliente (Player Web):**
    - Desenvolver o Player Web (HTML/JS).
    - O player deve ser capaz de chamar o endpoint de gatilho (ex: `/play/jetix_2000/canal.m3u8`).
    - Implementar a lógica `setInterval` que envia o `POST /heartbeat/jetix_2000` a cada 30 segundos.
- **A "Porta" (Nginx):**
    - Implementar a configuração final do `nginx`.
    - `location /play/` deve ser um `proxy_pass` para a `stream-api`.
    - `location /hls/` deve servir os arquivos estáticos (`.m3u8`, `.ts`) que o `ffmpeg` está criando em tempo real.
    - `location /` deve servir o Player Web.

**Critério de Conclusão da Etapa 3:**
A aplicação está 100% funcional. O usuário acessa o IP/domínio, o Player Web carrega, o `ffmpeg` é iniciado dinamicamente pela `stream-api` no ponto exato da programação, e o usuário assiste ao stream. Ao fechar a aba, o "Reaper" limpa o processo `ffmpeg` e o servidor retorna a 0% de CPU.

### 5. Resumo das Etapas de Construção

| Etapa | Título | Foco Principal | Resultado Chave |
| :--- | :--- | :--- | :--- |
| 1 | Pipeline de Ingestão | `media-manager`, `metadata-enricher`, `normalization-worker`, `scene-analyzer` | O PostgreSQL é populado automaticamente com ativos (`media_items`, `cue_points`) a partir de arquivos brutos. |
| 2 | Diretor de Programação | `scheduler-ai`, `channel_master_grid` (via `admin-ui`) | A tabela `epg_virtual` é preenchida com a grade de programação futura, com base em regras de negócio. |
| 3 | Consumo On-Demand | `stream-api`, `nginx`, Player Web | O usuário pode assistir ao EPG da Etapa 2, com streams (`ffmpeg`) iniciados e encerrados dinamicamente. |
