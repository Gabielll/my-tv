import pytest
from admin_ui.app import app as flask_app
import io

@pytest.fixture
def client():
    """Fixture que configura a aplicação Flask para testes e fornece um cliente de teste."""
    flask_app.config['TESTING'] = True
    # Aponta o UPLOAD_FOLDER para um diretório temporário (embora não será usado com mocks)
    flask_app.config['UPLOAD_FOLDER'] = '/tmp/test_uploads'
    with flask_app.test_client() as client:
        yield client

def test_index_route(client):
    """Testa se a rota raiz ('/') retorna a página inicial com sucesso."""
    response = client.get('/')
    assert response.status_code == 200
    # A verificação do conteúdo foi removida pois o index agora é um layout
    assert b'<nav class="navbar' in response.data

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

def test_list_rules_route(client, mocker):
    """
    Testa se a rota '/admin/rules' carrega com sucesso e exibe os dados.
    """
    # Arrange: Mock da conexão com o banco de dados
    mock_conn = mocker.patch('admin_ui.app.get_db_connection')
    mock_cursor = mock_conn.return_value.cursor.return_value.__enter__.return_value

    # Simula o retorno do banco de dados
    mock_rules = [
        {'id': 1, 'channel_id': 'jetix_2000', 'channel_name': 'Jetix', 'is_active': True},
        {'id': 2, 'channel_id': 'retro_tv', 'channel_name': 'Retro TV', 'is_active': False},
    ]
    mock_cursor.fetchall.return_value = mock_rules

    # Act
    response = client.get('/admin/rules')

    # Assert
    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert "<h2>Gerenciar Regras de Agendamento</h2>" in response_text
    assert "jetix_2000" in response_text
    assert '<span class="badge badge-success">Ativo</span>' in response_text
    assert "retro_tv" in response_text
    assert '<span class="badge badge-secondary">Inativo</span>' in response_text
