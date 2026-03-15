import pandas as pd

def calculate_kda(participant_data):
    kills = participant_data['kills']
    deaths = participant_data['deaths']
    assists = participant_data['assists']
    return (kills + assists) / max(1, deaths)

def get_team_stats(match_data, team_puuids):
    """
    Extracts stats for the specific team of 5 players from a match.
    """
    participants = match_data['info']['participants']
    team_puuids_set = set(team_puuids)

    # Calculate Team Totals for shares
    team_total_kills = sum(p['kills'] for p in participants if p['puuid'] in team_puuids_set)
    team_total_damage = sum(p['totalDamageDealtToChampions'] for p in participants if p['puuid'] in team_puuids_set)
    team_total_gold = sum(p['goldEarned'] for p in participants if p['puuid'] in team_puuids_set)

    game_duration_seconds = match_data['info']['gameDuration']
    game_duration_minutes = game_duration_seconds / 60.0

    # Filter for our team
    team_stats = []
    for p in participants:
        if p['puuid'] in team_puuids_set:
            # Basic Stats
            kills = p['kills']
            deaths = p['deaths']
            assists = p['assists']
            damage = p['totalDamageDealtToChampions']
            gold = p['goldEarned']
            cs = p['totalMinionsKilled'] + p['neutralMinionsKilled']
            vision = p['visionScore']
            
            # Handle Riot ID vs Summoner Name
            name = p.get('riotIdGameName')
            if not name:
                 name = p.get('summonerName')
            
            # Append Tag Line if available and using Riot ID
            if p.get('riotIdGameName') and p.get('riotIdTagLine'):
                name = f"{name}#{p.get('riotIdTagLine')}"

            stats = {
                'summonerName': name,
                'championName': p['championName'],
                'role': p.get('teamPosition', 'UNKNOWN'),
                'win': p['win'],
                'kda_ratio': calculate_kda(p),
                'kills': kills,
                'deaths': deaths,
                'assists': assists,
                'cs': cs,
                'gold': gold,
                'damage': damage,
                'vision': vision,
                # Advanced Stats
                'dpm': damage / game_duration_minutes if game_duration_minutes > 0 else 0,
                'dpg': damage / gold if gold > 0 else 0,
                'cspm': cs / game_duration_minutes if game_duration_minutes > 0 else 0,
                'vspm': vision / game_duration_minutes if game_duration_minutes > 0 else 0,
                'kp_%': ((kills + assists) / team_total_kills * 100) if team_total_kills > 0 else 0,
                'dmg_%': (damage / team_total_damage * 100) if team_total_damage > 0 else 0,
                'gold_%': (gold / team_total_gold * 100) if team_total_gold > 0 else 0,
            }
            team_stats.append(stats)
            
    return pd.DataFrame(team_stats)
