import math
import pandas as pd


def analyze_objective_setup(timeline, objective_event, team_participant_ids):
    """
    Analyzes vision control and lane priority before an objective spawn/take.
    """
    timestamp = objective_event['timestamp']
    setup_window_start = max(0, timestamp - 60000)  # 60s before

    wards_placed = 0

    obj_type = objective_event.get('monsterType', '')
    target_pos = None
    if obj_type == 'DRAGON':
        target_pos = {'x': 9866, 'y': 4414}
    elif obj_type == 'BARON_NASHOR':
        target_pos = {'x': 5007, 'y': 10471}
    elif obj_type == 'RIFTHERALD':
        target_pos = {'x': 5007, 'y': 10471}

    if target_pos:
        for frame in timeline['info']['frames']:
            if frame['timestamp'] >= setup_window_start and frame['timestamp'] <= timestamp:
                for event in frame['events']:
                    if event['type'] == 'WARD_PLACED' and event.get('creatorId') in team_participant_ids:
                        wards_placed += 1

    return {
        'wards_placed_60s': wards_placed,
        'has_prio': False
    }


def detect_objective_throw(timeline, match_data, team_participant_ids):
    """
    Identifies if a team lost an objective fight while having a significant gold lead
    or numbers advantage near the objective.
    
    A "throw" is when:
      - Enemy secured an elite monster
      - AND your team had ≥1500 gold lead OR ≥1 alive advantage near the objective
    """
    throws = []
    participants = match_data['info']['participants']
    team_pids = set(team_participant_ids)
    
    # Build PID -> team mapping
    pid_to_team = {}
    our_team_id = None
    for p in participants:
        pid_to_team[p['participantId']] = p['teamId']
        if p['participantId'] in team_pids:
            our_team_id = p['teamId']
    
    if our_team_id is None:
        return throws

    # Build PID -> PUUID mapping from timeline
    pid_to_puuid = {}
    for p_info in timeline['info'].get('participants', []):
        pid_to_puuid[p_info['participantId']] = p_info['puuid']

    frames = timeline['info']['frames']

    for frame in frames:
        for event in frame.get('events', []):
            if event['type'] != 'ELITE_MONSTER_KILL':
                continue

            killer_id = event.get('killerId', 0)
            killer_team = pid_to_team.get(killer_id, 0)

            # Only care about objectives the ENEMY secured
            if killer_team == our_team_id or killer_team == 0:
                continue

            timestamp = event['timestamp']
            monster_type = event.get('monsterType', 'UNKNOWN')

            # Find the frame closest to this timestamp for gold data
            closest_frame = None
            for f in frames:
                if f['timestamp'] <= timestamp:
                    closest_frame = f
                else:
                    break

            if not closest_frame:
                continue

            # Calculate gold diff
            our_gold = 0
            enemy_gold = 0
            p_frames = closest_frame.get('participantFrames', {})
            for pid_str, pf in p_frames.items():
                pid = int(pid_str)
                total_gold = pf.get('totalGold', 0)
                if pid in team_pids:
                    our_gold += total_gold
                else:
                    enemy_gold += total_gold

            gold_lead = our_gold - enemy_gold

            # Check alive players near objective (within 3000 units)
            obj_pos = event.get('position', {})
            obj_x = obj_pos.get('x', 0)
            obj_y = obj_pos.get('y', 0)

            # Count players currently alive and near the objective
            # We check who was NOT dead at that frame
            dead_pids = set()
            # Look for recent deaths (within 30s before the event)
            death_window = 30000
            for f in frames:
                if f['timestamp'] < timestamp - death_window:
                    continue
                if f['timestamp'] > timestamp:
                    break
                for ev in f.get('events', []):
                    if ev['type'] == 'CHAMPION_KILL' and ev['timestamp'] <= timestamp:
                        dead_pids.add(ev.get('victimId'))

            our_alive_near = 0
            enemy_alive_near = 0
            for pid_str, pf in p_frames.items():
                pid = int(pid_str)
                if pid in dead_pids:
                    continue
                pos = pf.get('position', {})
                px, py = pos.get('x', 0), pos.get('y', 0)
                dist = math.sqrt((px - obj_x)**2 + (py - obj_y)**2)
                if dist <= 3000:
                    if pid in team_pids:
                        our_alive_near += 1
                    else:
                        enemy_alive_near += 1

            alive_advantage = our_alive_near - enemy_alive_near

            # Determine if this is a throw
            is_throw = gold_lead >= 1500 or alive_advantage >= 1

            if is_throw:
                reasons = []
                if gold_lead >= 1500:
                    reasons.append(f"+{gold_lead:,}g lead")
                if alive_advantage >= 1:
                    reasons.append(f"{our_alive_near}v{enemy_alive_near} near objective")
                
                throws.append({
                    'timestamp': timestamp,
                    'time_str': f"{timestamp / 60000:.1f}m",
                    'monster_type': monster_type,
                    'gold_lead': gold_lead,
                    'alive_advantage': alive_advantage,
                    'reasons': reasons,
                })

    return throws
