import sys
import os
import pytest
import io

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from admin_ui import app as flask_app

@pytest.fixture
def client():
    """Fixture que configura a aplicação Flask para testes e fornece um cliente de teste."""
    flask_app.app.config['TESTING'] = True
    # Aponta o UPLOAD_FOLDER para um diretório temporário (embora não será usado com mocks)
    flask_app.app.config['UPLOAD_FOLDER'] = '/tmp/test_uploads'
    with flask_app.app.test_client() as client:
        yield client

def test_index_route(client):
    """Testa se a rota raiz ('/') retorna a página inicial com sucesso."""
    response = client.get('/')
    assert response.status_code == 200
    assert "<h1>Upload de Mídia</h1>" in response.data.decode('utf-8')

def test_upload_success_single_file(client, mocker):
    """
    Testa o upload bem-sucedido de um único arquivo com extensão permitida.
    """
    # Arrange
    mocker.patch('os.makedirs') # Mock para não criar diretórios
    mock_save = mocker.patch('werkzeug.datastructures.FileStorage.save')

    data = {
        'mediafiles': (io.BytesIO(b"dummy file content"), 'test_video.mp4')
    }

    # Act
    response = client.post('/upload', content_type='multipart/form-data', data=data)

    # Assert
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['message'] == "Todos os 1 arquivos foram enviados com sucesso!"
    mock_save.assert_called_once() # Verifica se o método save foi chamado

def test_upload_success_multiple_files(client, mocker):
    """
    Testa o upload bem-sucedido de múltiplos arquivos.
    """
    # Arrange
    mocker.patch('os.makedirs')
    mock_save = mocker.patch('werkzeug.datastructures.FileStorage.save')

    data = {
        'mediafiles': [
            (io.BytesIO(b"content1"), 'video1.mkv'),
            (io.BytesIO(b"content2"), 'video2.mov')
        ]
    }

    # Act
    response = client.post('/upload', content_type='multipart/form-data', data=data)

    # Assert
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['message'] == "Todos os 2 arquivos foram enviados com sucesso!"
    assert mock_save.call_count == 2

def test_upload_disallowed_extension(client, mocker):
    """
    Testa a falha de upload quando um arquivo tem uma extensão não permitida.
    """
    # Arrange
    mocker.patch('os.makedirs')
    mock_save = mocker.patch('werkzeug.datastructures.FileStorage.save')

    data = {
        'mediafiles': (io.BytesIO(b"this is a text file"), 'document.txt')
    }

    # Act
    response = client.post('/upload', content_type='multipart/form-data', data=data)

    # Assert
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['error'] == "Nenhum arquivo válido foi processado"
    assert "Extensão de arquivo não permitida" in json_data['details']['document.txt']
    mock_save.assert_not_called()

def test_upload_no_file_selected(client):
    """
    Testa a resposta do servidor quando o formulário é enviado sem nenhum arquivo.
    """
    # Arrange
    data = {
        'mediafiles': (io.BytesIO(b""), '') # O navegador envia isso quando nenhum arquivo é selecionado
    }

    # Act
    response = client.post('/upload', content_type='multipart/form-data', data=data)

    # Assert
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['error'] == "Nenhum arquivo selecionado"

def test_upload_no_file_part(client):
    """
    Testa a resposta do servidor quando a requisição não contém a parte 'mediafiles'.
    """
    # Act
    response = client.post('/upload', content_type='multipart/form-data', data={})

    # Assert
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['error'] == "Nenhum arquivo enviado"
