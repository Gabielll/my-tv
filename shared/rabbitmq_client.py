import os
import pika
import logging
import time
from .config import Config

def get_rabbitmq_connection():
    """
    Cria e retorna uma conexão com o RabbitMQ.
    Inclui retentativas para dar tempo ao serviço de iniciar.
    """
    config = Config.get_rabbitmq_config()
    
    # Check if RabbitMQ is properly configured
    if not config['host'] or config['host'] == 'localhost':
        logging.warning("RabbitMQ host not configured or using localhost. Skipping connection.")
        return None
    
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Create connection parameters with credentials
            credentials = pika.PlainCredentials(config['username'], config['password'])
            parameters = pika.ConnectionParameters(
                host=config['host'],
                port=config['port'],
                virtual_host=config['virtual_host'],
                credentials=credentials,
                connection_attempts=3,
                retry_delay=2,
                heartbeat=config['heartbeat']
            )
            
            connection = pika.BlockingConnection(parameters)
            logging.info("Conexão com RabbitMQ estabelecida com sucesso.")
            return connection
        except (pika.exceptions.AMQPConnectionError, pika.exceptions.ProbableAuthenticationError) as e:
            logging.warning(f"Não foi possível conectar ao RabbitMQ (tentativa {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                logging.error("Falha de autenticação no RabbitMQ. Verifique as credenciais nas variáveis de ambiente.")
            time.sleep(retry_delay)
        except Exception as e:
            logging.error(f"Erro inesperado ao conectar ao RabbitMQ (tentativa {attempt + 1}/{max_retries}): {e}")
            time.sleep(retry_delay)
    
    logging.error("Falha ao conectar ao RabbitMQ após múltiplas tentativas.")
    return None

def publish_message(queue_name, message):
    """
    Publica uma mensagem em uma fila RabbitMQ.
    A função gerencia a conexão e o canal.
    """
    connection = get_rabbitmq_connection()
    if not connection:
        logging.warning(f"RabbitMQ não disponível. Mensagem '{message}' para fila '{queue_name}' não foi publicada.")
        return False

    try:
        channel = connection.channel()
        # Declara a fila (cria se não existir), durable=True a torna resistente a reinicializações
        channel.queue_declare(queue=queue_name, durable=True)
        # Publica a mensagem
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Torna a mensagem persistente
            ))
        logging.info(f"Mensagem '{message}' publicada na fila '{queue_name}'")
        return True
    except Exception as e:
        logging.error(f"Erro ao publicar mensagem no RabbitMQ: {e}")
        return False
    finally:
        if connection and connection.is_open:
            connection.close()

def start_consumer(queue_name, callback_function):
    """
    Inicia um consumidor para uma fila RabbitMQ.
    Esta função entra em um loop infinito para escutar mensagens.
    """
    connection = get_rabbitmq_connection()
    if not connection:
        logging.warning(f"RabbitMQ não disponível. Consumidor para fila '{queue_name}' não foi iniciado.")
        return False

    try:
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)

        # Garante que o consumidor só receba uma mensagem por vez
        channel.basic_qos(prefetch_count=1)

        def callback_wrapper(ch, method, properties, body):
            """Wrapper para a função de callback que confirma o recebimento da mensagem."""
            try:
                # Executa a função de processamento real
                callback_function(body.decode())
                # Confirma que a mensagem foi processada com sucesso
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logging.info(f"Mensagem processada e confirmada: {body.decode()}")
            except Exception as e:
                logging.error(f"Erro ao processar a mensagem: {e}")
                # Rejeita a mensagem, mas não a re-enfileira para evitar loops de falha
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(queue=queue_name, on_message_callback=callback_wrapper)

        logging.info(f"Consumidor iniciado para a fila '{queue_name}'. Aguardando mensagens...")
        channel.start_consuming()
        return True
    except Exception as e:
        logging.error(f"Erro crítico no consumidor RabbitMQ: {e}")
        return False
    finally:
        if connection and connection.is_open:
            connection.close()
