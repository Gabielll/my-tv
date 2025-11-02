import sys
import os
import pytest
from unittest.mock import MagicMock

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa o módulo que será testado
from scheduler_ai import scheduler

def test_fetch_scheduling_rules(mocker):
    """
    Testa se a função fetch_scheduling_rules executa a consulta SQL correta.
    """
    # Cria um mock para a conexão com o banco de dados
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Configura o mock do cursor para retornar um resultado simulado
    mock_cursor.fetchall.return_value = [
        {"id": 1, "channel": "jetix_2000", "rule_type": "series_linear"},
        {"id": 2, "channel": "retro_tv", "rule_type": "flexible_theme"}
    ]

    # Configura o gerenciador de contexto 'with' para retornar o mock do cursor
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Chama a função que está sendo testada
    rules = scheduler.fetch_scheduling_rules(mock_conn)

    # Verifica se a consulta SQL correta foi executada
    mock_cursor.execute.assert_called_once_with("SELECT * FROM channel_master_grid;")

    # Verifica se o resultado retornado está correto
    assert len(rules) == 2
    assert rules[0]["channel"] == "jetix_2000"
    assert rules[1]["rule_type"] == "flexible_theme"

def test_fetch_media_items(mocker):
    """
    Testa se a função fetch_media_items executa a consulta SQL correta.
    """
    # Cria um mock para a conexão com o banco de dados
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Configura o mock do cursor para retornar um resultado simulado
    mock_cursor.fetchall.return_value = [
        {"id": 1, "title": "Power Rangers S01E01", "status": "processed"},
        {"id": 2, "title": "Power Rangers S01E02", "status": "processed"}
    ]

    # Configura o gerenciador de contexto 'with' para retornar o mock do cursor
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Chama a função que está sendo testada
    media_items = scheduler.fetch_media_items(mock_conn)

    # Verifica se a consulta SQL correta foi executada
    mock_cursor.execute.assert_called_once_with("SELECT * FROM media_items WHERE status = 'processed';")

    # Verifica se o resultado retornado está correto
    assert len(media_items) == 2
    assert media_items[0]["title"] == "Power Rangers S01E01"

def test_initial():
    """
    Teste inicial para garantir que o ambiente de teste está funcionando.
    """
    assert True
