import pytest
from unittest.mock import MagicMock, call
import sys
import os

from scene_analyzer import analyzer


@pytest.fixture
def mock_db_connection(mocker):
    """Fixture que simula a conexão com o banco de dados."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mocker.patch('scene_analyzer.analyzer.get_db_connection', return_value=mock_conn)
    return mock_conn, mock_cur

@pytest.fixture
def mock_subprocess(mocker):
    """Fixture que simula o subprocess.Popen usado pelo ffmpeg."""
    mock_proc = MagicMock()
    # A saída do blackdetect está no stderr, então simulamos `communicate` retornando (stdout, stderr)
    mocker.patch('subprocess.Popen', return_value=mock_proc)
    # Mock para a verificação de existência do arquivo para evitar erros de I/O
    mocker.patch('os.path.exists', return_value=True)
    return mock_proc

def test_analyze_scenes_success(mock_subprocess):
    """
    Testa se a função `analyze_scenes` extrai corretamente os timestamps da saída do ffmpeg.
    """
    # Arrange
    # Exemplo de saída do stderr do ffmpeg com o filtro blackdetect
    ffmpeg_output = """
    [blackdetect @ 0x55a4d2b2d3c0] black_start:10.5 black_end:12.0 black_duration:1.5
    [blackdetect @ 0x55a4d2b2d3c0] black_start:30.0 black_end:32.5 black_duration:2.5
    frame= 1226 fps=239 q=-0.0 Lsize=N/A time=00:00:51.21 bitrate=N/A speed=9.98x
    """
    mock_subprocess.communicate.return_value = ('', ffmpeg_output)

    # Act
    cue_points = analyzer.analyze_scenes("/fake/path/to/video.mp4")

    # Assert
    # 1. Verifica se o subprocesso foi chamado com os argumentos corretos
    mock_subprocess.communicate.assert_called_once()

    # 2. Verifica se os timestamps foram extraídos corretamente
    assert cue_points == [10.5, 30.0]

def test_analyze_scenes_no_breaks_found(mock_subprocess):
    """
    Testa o caso onde o ffmpeg não detecta nenhum 'break' (nenhuma linha com 'black_start').
    """
    # Arrange
    ffmpeg_output = """
    frame= 1226 fps=239 q=-0.0 Lsize=N/A time=00:00:51.21 bitrate=N/A speed=9.98x
    """
    mock_subprocess.communicate.return_value = ('', ffmpeg_output)

    # Act
    cue_points = analyzer.analyze_scenes("/fake/path/to/video.mp4")

    # Assert
    assert cue_points == []

def test_analyze_scenes_ffmpeg_not_found(mocker):
    """
    Testa se a função retorna uma lista vazia se o comando ffmpeg não for encontrado.
    """
    # Arrange
    # O mocker levanta um FileNotFoundError quando Popen é chamado
    mocker.patch('subprocess.Popen', side_effect=FileNotFoundError("ffmpeg not found"))

    # Act
    cue_points = analyzer.analyze_scenes("/fake/path/to/video.mp4")

    # Assert
    assert cue_points == []

@pytest.mark.parametrize("file_exists", [True, False])
def test_analyze_scenes_file_existence(mocker, file_exists):
    """
    Testa se a função verifica a existência do arquivo de entrada.
    """
    # Arrange
    mocker.patch('os.path.exists', return_value=file_exists)
    mock_popen = mocker.patch('subprocess.Popen')

    # Act
    analyzer.analyze_scenes("/some/path")

    # Assert
    if file_exists:
        # Se o arquivo existe, o ffmpeg deve ser chamado
        mock_popen.assert_called_once()
    else:
        # Se o arquivo não existe, o ffmpeg não deve ser chamado
        mock_popen.assert_not_called()


# --- Testes de Integração para process_message ---

def test_process_message_success(mock_db_connection, mocker):
    """
    Testa o fluxo de sucesso de 'process_message', onde pontos de corte são encontrados e salvos.
    """
    # Arrange
    media_item_id = 1
    normalized_path = "/path/to/normalized/video.mp4"

    mock_conn, mock_cur = mock_db_connection
    mock_cur.fetchone.return_value = (normalized_path,)

    # Mock a função 'analyze_scenes' para retornar pontos de corte
    mock_analyze = mocker.patch('scene_analyzer.analyzer.analyze_scenes', return_value=[10.5, 30.0])

    # Act
    analyzer.process_message(str(media_item_id))

    # Assert
    # 1. Verifica as chamadas ao BD
    calls = [
        call("UPDATE media_items SET status = 'analyzing' WHERE id = %s;", (media_item_id,)),
        call("SELECT file_path FROM media_items WHERE id = %s;", (media_item_id,)),
        call("INSERT INTO cue_points (media_item_id, cue_time, cue_type) VALUES (%s, %s, %s);", (media_item_id, 10.5, 'commercial_break')),
        call("INSERT INTO cue_points (media_item_id, cue_time, cue_type) VALUES (%s, %s, %s);", (media_item_id, 30.0, 'commercial_break')),
        call("UPDATE media_items SET status = %s WHERE id = %s;", ('processed', media_item_id))
    ]
    mock_cur.execute.assert_has_calls(calls, any_order=False)
    assert mock_conn.commit.call_count == 2 # Um commit após 'analyzing', outro no final

    # 2. Verifica se 'analyze_scenes' foi chamada
    mock_analyze.assert_called_once_with(normalized_path)


def test_process_message_no_cue_points(mock_db_connection, mocker):
    """
    Testa o fluxo onde 'analyze_scenes' não retorna pontos de corte.
    O status final ainda deve ser 'complete'.
    """
    # Arrange
    media_item_id = 2
    normalized_path = "/path/to/normalized/another_video.mp4"

    mock_conn, mock_cur = mock_db_connection
    mock_cur.fetchone.return_value = (normalized_path,)

    # Mock a função 'analyze_scenes' para não retornar nenhum ponto de corte
    mock_analyze = mocker.patch('scene_analyzer.analyzer.analyze_scenes', return_value=[])

    # Act
    analyzer.process_message(str(media_item_id))

    # Assert
    # 1. Verifica as chamadas ao BD
    calls = [
        call("UPDATE media_items SET status = 'analyzing' WHERE id = %s;", (media_item_id,)),
        call("SELECT file_path FROM media_items WHERE id = %s;", (media_item_id,)),
        call("UPDATE media_items SET status = %s WHERE id = %s;", ('processed', media_item_id))
    ]
    mock_cur.execute.assert_has_calls(calls, any_order=False)

    # 2. Nenhuma chamada de INSERT para cue_points deve ter sido feita
    for c in mock_cur.execute.call_args_list:
        assert "INSERT INTO cue_points" not in c.args[0]
