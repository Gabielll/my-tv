# scheduler_ai/tests/test_engine.py
import pytest
from unittest.mock import MagicMock
import datetime

from scheduler_ai import engine

def test_apply_series_linear_rule_finds_next_episode():
    """
    Testa se a regra 'series_linear' encontra o episódio correto e gera a EPG.
    """
    # Dados de exemplo
    rule = {
        'id': 1,
        'channel_id': 'jetix_2000',
        'rules': {
            'series_linear': {
                'title': 'Power Rangers',
                'time_slot': {'hour': 17, 'minute': 30}
            }
        },
        'program_state': {
            'series_linear': {
                'Power Rangers': {'current_season': 1, 'current_episode': 2}
            }
        }
    }
    media_items = [
        {'id': 1, 'title': 'Power Rangers S01E01', 'metadata': {'series_title': 'Power Rangers', 'season_number': 1, 'episode_number': 1, 'duration_seconds': 1200}},
        {'id': 2, 'title': 'Power Rangers S01E02', 'metadata': {'series_title': 'Power Rangers', 'season_number': 1, 'episode_number': 2, 'duration_seconds': 1200}},
        {'id': 3, 'title': 'Power Rangers S01E03', 'metadata': {'series_title': 'Power Rangers', 'season_number': 1, 'episode_number': 3, 'duration_seconds': 1200}},
    ]
    start_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Chama a função
    epg_entry, updated_state = engine.apply_series_linear_rule(rule, media_items, start_time)

    # Verifica o EPG
    assert epg_entry is not None
    assert epg_entry['media_item_id'] == 2
    assert epg_entry['start_time_virtual'].hour == 17
    assert epg_entry['start_time_virtual'].minute == 30

    # Verifica a atualização do estado
    assert updated_state is not None
    assert updated_state['series_linear']['Power Rangers']['current_episode'] == 3
