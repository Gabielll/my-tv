# scheduler_ai/engine.py

import datetime

def apply_series_linear_rule(rule, media_items, current_time):
    """
    Aplica a regra 'series_linear': encontra e agenda o próximo episódio de uma série.
    """
    rule_details = rule['rules']['series_linear']
    series_title = rule_details['title']

    # Encontra o estado atual do episódio para esta série
    program_state = rule.get('program_state', {})
    series_state = program_state.get('series_linear', {}).get(series_title, {})
    current_episode = series_state.get('current_episode', 1)
    current_season = series_state.get('current_season', 1)

    # Filtra os media_items para encontrar o próximo episódio da série
    next_episode_item = None
    for item in media_items:
        meta = item.get('metadata', {})
        if (meta.get('series_title') == series_title and
            meta.get('season_number') == current_season and
            meta.get('episode_number') == current_episode):
            next_episode_item = item
            break

    if not next_episode_item:
        # Lógica para reiniciar a série ou marcar como concluída pode ser adicionada aqui
        return None, None

    # Calcula o horário de início e fim
    start_time = current_time.replace(
        hour=rule_details['time_slot']['hour'],
        minute=rule_details['time_slot']['minute'],
        second=0,
        microsecond=0
    )
    duration_seconds = next_episode_item['metadata'].get('duration_seconds', 1800) # Padrão de 30 min
    end_time = start_time + datetime.timedelta(seconds=duration_seconds)

    # Cria a entrada do EPG
    epg_entry = {
        'channel_id': rule['channel_id'],
        'media_item_id': next_episode_item['id'],
        'start_time_virtual': start_time,
        'end_time_virtual': end_time,
        'title': next_episode_item['title'],
        'synopsis': next_episode_item.get('synopsis')
    }

    # Prepara o estado atualizado para ser salvo no banco de dados
    updated_state = {
        'series_linear': {
            series_title: {
                'current_season': current_season,
                'current_episode': current_episode + 1
            }
        }
    }

    return epg_entry, updated_state


def process_scheduling_rules(rules, media_items):
    """
    Processa uma lista de regras de agendamento e gera a grade de programação.
    """
    print("Scheduling engine started...")
    epg_entries = []
    updated_states = {}

    # Define um ponto de partida para a programação (hoje)
    start_of_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for rule in rules:
        # Por enquanto, estamos agendando para hoje, um item por regra.
        # A lógica para agendar múltiplos dias e múltiplos itens virá depois.
        current_scheduling_time = start_of_day

        if 'series_linear' in rule.get('rules', {}):
            epg_entry, state = apply_series_linear_rule(rule, media_items, current_scheduling_time)
            if epg_entry:
                epg_entries.append(epg_entry)
                updated_states[rule['id']] = state

    print(f"Scheduling engine finished. Generated {len(epg_entries)} EPG entries.")
    return epg_entries, updated_states
