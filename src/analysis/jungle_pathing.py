import pandas as pd
import numpy as np

def extract_jungle_path(timeline_data, puuid):
    """
    Extracts the movement path and jungle/objective kills for a specific player (by PUUID).
    """
    frames = timeline_data['info']['frames']
    
    # Find participant ID for the given PUUID
    participant_id = None
    for p in timeline_data['info']['participants']:
        if p['puuid'] == puuid:
            participant_id = p['participantId']
            break
            
    if not participant_id:
        return pd.DataFrame()

    path_points = []
    
    for frame in frames:
        timestamp = frame['timestamp']
        
        # 1. Get Position from Participant Frames
        p_frame = frame['participantFrames'].get(str(participant_id))
        if p_frame and 'position' in p_frame:
            pos = p_frame['position']
            path_points.append({
                'timestamp': timestamp,
                'x': pos['x'],
                'y': pos['y'],
                'type': 'POSITION'
            })
            
        # 2. Check for Events (kills)
        for event in frame['events']:
            if event['type'] == 'ELITE_MONSTER_KILL':
                # Check if this player killed it or assisted
                # 'killerId' is the one who got the kill.
                if event.get('killerId') == participant_id:
                     # Events usually have position, if not, use last known position
                     ev_pos = event.get('position')
                     if ev_pos:
                         path_points.append({
                             'timestamp': event['timestamp'],
                             'x': ev_pos['x'],
                             'y': ev_pos['y'],
                             'type': 'ELITE_KILL',
                             'monster': event.get('monsterType')
                         })

            # Check for generic kills (ganks)
            if event['type'] == 'CHAMPION_KILL':
                 if event.get('killerId') == participant_id or participant_id in event.get('assistingParticipantIds', []):
                     ev_pos = event.get('position')
                     if ev_pos:
                         path_points.append({
                             'timestamp': event['timestamp'],
                             'x': ev_pos['x'],
                             'y': ev_pos['y'],
                             'type': 'KILL_PARTICIPATION'
                         })

    return pd.DataFrame(path_points)
