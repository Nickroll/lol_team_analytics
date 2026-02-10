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
    
    # Filter for our team
    team_stats = []
    for p in participants:
        if p['puuid'] in team_puuids:
            stats = {
                'summonerName': p['summonerName'],
                'championName': p['championName'],
                'win': p['win'],
                'kills': p['kills'],
                'deaths': p['deaths'],
                'assists': p['assists'],
                'kda': calculate_kda(p),
                'totalMinionsKilled': p['totalMinionsKilled'],
                'neutralMinionsKilled': p['neutralMinionsKilled'], # Jungle CS
                'goldEarned': p['goldEarned'],
                'visionScore': p['visionScore'],
                'damageDealtToChampions': p['totalDamageDealtToChampions'],
                'role': p.get('teamPosition', 'UNKNOWN')
            }
            team_stats.append(stats)
            
    return pd.DataFrame(team_stats)
