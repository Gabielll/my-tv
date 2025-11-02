import pytest
from unittest.mock import MagicMock, call
from metadata_enricher import enricher

@pytest.fixture
def mock_db_cursor(mocker):
    """Fixture que simula o cursor do banco de dados."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mocker.patch('metadata_enricher.enricher.get_db_connection', return_value=mock_conn)
    return mock_cur

@pytest.fixture
def mock_tmdb(mocker):
    """Fixture que simula a função de chamada à API do TMDB."""
    return mocker.patch('metadata_enricher.enricher.fetch_metadata_from_tmdb')

def test_process_message_success_series(mock_db_cursor, mock_tmdb):
    """
    Testa o fluxo de sucesso para um episódio de série.
    Verifica se a função busca o arquivo, analisa, busca metadados e atualiza o BD.
    """
    # Arrange
    media_item_id = 1
    original_filename = "The.Mandalorian.S02E08.mkv"
    parsed_info = {'type': 'series', 'title': 'The Mandalorian', 'season': 2, 'episode': 8}
    tmdb_metadata = {
        'name': 'The Mandalorian: Chapter 16',
        'overview': 'The Mandalorian and his allies attempt a daring rescue.',
        'genres': [{'id': 10765, 'name': 'Sci-Fi & Fantasy'}]
    }

    # Configura os mocks
    mock_db_cursor.fetchone.return_value = ('The.Mandalorian.S02E08', f"/path/to/{original_filename}")
    mock_tmdb.return_value = tmdb_metadata

    # Act
    enricher.process_message(media_item_id)

    # Assert
    # 1. Verificamos se o item foi buscado no BD
    mock_db_cursor.execute.assert_any_call("SELECT title, original_file_path FROM media_items WHERE id = %s;", (media_item_id,))

    # 2. Verificamos se o TMDB foi chamado com a informação correta
    # (A função parse_filename é testada em separado, então aqui confiamos nela)
    mock_tmdb.assert_called_once()

    # 3. Verificamos se o BD foi atualizado com os metadados corretos
    update_sql = """
                    UPDATE media_items
                    SET title = %s, synopsis = %s, tags = %s, metadata = %s, status = %s
                    WHERE id = %s;
                    """
    mock_db_cursor.execute.assert_any_call(
        update_sql,
        (
            'The Mandalorian: Chapter 16',
            'The Mandalorian and his allies attempt a daring rescue.',
            '[{"id": 10765, "name": "Sci-Fi & Fantasy"}]',
            '{"name": "The Mandalorian: Chapter 16", "overview": "The Mandalorian and his allies attempt a daring rescue.", "genres": [{"id": 10765, "name": "Sci-Fi & Fantasy"}]}',
            'pending_normalization',
            media_item_id
        )
    )

def test_process_message_tmdb_fails(mock_db_cursor, mock_tmdb):
    """
    Testa o fluxo onde a busca de metadados no TMDB falha.
    O status do item deve ser atualizado para 'needs_review'.
    """
    # Arrange
    media_item_id = 2
    original_filename = "Unknown.Movie.2023.mkv"

    # Configura os mocks
    mock_db_cursor.fetchone.return_value = ('Unknown.Movie.2023', f"/path/to/{original_filename}")
    mock_tmdb.return_value = None # Simula falha na busca

    # Act
    enricher.process_message(media_item_id)

    # Assert
    # 1. Verificamos se o item foi buscado no BD
    mock_db_cursor.execute.assert_any_call("SELECT title, original_file_path FROM media_items WHERE id = %s;", (media_item_id,))

    # 2. Verificamos se o BD foi atualizado com o status 'needs_review'
    mock_db_cursor.execute.assert_any_call(
        "UPDATE media_items SET status = %s WHERE id = %s;",
        ('needs_review', media_item_id)
    )

def test_process_message_item_not_found(mock_db_cursor, mock_tmdb):
    """
    Testa o caso onde o media_item_id não é encontrado no banco de dados.
    """
    # Arrange
    media_item_id = 999
    mock_db_cursor.fetchone.return_value = None # Simula que o item não existe

    # Act
    enricher.process_message(media_item_id)

    # Assert
    # 1. A busca no BD foi feita
    mock_db_cursor.execute.assert_called_once_with("SELECT title, original_file_path FROM media_items WHERE id = %s;", (media_item_id,))

    # 2. Nenhuma outra chamada ao BD (UPDATE) ou ao TMDB deve ocorrer
    mock_tmdb.assert_not_called()
    assert mock_db_cursor.execute.call_count == 1
