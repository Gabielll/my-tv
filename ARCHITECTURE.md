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

## 5. Roteiro de Construção (Fatiamento)

A implementação será dividida em três (3) etapas de construção principais.
- **Etapa 1: O Pipeline de Ingestão (A "Fábrica")**
    - **Foco:** Construir todos os componentes do Fluxo 1.
    - **Componentes:** PostgreSQL (Schema), `udev-ingest`, `admin-ui` (só upload), `media-manager`, `metadata-enricher`, `normalization-worker`, `scene-analyzer`.
    - **Resultado:** Um sistema que automaticamente cataloga, transcodifica e analisa qualquer arquivo de mídia adicionado (via USB ou Web). O BD estará populado, mas nada será "assistível".
- **Etapa 2: O Diretor de Programação (O "Cérebro Criativo")**
    - **Foco:** Construir o microsserviço que cria a programação (Parte A do Fluxo 2).
    - **Componentes:** `scheduler-ai` e a expansão do `admin-ui` (para editar a `channel_master_grid`).
    - **Resultado:** A tabela `epg_virtual` do PostgreSQL será preenchida com uma grade de programação inteligente e completa. O servidor ainda estará 100% ocioso.
- **Etapa 3: O Consumo On-Demand (O "Play")**
    - **Foco:** Construir os componentes que entregam o vídeo ao usuário (Parte B do Fluxo 2).
    - **Componentes:** `stream-api`, Player Web (com Heartbeat) e a configuração final do `nginx` (proxy e HLS).
    - **Resultado:** A aplicação está 100% funcional. O usuário pode "sintonizar" o canal e assistir à programação no ponto exato em que ela deveria estar.
