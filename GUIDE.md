# Guia de Funcionamento e Utilização do Projeto

Este guia detalha como funciona o projeto de servidor de mídia, como configurá-lo localmente e como utilizá-lo no dia a dia, tanto na versão de desenvolvimento quanto na versão online implantada no Render.

## 1. Visão Geral do Projeto

O projeto é um servidor de mídia pessoal desenhado para simular canais de TV 24/7, mas com uma filosofia de **eficiência on-demand**. Em vez de transcodificar vídeo continuamente, o sistema permanece 100% ocioso até que um espectador "sintonize" um canal. Nesse momento, um processo `ffmpeg` é iniciado dinamicamente para servir o conteúdo. Quando o último espectador sai, o processo é encerrado, economizando recursos computacionais.

A arquitetura é baseada em microsserviços que cuidam de tarefas específicas: ingestão de mídia, enriquecimento de metadados, agendamento de programação e streaming.

## 2. Configuração do Ambiente Local (Desenvolvimento)

Para rodar o projeto em sua máquina local, você precisará de um ambiente Linux com Docker e Docker Compose.

### Pré-requisitos

- **Sistema Operacional:** Uma distribuição Linux (recomendado Ubuntu 20.04 ou superior).
- **Docker e Docker Compose:** Essenciais para orquestrar os contêineres dos microsserviços. [Instale o Docker](https://docs.docker.com/engine/install/ubuntu/) e o [Docker Compose](https://docs.docker.com/compose/install/).
- **Git:** Para clonar o repositório.
- **HD Externo (Opcional, mas recomendado):** Formatado em um sistema de arquivos Linux (ex: `ext4`) para armazenar a mídia.

### Passos para Instalação

1.  **Clonar o Repositório:**
    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd <NOME_DO_REPOSITORIO>
    ```

2.  **Configurar o Ponto de Montagem:**
    O sistema é projetado para usar um diretório `/mnt/media` como a biblioteca principal. Você pode criar um link simbólico para sua pasta de mídia ou configurar uma montagem permanente via `/etc/fstab`.

    **Exemplo (Link Simbólico):**
    Suponha que seu HD externo com as mídias esteja em `/media/user/MeuHD`.
    ```bash
    # Crie o diretório base se ele não existir
    sudo mkdir -p /mnt/media

    # Crie as subpastas que o sistema espera
    sudo mkdir -p /mnt/media/staging_ingest
    sudo mkdir -p /mnt/media/normalized
    sudo mkdir -p /mnt/media/streams
    sudo mkdir -p /mnt/media/series
    sudo mkdir -p /mnt/media/movies

    # Dê permissões adequadas
    sudo chown -R $USER:$USER /mnt/media

    # Se você quiser usar uma pasta diferente, pode criar um link
    # ln -s /media/user/MeuHD/videos /mnt/media/series
    ```

3.  **Subir os Contêineres:**
    O arquivo `docker-compose.yml` na raiz do projeto contém a definição de todos os serviços. Para iniciar a aplicação completa:
    ```bash
    docker compose up --build -d
    ```
    O comando `--build` força a reconstrução das imagens, útil na primeira vez ou após mudanças no código. O `-d` (detached) executa os contêineres em segundo plano.

4.  **Verificar o Status:**
    Para ver se todos os serviços estão rodando corretamente:
    ```bash
    docker compose ps
    ```
    Você também pode ver os logs de um serviço específico:
    ```bash
    docker compose logs -f admin_ui
    ```

### Acessando os Serviços Locais

- **Admin UI (Upload e Gestão):** `http://localhost:8000`
- **Player Web:** `http://localhost` (servido pelo Nginx na porta 80)
- **RabbitMQ Management:** `http://localhost:15672` (usuário: `user`, senha: `password`)
- **CockroachDB Admin:** `http://localhost:8081`

## 3. Utilização do Sistema

### Formato dos Vídeos

Para garantir a máxima compatibilidade e eficiência (usando `-c copy` no `ffmpeg`), o ideal é que seus arquivos de vídeo já estejam em um formato padrão:

- **Contêiner:** MP4 ou MKV
- **Codec de Vídeo:** H.264 (AVC)
- **Codec de Áudio:** AAC

O serviço `normalization-worker` tentará converter os vídeos para este formato, mas se eles já estiverem padronizados, o processo de ingestão será muito mais rápido.

### Adicionando Mídia

Existem duas formas de adicionar novos arquivos de mídia ao sistema:

1.  **Via HD Externo (Modo Offline - `udev-ingest`):**
    - Esta funcionalidade (ainda a ser implementada com scripts `udev`) permite que você simplesmente conecte um dispositivo USB (pendrive, HD externo) ao seu servidor Linux.
    - Um script detectará o dispositivo e copiará automaticamente os arquivos para a pasta `/mnt/media/staging_ingest`.
    - A partir daí, o serviço `media-manager` iniciará o pipeline de processamento.

2.  **Via Interface Web (Modo Online - `admin-ui`):**
    - Acesse a interface de administração em `http://localhost:8000`.
    - Utilize o formulário de upload para enviar os arquivos de vídeo.
    - Os arquivos serão salvos em `/mnt/media/staging_ingest`, e o `media-manager` começará o processamento.

O `media-manager` orquestra o processo: o `metadata-enricher` busca informações online (capa, sinopse, tags), o `normalization-worker` padroniza o formato e o `scene-analyzer` detecta possíveis pontos de intervalo.

## 4. Configuração do Servidor Físico (Opcional)

Se você planeja usar um PC dedicado como servidor de mídia 24/7, estas configurações são recomendadas.

### Sistema Operacional

- **Recomendação:** Ubuntu Server 20.04 LTS. É estável, tem suporte de longo prazo e uma vasta documentação.
- **Configuração Mínima:**
    - Acesso SSH habilitado para administração remota.
    - Firewall (`ufw`) configurado para permitir apenas as portas necessárias (SSH, HTTP).

### Configuração da BIOS

Para garantir que o servidor volte a funcionar sozinho após uma queda de energia, uma configuração na BIOS é crucial.

1.  **Acesse a BIOS/UEFI:** Reinicie o PC e pressione a tecla indicada para entrar no setup (geralmente `DEL`, `F2`, `F10` ou `ESC`).
2.  **Encontre a Configuração de Energia:** Procure por uma seção chamada `Power Management`, `ACPI Configuration` ou similar.
3.  **Habilite "Restore on AC/Power Loss":** Dentro dessa seção, haverá uma opção como `AC Power Recovery`, `Restore on AC/Power Loss`, `After Power Loss` ou `Power On after Power Fail`.
4.  **Selecione "Power On" ou "Always On":** Mude o valor desta opção para `Power On` (ou similar). Isso fará com que o computador ligue automaticamente assim que a energia elétrica for restabelecida.
5.  **Salve e Saia:** Salve as configurações e reinicie o PC.

## 5. Consumo do Conteúdo (Online - Render)

A versão implantada no Render permite que você acesse seus canais de qualquer lugar.

- **Acesso ao Player:** Você receberá uma URL pública para o serviço `nginx` (ex: `https://meu-media-server.onrender.com`). Acesse essa URL para abrir o player web.
- **Seleção de Canais:** O player terá uma interface para selecionar o canal que você deseja assistir.
- **Funcionamento:** Ao "sintonizar", o player fará uma requisição à `stream-api` (através do proxy Nginx), que iniciará o processo `ffmpeg` nos servidores do Render e começará a transmitir o conteúdo agendado.
- **Heartbeat:** Assim como na versão local, o player envia "heartbeats" para manter o stream ativo. Se você fechar a aba, o "Reaper" no Render encerrará o processo para economizar recursos.
