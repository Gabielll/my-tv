import pytest
from unittest.mock import MagicMock
from scene_analyzer import analyzer

@pytest.fixture
def mock_subprocess(mocker):
    """Fixture que simula o subprocess.Popen usado pelo ffmpeg."""
    mock_proc = MagicMock()
    # A saída do blackdetect está no stderr, então simulamos `communicate` retornando (stdout, stderr)
    mocker.patch('subprocess.Popen', return_value=mock_proc)
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
