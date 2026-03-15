import math
import numpy as np
import pandas as pd

# Approximate outer tower positions (blue-side and red-side)
_BLUE_OUTER_TOWERS = [(1325, 10950), (5048, 4812), (10950, 1325)]
_RED_OUTER_TOWERS  = [(4530, 13870), (9560, 10076), (13870, 4530)]


def calculate_laning_diffs(timeline, participant_id, opponent_id):
    """
    Gold, CS, and XP difference vs lane opponent at 15 minutes.
    Positive values mean the player is ahead.
    """
    frames = timeline['info']['frames']
    target_idx = min(15, len(frames) - 1)
    frame = frames[target_idx]
    p_frames = frame.get('participantFrames', {})

    p   = p_frames.get(str(participant_id), {})
    opp = p_frames.get(str(opponent_id), {})

    gold_diff = p.get('totalGold', 0) - opp.get('totalGold', 0)
    cs_diff   = (p.get('minionsKilled', 0) + p.get('jungleMinionsKilled', 0)) - \
                (opp.get('minionsKilled', 0) + opp.get('jungleMinionsKilled', 0))
    xp_diff   = p.get('xp', 0) - opp.get('xp', 0)

    return {'gold_diff_15': gold_diff, 'cs_diff_15': cs_diff, 'xp_diff_15': xp_diff}


def classify_early_deaths(timeline, participant_id, enemy_jungler_id, is_blue_side):
    """
    Classifies pre-14 min deaths into:
      solo_kill   — killed 1v1 by laner only, no assists (pure mechanical loss)
      gank_death  — enemy jungler was the killer or an assister
      multi_death — 2+ enemies involved but jungler not among them (e.g. roaming mid)
      dive_death  — died within ~1500 units of an own outer tower (can overlap the above)

    Returns a dict with counts for each category.
    """
    frames = timeline['info']['frames']
    cutoff = 14 * 60 * 1000
    tower_list = _BLUE_OUTER_TOWERS if is_blue_side else _RED_OUTER_TOWERS
    threshold_sq = 1500 ** 2
    counts = {'solo_kill': 0, 'gank_death': 0, 'multi_death': 0, 'dive_death': 0}

    for frame in frames:
        if frame['timestamp'] > cutoff:
            break
        for event in frame.get('events', []):
            if event['type'] != 'CHAMPION_KILL' or event.get('victimId') != participant_id:
                continue

            killer  = event.get('killerId', 0)
            assists = event.get('assistingParticipantIds', [])
            all_enemies = set([killer] + assists) - {0}
            jungler_involved = bool(enemy_jungler_id and enemy_jungler_id in all_enemies)

            if jungler_involved:
                counts['gank_death'] += 1
            elif len(all_enemies) <= 1:
                counts['solo_kill'] += 1
            else:
                counts['multi_death'] += 1

            pos = event.get('position', {})
            if pos:
                x, y = pos.get('x', 0), pos.get('y', 0)
                if any((x - tx) ** 2 + (y - ty) ** 2 <= threshold_sq for tx, ty in tower_list):
                    counts['dive_death'] += 1

    return counts

def calculate_harass_score(timeline_data, participant_id):
    """
    Calculates Laning Phase Harass Score (0-14 min).
    (Damage Dealt / Damage Taken)
    """
    frames = timeline_data['info']['frames']
    cutoff = 14 * 60 * 1000
    
    target_frame = None
    for frame in frames:
        if frame['timestamp'] >= cutoff:
            target_frame = frame
            break
    
    if not target_frame:
        target_frame = frames[-1]
        
    p_frames = target_frame.get('participantFrames', {})
    p_frame = p_frames.get(str(participant_id))
    if not p_frame:
        return 0.0
        
    damage_stats = p_frame.get('damageStats', {})
    dealt = damage_stats.get('totalDamageDoneToChampions', 0)
    taken = damage_stats.get('totalDamageTaken', 0)
    
    if taken == 0:
        return float(dealt) if dealt > 0 else 0.0
        
    return round(float(dealt) / float(taken), 2)

def calculate_greed_index(timeline_data, participant_id, team_id):
    """
    Calculates Greed Index based on:
    1. Deep Deaths (Isolated in enemy territory)
    2. Gold Hoarding (Dying with > 1500 gold)
    3. Overstaying (Dying within 30s of a takedown)
    """
    frames = timeline_data['info']['frames']
    is_blue_side = (team_id == 100)
    deep_threshold_blue = 9000
    deep_threshold_red = 6000
    gold_hoard_threshold = 1500
    overstay_window_ms = 30 * 1000
    
    greedy_events = 0
    takedown_timestamps = []
    
    for frame in frames:
        p_frame = frame.get('participantFrames', {}).get(str(participant_id))
        current_gold = p_frame.get('currentGold', 0) if p_frame else 0
        
        for event in frame.get('events', []):
            if event['type'] == 'CHAMPION_KILL':
                # Track Takedowns
                if event.get('killerId') == participant_id or (event.get('assistingParticipantIds') and participant_id in event.get('assistingParticipantIds')):
                    takedown_timestamps.append(event['timestamp'])
                
                # Analyze Deaths
                if event.get('victimId') == participant_id:
                    death_ts = event['timestamp']
                    is_greedy = False
                    
                    # A. Deep Death
                    pos = event.get('position')
                    if pos:
                        x, y = pos['x'], pos['y']
                        if is_blue_side:
                            if x > deep_threshold_blue and y > deep_threshold_blue:
                                is_greedy = True
                        else:
                            if x < deep_threshold_red and y < deep_threshold_red:
                                is_greedy = True
                    
                    # B. Gold Hoarding
                    if current_gold > gold_hoard_threshold:
                        is_greedy = True
                        
                    # C. Overstay
                    for t_ts in takedown_timestamps:
                        if 0 <= (death_ts - t_ts) <= overstay_window_ms:
                            is_greedy = True
                            break
                    
                    if is_greedy:
                        greedy_events += 1
                        
    return greedy_events

def calculate_jungle_proximity(timeline_data, participant_id, jungler_id):
    if not jungler_id or participant_id == jungler_id:
        return 0.0
        
    frames = timeline_data['info']['frames']
    cutoff = 14 * 60 * 1000
    nearby_frames = 0
    total_frames = 0
    proximity_range = 2000
    
    for frame in frames:
        if frame['timestamp'] > cutoff:
            break
        total_frames += 1
        p_frame = frame.get('participantFrames', {}).get(str(participant_id))
        j_frame = frame.get('participantFrames', {}).get(str(jungler_id))
        
        if p_frame and j_frame and 'position' in p_frame and 'position' in j_frame:
            p_pos = p_frame['position']
            j_pos = j_frame['position']
            dist = math.sqrt((p_pos['x'] - j_pos['x'])**2 + (p_pos['y'] - j_pos['y'])**2)
            if dist <= proximity_range:
                nearby_frames += 1
                
    if total_frames == 0:
        return 0.0
    return round((float(nearby_frames) / float(total_frames)) * 100.0, 1)

def calculate_gank_susceptibility(timeline_data, participant_id, enemy_jungler_id):
    if not enemy_jungler_id:
        return 0
    frames = timeline_data['info']['frames']
    cutoff = 14 * 60 * 1000
    gank_deaths = 0
    for frame in frames:
        if frame['timestamp'] > cutoff:
            break
        for event in frame.get('events', []):
            if event['type'] == 'CHAMPION_KILL' and event.get('victimId') == participant_id:
                killer = event.get('killerId')
                assists = event.get('assistingParticipantIds', [])
                if killer == enemy_jungler_id or enemy_jungler_id in assists:
                    gank_deaths += 1
    return gank_deaths

def calculate_early_ward_count(timeline_data, participant_id):
    frames = timeline_data['info']['frames']
    cutoff = 14 * 60 * 1000
    wards = 0
    for frame in frames:
        if frame['timestamp'] > cutoff:
            break
        for event in frame.get('events', []):
            if event['type'] == 'WARD_PLACED' and event.get('creatorId') == participant_id:
                wards += 1
    return wards

def calculate_spotted_ganks(timeline_data, victim_id, enemy_jungler_id, enemy_jungler_path_df, team_participant_ids):
    if enemy_jungler_path_df.empty:
        return 0, 0

    spotted = 0
    unspotted = 0
    cutoff = 14 * 60 * 1000
    vision_range_sq = 1000 ** 2
    gank_window = 30 * 1000
    active_wards = []
    team_pids_set = set(team_participant_ids)

    # Pre-extract path arrays for fast slicing
    path_timestamps = enemy_jungler_path_df['timestamp'].values
    path_x = enemy_jungler_path_df['x'].values
    path_y = enemy_jungler_path_df['y'].values

    def is_visible(seg_x, seg_y, wards):
        if not wards:
            return False
        ward_coords = np.array([[w['x'], w['y']] for w in wards])
        for i in range(len(seg_x)):
            dx = seg_x[i] - ward_coords[:, 0]
            dy = seg_y[i] - ward_coords[:, 1]
            if np.any(dx * dx + dy * dy <= vision_range_sq):
                return True
        return False

    for frame in timeline_data['info']['frames']:
        ts = frame['timestamp']
        if ts > cutoff:
            break

        active_wards = [w for w in active_wards if w['expiry'] > ts]

        for event in frame.get('events', []):
            if event['type'] == 'WARD_PLACED' and event.get('creatorId') in team_pids_set:
                duration = 90000
                wtype = event.get('wardType')
                if wtype == 'CONTROL_WARD': duration = 1200000
                elif wtype == 'SITE_WARD': duration = 150000

                pos = event.get('position')
                if pos:
                    active_wards.append({'x': pos['x'], 'y': pos['y'], 'expiry': ts + duration})

            if event['type'] == 'CHAMPION_KILL' and event.get('victimId') == victim_id:
                killer = event.get('killerId')
                assists = event.get('assistingParticipantIds', [])
                if killer == enemy_jungler_id or enemy_jungler_id in assists:
                    window_start = ts - gank_window
                    mask = (path_timestamps >= window_start) & (path_timestamps <= ts)
                    seg_x = path_x[mask]
                    seg_y = path_y[mask]
                    if len(seg_x) > 0 and is_visible(seg_x, seg_y, active_wards):
                        spotted += 1
                    else:
                        unspotted += 1

    return spotted, unspotted
