import math
import pandas as pd


def detect_teamfights(timeline, match_data):
    """
    Detects teamfights by clustering CHAMPION_KILL events.
    A teamfight is defined as 3+ kills within a 15-second window and 4000 unit radius.
    """
    kills = []
    for frame in timeline['info']['frames']:
        for event in frame.get('events', []):
            if event['type'] == 'CHAMPION_KILL':
                pos = event.get('position', {})
                kills.append({
                    'timestamp': event['timestamp'],
                    'x': pos.get('x', 0),
                    'y': pos.get('y', 0),
                    'killerId': event.get('killerId'),
                    'victimId': event.get('victimId'),
                    'assistingParticipantIds': event.get('assistingParticipantIds', []),
                })

    if len(kills) < 3:
        return []

    # Sort by time
    kills.sort(key=lambda k: k['timestamp'])

    # Cluster kills
    teamfights = []
    used = set()

    for i, k in enumerate(kills):
        if i in used:
            continue
        cluster = [k]
        used.add(i)

        for j in range(i + 1, len(kills)):
            if j in used:
                continue
            candidate = kills[j]
            # Time window: 15 seconds from any kill in the cluster
            time_ok = (candidate['timestamp'] - cluster[-1]['timestamp']) <= 15000
            # Distance: within 4000 units of any kill in the cluster
            dist_ok = any(
                math.sqrt((candidate['x'] - c['x'])**2 + (candidate['y'] - c['y'])**2) <= 4000
                for c in cluster
            )
            if time_ok and dist_ok:
                cluster.append(candidate)
                used.add(j)

        if len(cluster) >= 3:
            teamfights.append(cluster)

    return teamfights


def analyze_teamfight(teamfight_kills, timeline, match_data, team_participant_ids):
    """
    Analyzes a single teamfight cluster.
    Returns summary dict with outcome, kill breakdown, and participants.
    """
    participants = match_data['info']['participants']
    team_pids = set(team_participant_ids)
    enemy_pids = set(p['participantId'] for p in participants) - team_pids

    start_ts = teamfight_kills[0]['timestamp']
    end_ts = teamfight_kills[-1]['timestamp']
    center_x = sum(k['x'] for k in teamfight_kills) / len(teamfight_kills)
    center_y = sum(k['y'] for k in teamfight_kills) / len(teamfight_kills)

    # Count kills per side
    team_kills = 0
    enemy_kills = 0
    team_deaths = 0
    enemy_deaths = 0
    
    team_involved = set()
    enemy_involved = set()

    for k in teamfight_kills:
        killer = k['killerId']
        victim = k['victimId']
        assisters = k.get('assistingParticipantIds', [])

        if killer in team_pids:
            team_kills += 1
        elif killer in enemy_pids:
            enemy_kills += 1

        if victim in team_pids:
            team_deaths += 1
        elif victim in enemy_pids:
            enemy_deaths += 1

        # Track participants involved
        if killer in team_pids:
            team_involved.add(killer)
        elif killer in enemy_pids:
            enemy_involved.add(killer)
        if victim in team_pids:
            team_involved.add(victim)
        elif victim in enemy_pids:
            enemy_involved.add(victim)
        for a in assisters:
            if a in team_pids:
                team_involved.add(a)
            elif a in enemy_pids:
                enemy_involved.add(a)

    # Determine outcome
    if team_kills > enemy_kills:
        outcome = "Won"
    elif enemy_kills > team_kills:
        outcome = "Lost"
    else:
        outcome = "Even"

    # Map participant IDs to names
    pid_to_info = {}
    for p in participants:
        pid_to_info[p['participantId']] = {
            'name': p.get('riotIdGameName', p.get('summonerName', '?')),
            'champion': p['championName'],
        }

    # Find who engaged (first kill or assist)
    first_kill = teamfight_kills[0]
    engager_id = first_kill['killerId']
    engager_info = pid_to_info.get(engager_id, {'name': '?', 'champion': '?'})
    engaged_by_team = engager_id in team_pids

    # Get names of involved players
    team_names = [f"{pid_to_info.get(pid, {}).get('name', '?')} ({pid_to_info.get(pid, {}).get('champion', '?')})" for pid in team_involved]
    
    return {
        'start_time': start_ts,
        'end_time': end_ts,
        'duration_s': (end_ts - start_ts) / 1000,
        'center_x': center_x,
        'center_y': center_y,
        'outcome': outcome,
        'team_kills': team_kills,
        'enemy_kills': enemy_kills,
        'team_deaths': team_deaths,
        'enemy_deaths': enemy_deaths,
        'team_involved': list(team_involved),
        'enemy_involved': list(enemy_involved),
        'team_names': team_names,
        'total_kills': len(teamfight_kills),
        'engager': engager_info,
        'engaged_by_team': engaged_by_team,
    }
