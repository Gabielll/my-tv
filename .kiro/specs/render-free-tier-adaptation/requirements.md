# Requirements Document

## Introduction

Este documento define os requisitos para converter os workers do sistema de TV/mídia em web services, mantendo a arquitetura e funcionalidades originais intactas. O objetivo é adaptar apenas o tipo de serviço (de worker para web service) para compatibilidade com o nível gratuito do Render, usando UptimeRobot para manter os serviços ativos.

## Requirements

### Requirement 1

**User Story:** Como um desenvolvedor, eu quero que os workers sejam convertidos em web services, para que eu possa fazer deploy no Render gratuito mantendo a arquitetura original.

#### Acceptance Criteria

1. WHEN um worker é convertido THEN o serviço SHALL manter toda a lógica de processamento original
2. WHEN o web service inicia THEN o sistema SHALL executar a lógica de worker internamente
3. WHEN o serviço recebe requisições HTTP THEN o sistema SHALL responder com status de saúde
4. WHEN o UptimeRobot faz ping THEN o serviço SHALL permanecer ativo e processando

### Requirement 2

**User Story:** Como um administrador do sistema, eu quero que a funcionalidade original seja preservada, para que o sistema continue funcionando exatamente como projetado.

#### Acceptance Criteria

1. WHEN o media-manager é convertido THEN o sistema SHALL continuar monitorando a pasta staging
2. WHEN o metadata-enricher é convertido THEN o sistema SHALL continuar processando metadados via RabbitMQ
3. WHEN o normalization-worker é convertido THEN o sistema SHALL continuar normalizando vídeos via fila
4. WHEN o scene-analyzer é convertido THEN o sistema SHALL continuar analisando cenas via fila
5. WHEN o scheduler-ai é convertido THEN o sistema SHALL continuar gerando EPG periodicamente

### Requirement 3

**User Story:** Como um DevOps, eu quero que os serviços tenham endpoints de saúde, para que o UptimeRobot possa mantê-los ativos.

#### Acceptance Criteria

1. WHEN um web service é acessado THEN o sistema SHALL expor endpoint /health
2. WHEN o endpoint /health é chamado THEN o sistema SHALL retornar status 200 com informações do worker
3. WHEN o serviço está processando THEN o health check SHALL indicar status ativo
4. WHEN há erro no processamento THEN o health check SHALL indicar o problema

### Requirement 4

**User Story:** Como um desenvolvedor, eu quero manter as mesmas dependências e configurações, para que não seja necessário alterar a lógica de negócio.

#### Acceptance Criteria

1. WHEN os serviços são convertidos THEN o sistema SHALL manter conexões com PostgreSQL/CockroachDB
2. WHEN os serviços são convertidos THEN o sistema SHALL manter conexões com RabbitMQ
3. WHEN os serviços são convertidos THEN o sistema SHALL manter todas as variáveis de ambiente
4. WHEN os serviços são convertidos THEN o sistema SHALL manter a mesma estrutura de logs

### Requirement 5

**User Story:** Como um testador, eu quero que o sistema funcione identicamente ao original, para que eu possa validar se a arquitetura é viável.

#### Acceptance Criteria

1. WHEN arquivos são enviados THEN o pipeline de ingestão SHALL funcionar exatamente igual
2. WHEN o scheduler executa THEN a geração de EPG SHALL funcionar exatamente igual  
3. WHEN streams são iniciados THEN o comportamento SHALL ser idêntico ao original
4. WHEN todos os serviços estão rodando THEN o sistema SHALL ter a mesma funcionalidade completa