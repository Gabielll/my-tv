import pytest
from unittest.mock import MagicMock, call
import os
import sys

from media_manager import media_manager

# --- Fixtures ---

@pytest.fixture
def mock_db_connection(mocker):
    """Fixture que simula a conexão com o banco de dados."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    # Configura o gerenciador de contexto 'with' para retornar o mock do cursor
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mocker.patch('media_manager.media_manager.get_db_connection', return_value=mock_conn)
    return mock_conn, mock_cur

@pytest.fixture
def mock_rabbitmq_client(mocker):
    """Fixture que simula o cliente RabbitMQ."""
    # Substitui o objeto inteiro para garantir que a referência seja a correta
    mock_client = MagicMock()
    mocker.patch('media_manager.media_manager.rabbitmq_client', mock_client)
    return mock_client

@pytest.fixture
def handler(mock_db_connection, mock_rabbitmq_client):
    """Fixture que cria uma instância do NewFileHandler."""
    return media_manager.NewFileHandler()

# --- Testes ---

def test_process_new_media_success(handler, mock_db_connection, mock_rabbitmq_client):
    """
    Testa o cenário de sucesso: um novo arquivo de mídia válido é detectado e processado.
    Verifica se o arquivo é inserido no BD e uma mensagem é publicada.
    """
    # Arrange
    mock_conn, mock_cur = mock_db_connection

    file_path = "/mnt/media/staging_ingest/My.Movie.2023.mkv"

    # Configura o comportamento do fetchone para duas chamadas sequenciais:
    # 1. A primeira (SELECT) não encontra o arquivo.
    # 2. A segunda (INSERT ... RETURNING) retorna o novo ID.
    mock_cur.fetchone.side_effect = [None, [123]]

    # Act
    handler.process_new_media(file_path)

    # Assert
    # 1. Verifica se a consulta de SELECT (para evitar duplicatas) foi chamada
    mock_cur.execute.assert_any_call("SELECT id FROM media_items WHERE original_file_path = %s;", (file_path,))

    # 2. Verifica se a consulta de INSERT foi chamada com os dados corretos
    insert_sql = """
                    INSERT INTO media_items (title, original_file_path, file_path, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """
    expected_title = "My.Movie.2023"
    expected_final_path = f"/mnt/media/normalized/{os.path.basename(file_path)}"
    mock_cur.execute.assert_any_call(insert_sql, (expected_title, file_path, expected_final_path, 'pending_enrichment'))

    # 3. Verifica se o commit foi chamado
    mock_conn.commit.assert_called_once()

    # 4. Verifica se a mensagem foi publicada no RabbitMQ com o ID correto
    mock_rabbitmq_client.publish_message.assert_called_once_with('enrichment_jobs', '123')

def test_process_new_media_already_exists(handler, mock_db_connection, mock_rabbitmq_client):
    """
    Testa o cenário onde o arquivo de mídia já existe no banco de dados.
    Verifica se o processo é interrompido e nenhuma ação de inserção ou publicação ocorre.
    """
    # Arrange
    mock_conn, mock_cur = mock_db_connection

    file_path = "/mnt/media/staging_ingest/Existing.Movie.2022.mp4"

    # Simula que o arquivo JÁ EXISTE no BD
    mock_cur.fetchone.return_value = (1,) # Retorna um ID existente

    # Act
    handler.process_new_media(file_path)

    # Assert
    # 1. Apenas o SELECT deve ser chamado
    mock_cur.execute.assert_called_once_with("SELECT id FROM media_items WHERE original_file_path = %s;", (file_path,))

    # 2. Nenhuma outra chamada ao cursor (INSERT) deve ocorrer
    assert mock_cur.execute.call_count == 1

    # 3. O commit não deve ser chamado
    mock_conn.commit.assert_not_called()

    # 4. Nenhuma mensagem deve ser publicada
    mock_rabbitmq_client.publish_message.assert_not_called()

def test_on_created_ignores_directories(handler):
    """
    Testa se o manipulador de eventos ignora eventos de criação de diretórios.
    """
    # Arrange
    mock_event = MagicMock()
    mock_event.is_directory = True
    handler.process_new_media = MagicMock() # Mock para verificar se não é chamado

    # Act
    handler.on_created(mock_event)

    # Assert
    handler.process_new_media.assert_not_called()

def test_on_created_ignores_invalid_extensions(handler):
    """
    Testa se o manipulador de eventos ignora arquivos com extensões não permitidas.
    """
    # Arrange
    mock_event = MagicMock()
    mock_event.is_directory = False
    mock_event.src_path = "/path/to/my/document.txt" # Extensão inválida
    handler.process_new_media = MagicMock()

    # Act
    handler.on_created(mock_event)

    # Assert
    handler.process_new_media.assert_not_called()
