import os
import pika
import logging
import time

# --- Configuração ---
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')

def get_rabbitmq_connection():
    """
    Cria e retorna uma conexão com o RabbitMQ.
    Inclui retentativas para dar tempo ao serviço de iniciar.
    """
    max_retries = 10
    retry_delay = 5
    for attempt in range(max_retries):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            logging.info("Conexão com RabbitMQ estabelecida com sucesso.")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            logging.warning(f"Não foi possível conectar ao RabbitMQ (tentativa {attempt + 1}/{max_retries}): {e}")
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
        return

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
    except Exception as e:
        logging.error(f"Erro ao publicar mensagem no RabbitMQ: {e}")
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
        logging.error("Não é possível iniciar o consumidor sem uma conexão com o RabbitMQ.")
        return

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
    except Exception as e:
        logging.error(f"Erro crítico no consumidor RabbitMQ: {e}")
    finally:
        if connection and connection.is_open:
            connection.close()
