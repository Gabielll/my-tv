# Requirements Document

## Introduction

Para facilitar o teste do sistema no Render, precisamos temporariamente hardcodar as variáveis de ambiente do RabbitMQ diretamente no código. Isso permitirá testar a funcionalidade completa do pipeline de processamento de mídia sem depender da configuração manual das variáveis de ambiente no dashboard do Render.

## Requirements

### Requirement 1

**User Story:** Como desenvolvedor, eu quero hardcodar temporariamente as credenciais do RabbitMQ no código, para que eu possa testar rapidamente se o pipeline de processamento está funcionando no Render.

#### Acceptance Criteria

1. WHEN o sistema inicializar THEN as credenciais do RabbitMQ devem ser definidas diretamente no código
2. WHEN um serviço tentar conectar ao RabbitMQ THEN deve usar as credenciais hardcoded em vez das variáveis de ambiente
3. WHEN as credenciais hardcoded estiverem ativas THEN deve haver um log de warning indicando que está em modo de teste
4. WHEN o sistema estiver em produção THEN deve ser fácil reverter para usar variáveis de ambiente

### Requirement 2

**User Story:** Como desenvolvedor, eu quero que apenas as variáveis do RabbitMQ sejam hardcoded, para que outras configurações sensíveis (banco de dados, APIs) continuem usando variáveis de ambiente.

#### Acceptance Criteria

1. WHEN o sistema usar credenciais hardcoded THEN apenas as variáveis RABBITMQ_* devem ser afetadas
2. WHEN outras configurações forem acessadas THEN devem continuar usando variáveis de ambiente normalmente
3. WHEN o modo de teste estiver ativo THEN deve ser claramente identificável nos logs

### Requirement 3

**User Story:** Como desenvolvedor, eu quero que a mudança seja facilmente reversível, para que eu possa voltar ao modo normal de produção rapidamente.

#### Acceptance Criteria

1. WHEN eu quiser desabilitar o modo de teste THEN deve ser possível com uma única mudança de configuração
2. WHEN reverter para produção THEN não deve haver código de teste residual
3. WHEN em modo de produção THEN não deve haver logs ou comportamentos relacionados ao modo de teste

### Requirement 4

**User Story:** Como desenvolvedor, eu quero testar o pipeline completo de processamento, para que eu possa verificar se o upload, enrichment, normalização e análise estão funcionando.

#### Acceptance Criteria

1. WHEN um arquivo for enviado via admin-ui THEN deve ser processado automaticamente pelo pipeline
2. WHEN o media-manager detectar um arquivo THEN deve publicar mensagem na fila de enrichment
3. WHEN o metadata-enricher processar um item THEN deve publicar mensagem na fila de normalização
4. WHEN o normalization-worker processar um item THEN deve publicar mensagem na fila de análise
5. WHEN todo o pipeline executar THEN o status do arquivo deve progredir através de todos os estágios

### Requirement 5

**User Story:** Como desenvolvedor, eu quero logs detalhados do processamento, para que eu possa identificar onde o pipeline pode estar falhando.

#### Acceptance Criteria

1. WHEN cada serviço processar uma mensagem THEN deve logar o início e fim do processamento
2. WHEN houver erro de conexão RabbitMQ THEN deve logar detalhes específicos do erro
3. WHEN uma mensagem for publicada THEN deve logar a fila de destino e o conteúdo
4. WHEN uma mensagem for consumida THEN deve logar a origem e o processamento