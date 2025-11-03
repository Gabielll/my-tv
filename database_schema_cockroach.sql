-- Tabela para armazenar todos os itens de mídia e seus metadados.
CREATE TABLE media_items (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    synopsis TEXT,
    tags JSONB,
    -- O caminho para o arquivo normalizado em /mnt/media/normalized/
    file_path TEXT NOT NULL UNIQUE,
    -- O caminho para o arquivo original (para referência)
    original_file_path TEXT,
    -- Status do processamento no pipeline de ingestão
    status VARCHAR(20) DEFAULT 'pending', -- ex: pending, processing, needs_review, complete
    -- Metadados ricos do TMDB ou outras fontes
    metadata JSONB,
    -- Controle de reprodução
    last_played_time TIMESTAMP,
    play_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para armazenar os pontos de corte (ex: "breaks" comerciais)
CREATE TABLE cue_points (
    id SERIAL PRIMARY KEY,
    media_item_id INT NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    -- O timestamp do ponto de corte dentro do vídeo (em segundos)
    cue_time REAL NOT NULL,
    cue_type VARCHAR(20) DEFAULT 'commercial_break', -- ex: commercial_break, intro_end, credits_start
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para definir as regras de negócio de cada canal.
-- Esta é a "alma" do Diretor de Programação.
CREATE TABLE channel_master_grid (
    id SERIAL PRIMARY KEY,
    channel_id VARCHAR(50) NOT NULL UNIQUE, -- ex: 'jetix_2000'
    channel_name TEXT NOT NULL,
    -- As regras de programação como um todo.
    rules JSONB,
    -- Estado dinâmico que o scheduler-ai pode usar para manter a continuidade.
    -- Ex: {"series_linear": {"power_rangers": {"current_episode": 12}}}
    program_state JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para armazenar a grade de programação virtual gerada.
-- É o resultado do trabalho do scheduler-ai.
CREATE TABLE epg_virtual (
    id BIGSERIAL PRIMARY KEY,
    channel_id VARCHAR(50) NOT NULL REFERENCES channel_master_grid(channel_id),
    media_item_id INT NOT NULL REFERENCES media_items(id),
    -- Horário de início e fim "virtual" na grade de programação
    start_time_virtual TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time_virtual TIMESTAMP WITH TIME ZONE NOT NULL,
    -- Título e sinopse podem ser duplicados aqui para acesso rápido
    title TEXT,
    synopsis TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para otimizar as consultas mais comuns
CREATE INDEX idx_media_items_status ON media_items(status);
CREATE INDEX idx_cue_points_media_item_id ON cue_points(media_item_id);
CREATE INDEX idx_epg_virtual_channel_id_start_time ON epg_virtual(channel_id, start_time_virtual);

-- Índice único para evitar sobreposições de programação no mesmo canal
-- (substitui a constraint EXCLUDE que não é suportada no CockroachDB)
CREATE UNIQUE INDEX idx_epg_virtual_no_overlap ON epg_virtual(channel_id, start_time_virtual, end_time_virtual);