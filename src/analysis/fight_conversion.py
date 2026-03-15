from src.analysis.teamfights import detect_teamfights, analyze_teamfight


def get_objective_events(timeline, pid_to_team):
    """
    Extracts objective events (elite monsters + buildings) from the timeline.
    Returns list of {timestamp, type, team_id}.
    """
    objectives = []

    for frame in timeline['info']['frames']:
        for event in frame.get('events', []):
            if event['type'] == 'ELITE_MONSTER_KILL':
                killer_id = event.get('killerId', 0)
                team_id = pid_to_team.get(killer_id, 0)
                objectives.append({
                    'timestamp': event['timestamp'],
                    'type': event.get('monsterType', 'UNKNOWN'),
                    'team_id': team_id,
                })
            elif event['type'] == 'BUILDING_KILL':
                # For buildings, teamId is directly on the event
                team_id = event.get('teamId', 0)
                # teamId in BUILDING_KILL is the team that LOST the building,
                # so the team that destroyed it is the other team
                destroying_team = 200 if team_id == 100 else 100
                building = event.get('buildingType', 'UNKNOWN')
                objectives.append({
                    'timestamp': event['timestamp'],
                    'type': building,
                    'team_id': destroying_team,
                })

    return objectives


def analyze_fight_conversion(timeline, match_data, team_participant_ids):
    """
    For each teamfight, checks if the winning side took an objective within 60s.
    Returns dict with per-fight details and overall conversion rates.
    """
    team_pids = set(team_participant_ids)
    participants = match_data['info']['participants']

    # Determine our team ID
    our_team_id = None
    for p in participants:
        if p['participantId'] in team_pids:
            our_team_id = p['teamId']
            break
    if our_team_id is None:
        return {'fights': [], 'team_conversion_rate': 0, 'enemy_conversion_rate': 0}

    # Build pid -> team mapping
    pid_to_team = {}
    for p in participants:
        pid_to_team[p['participantId']] = p['teamId']

    obj_events = get_objective_events(timeline, pid_to_team)
    teamfight_clusters = detect_teamfights(timeline, match_data)

    fights = []
    team_wins = 0
    team_conversions = 0
    enemy_wins = 0
    enemy_conversions = 0

    conversion_window = 60000  # 60 seconds

    for idx, tf_kills in enumerate(teamfight_clusters):
        tf_data = analyze_teamfight(tf_kills, timeline, match_data, list(team_pids))
        fight_end = tf_data['end_time']
        outcome = tf_data['outcome']

        # Find objectives taken within 60s after fight end
        objs_after = [
            o for o in obj_events
            if fight_end <= o['timestamp'] <= fight_end + conversion_window
        ]

        team_objs = [o for o in objs_after if o['team_id'] == our_team_id]
        enemy_objs = [o for o in objs_after if o['team_id'] != our_team_id and o['team_id'] != 0]

        converted = False
        converted_objectives = []

        if outcome == "Won":
            team_wins += 1
            if team_objs:
                team_conversions += 1
                converted = True
                converted_objectives = [o['type'] for o in team_objs]
        elif outcome == "Lost":
            enemy_wins += 1
            if enemy_objs:
                enemy_conversions += 1
                converted = True
                converted_objectives = [o['type'] for o in enemy_objs]

        fights.append({
            'fight_num': idx + 1,
            'time': f"{tf_data['start_time'] / 60000:.1f}m",
            'outcome': outcome,
            'score': f"{tf_data['team_kills']}v{tf_data['enemy_kills']}",
            'converted': converted,
            'objectives': ', '.join(converted_objectives) if converted_objectives else '-',
        })

    team_rate = (team_conversions / team_wins * 100) if team_wins > 0 else 0
    enemy_rate = (enemy_conversions / enemy_wins * 100) if enemy_wins > 0 else 0

    return {
        'fights': fights,
        'team_conversion_rate': round(team_rate, 1),
        'enemy_conversion_rate': round(enemy_rate, 1),
    }
