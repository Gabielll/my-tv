import pytest
from unittest.mock import MagicMock, call
import os
import sys

from normalization_worker import worker

# --- Fixtures ---

@pytest.fixture
def mock_db_connection(mocker):
    """Fixture que simula a conexão com o banco de dados."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mocker.patch('normalization_worker.worker.get_db_connection', return_value=mock_conn)
    return mock_conn, mock_cur

@pytest.fixture
def mock_rabbitmq_client(mocker):
    """Fixture que simula o cliente RabbitMQ."""
    mock_client = MagicMock()
    mocker.patch('normalization_worker.worker.rabbitmq_client', mock_client)
    return mock_client

@pytest.fixture
def mock_subprocess(mocker):
    """Fixture que simula o subprocess.Popen usado pelo ffmpeg."""
    mock_proc = MagicMock()
    mock_proc.wait.return_value = None
    mock_proc.returncode = 0
    mock_proc.stderr = iter([])  # Simula stderr vazio
    mocker.patch('subprocess.Popen', return_value=mock_proc)
    # Mock para interações com o sistema de arquivos
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.makedirs')
    mocker.patch('os.path.getsize', return_value=1024)  # Mock file size
    return mock_proc

# --- Testes ---

def test_process_message_success(mock_db_connection, mock_rabbitmq_client, mock_subprocess):
    """
    Testa o cenário de sucesso da normalização.
    Verifica se o BD é atualizado e a mensagem é publicada para a próxima fila.
    """
    # Arrange
    media_item_id = 1
    original_path = "/path/to/source/video.mkv"

    mock_conn, mock_cur = mock_db_connection
    # Simula a busca do caminho do arquivo original no BD
    mock_cur.fetchone.return_value = (original_path,)

    # Simula uma execução bem-sucedida do ffmpeg
    mock_subprocess.returncode = 0

    # Act
    worker.process_message(str(media_item_id))

    # Assert
    # 1. Verifica as chamadas ao BD
    calls = [
        call("UPDATE media_items SET status = 'normalizing' WHERE id = %s;", (media_item_id,)),
        call("SELECT original_file_path FROM media_items WHERE id = %s;", (media_item_id,)),
        call("UPDATE media_items SET file_path = %s, status = %s WHERE id = %s;", ('/mnt/media/normalized/video.mp4', 'pending_analysis', media_item_id))
    ]
    mock_cur.execute.assert_has_calls(calls, any_order=False)
    # O commit é chamado duas vezes neste fluxo (após 'normalizing' e após o sucesso)
    assert mock_conn.commit.call_count == 2

    # 2. Verifica a chamada ao ffmpeg
    mock_subprocess.wait.assert_called_once()

    # 3. Verifica a publicação na próxima fila
    mock_rabbitmq_client.publish_message.assert_called_once_with('scene_analysis_jobs', str(media_item_id))


def test_process_message_ffmpeg_fails(mock_db_connection, mock_rabbitmq_client, mock_subprocess):
    """
    Testa o cenário de falha onde o ffmpeg retorna um código de erro.
    Verifica se o status no BD é atualizado para 'normalization_failed' e nenhuma mensagem é publicada.
    """
    # Arrange
    media_item_id = 2
    original_path = "/path/to/source/corrupted_video.avi"

    mock_conn, mock_cur = mock_db_connection
    mock_cur.fetchone.return_value = (original_path,)

    # Simula uma falha na execução do ffmpeg
    mock_subprocess.returncode = 1

    # Act
    worker.process_message(str(media_item_id))

    # Assert
    # 1. Verifica as chamadas ao BD
    calls = [
        call("UPDATE media_items SET status = 'normalizing' WHERE id = %s;", (media_item_id,)),
        call("SELECT original_file_path FROM media_items WHERE id = %s;", (media_item_id,)),
        call("UPDATE media_items SET status = %s WHERE id = %s;", ('normalization_failed', media_item_id))
    ]
    mock_cur.execute.assert_has_calls(calls, any_order=False)
    # O commit é chamado duas vezes neste fluxo (após 'normalizing' e após a falha)
    assert mock_conn.commit.call_count == 2

    # 2. Verifica a chamada ao ffmpeg
    mock_subprocess.wait.assert_called_once()

    # 3. Garante que nenhuma mensagem foi publicada
    mock_rabbitmq_client.publish_message.assert_not_called()
