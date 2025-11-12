# Design Document

## Overview

Este design implementa uma solução temporária para hardcodar as credenciais do RabbitMQ diretamente no código, permitindo testes rápidos do pipeline de processamento no Render sem necessidade de configurar variáveis de ambiente manualmente.

## Architecture

### Componentes Afetados
- `shared/config.py` - Configuração centralizada
- `shared/rabbitmq_client.py` - Cliente RabbitMQ
- Todos os serviços que usam RabbitMQ (media-manager, metadata-enricher, normalization-worker, scene-analyzer, scheduler-ai)

### Fluxo de Configuração
1. Sistema verifica se existe uma flag de teste ativa
2. Se ativa, usa credenciais hardcoded para RabbitMQ
3. Se não ativa, usa variáveis de ambiente normalmente
4. Logs indicam qual modo está sendo usado

## Components and Interfaces

### 1. Test Configuration Flag
```python
# Em shared/config.py
ENABLE_RABBITMQ_TEST_MODE = True  # Flag para ativar/desativar modo teste
```

### 2. Enhanced RabbitMQ Configuration
```python
@classmethod
def get_rabbitmq_config(cls) -> Dict[str, Any]:
    """Get RabbitMQ configuration with test mode support"""
    
    # Credenciais hardcoded para teste
    if cls.is_rabbitmq_test_mode():
        return {
            'host': 'jaragua.lmq.cloudamqp.com',
            'port': 5672,
            'username': 'bgepvloi',
            'password': 'alfnh4BZ5O6TJCrrbfDXtrLLgifzIh01',
            'virtual_host': 'bgepvloi',
            'connection_timeout': 10,
            'heartbeat': 600
        }
    
    # Configuração normal via environment variables
    return {
        'host': os.getenv('RABBITMQ_HOST', 'localhost'),
        'port': int(os.getenv('RABBITMQ_PORT', '5672')),
        'username': os.getenv('RABBITMQ_USER', 'guest'),
        'password': os.getenv('RABBITMQ_PASS', 'guest'),
        'virtual_host': os.getenv('RABBITMQ_VHOST', '/'),
        'connection_timeout': int(os.getenv('RABBITMQ_CONNECT_TIMEOUT', '10')),
        'heartbeat': int(os.getenv('RABBITMQ_HEARTBEAT', '600'))
    }
```

### 3. Test Mode Detection
```python
@classmethod
def is_rabbitmq_test_mode(cls) -> bool:
    """Check if RabbitMQ test mode is enabled"""
    # Pode ser controlado por environment variable ou flag hardcoded
    return os.getenv('RABBITMQ_TEST_MODE', 'false').lower() == 'true' or ENABLE_RABBITMQ_TEST_MODE
```

### 4. Enhanced Logging
```python
def get_rabbitmq_connection():
    """Enhanced connection with test mode logging"""
    config = Config.get_rabbitmq_config()
    
    if Config.is_rabbitmq_test_mode():
        logging.warning("🧪 RABBITMQ TEST MODE ATIVO - Usando credenciais hardcoded")
        logging.info(f"Conectando ao RabbitMQ de teste: {config['host']}")
    else:
        logging.info(f"Conectando ao RabbitMQ: {config['host']}")
```

## Data Models

### Configuration Structure
```python
RabbitMQConfig = {
    'host': str,
    'port': int,
    'username': str,
    'password': str,
    'virtual_host': str,
    'connection_timeout': int,
    'heartbeat': int
}
```

### Test Mode Indicators
```python
TestModeStatus = {
    'rabbitmq_test_mode': bool,
    'config_source': 'hardcoded' | 'environment',
    'warning_logged': bool
}
```

## Error Handling

### 1. Fallback Strategy
- Se credenciais hardcoded falharem, tenta variáveis de ambiente
- Se ambas falharem, continua sem RabbitMQ (modo degradado)

### 2. Connection Errors
- Log detalhado de erros de conexão
- Diferenciação entre erros de autenticação e conectividade
- Retry automático com backoff

### 3. Configuration Validation
- Validação das credenciais antes de tentar conexão
- Warning se credenciais parecem inválidas

## Testing Strategy

### 1. Unit Tests
- Testes para modo hardcoded vs environment variables
- Validação de configuração em ambos os modos
- Mocking de conexões RabbitMQ

### 2. Integration Tests
- Teste completo do pipeline com credenciais hardcoded
- Verificação de publicação e consumo de mensagens
- Teste de fallback quando RabbitMQ não está disponível

### 3. Manual Testing
- Upload de arquivo via admin-ui
- Verificação de processamento através do pipeline
- Monitoramento de logs para confirmar modo de teste

## Implementation Plan

### Phase 1: Core Configuration
1. Adicionar flag de teste em `shared/config.py`
2. Implementar detecção de modo de teste
3. Adicionar credenciais hardcoded

### Phase 2: Enhanced Logging
1. Adicionar logs de warning para modo de teste
2. Melhorar logs de conexão RabbitMQ
3. Adicionar logs de debug para troubleshooting

### Phase 3: Testing & Validation
1. Testar conexão com credenciais hardcoded
2. Validar pipeline completo de processamento
3. Verificar logs e comportamento

### Phase 4: Cleanup Strategy
1. Documentar como desabilitar modo de teste
2. Preparar commit para reverter mudanças
3. Validar comportamento em produção

## Security Considerations

### 1. Temporary Nature
- Credenciais hardcoded são APENAS para teste
- Devem ser removidas antes de produção final
- Flag de controle permite desabilitação rápida

### 2. Logging Security
- Não logar senhas completas
- Mascarar credenciais sensíveis nos logs
- Indicar claramente quando em modo de teste

### 3. Environment Separation
- Modo de teste claramente identificado
- Não afetar outras configurações (DB, APIs)
- Fácil reversão para modo normal

## Deployment Strategy

### 1. Gradual Rollout
- Implementar primeiro em um serviço (media-manager)
- Testar conexão e funcionalidade
- Expandir para outros serviços

### 2. Monitoring
- Monitorar logs para confirmação de modo de teste
- Verificar métricas de conexão RabbitMQ
- Acompanhar processamento de mensagens

### 3. Rollback Plan
- Commit separado para cada mudança
- Flag de controle para desabilitação rápida
- Documentação clara de reversão