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

    participant_frames = []
    
    # 1. Determine Cutoff Timestamp
    # User requested fixed 15 minutes (15 * 60 * 1000 = 900000 ms)
    cutoff_timestamp = 900000

    # Helper for interpolation
    def get_position_at_timestamp(frames, target_ts, p_id):
        # Find frames before and after
        before_frame = None
        after_frame = None
        
        for f in frames:
            if f['timestamp'] <= target_ts:
                before_frame = f
            if f['timestamp'] >= target_ts:
                after_frame = f
                break
                
        if not before_frame:
            return None
            
        # If exact match or no after frame (end of game), return before
        if not after_frame or before_frame == after_frame:
             p_data = before_frame['participantFrames'].get(str(p_id))
             return p_data['position'] if p_data else None

        # Interpolate
        t1 = before_frame['timestamp']
        t2 = after_frame['timestamp']
        
        p1_data = before_frame['participantFrames'].get(str(p_id))
        p2_data = after_frame['participantFrames'].get(str(p_id))
        
        if not p1_data or not p2_data or 'position' not in p1_data or 'position' not in p2_data:
            return None
            
        p1 = p1_data['position']
        p2 = p2_data['position']
        
        ratio = (target_ts - t1) / (t2 - t1)
        
        x = p1['x'] + (p2['x'] - p1['x']) * ratio
        y = p1['y'] + (p2['y'] - p1['y']) * ratio
        
        return {'x': int(x), 'y': int(y)}

    path_points = []
    
    for frame in frames:
        timestamp = frame['timestamp']
        
        if timestamp > cutoff_timestamp:
            break
        
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
            
        # 2. Check for Events
        for event in frame['events']:
            if event['timestamp'] > cutoff_timestamp:
                continue
            
            ev_pos = None
            ev_type = None
            extra_info = None
            
            # ELITE MONSTER KILL
            if event['type'] == 'ELITE_MONSTER_KILL':
                if event.get('killerId') == participant_id:
                     ev_pos = event.get('position')
                     ev_type = 'ELITE_KILL'
                     extra_info = event.get('monsterType')

            # CHAMPION KILL / ASSIST
            elif event['type'] == 'CHAMPION_KILL':
                 if event.get('killerId') == participant_id or participant_id in event.get('assistingParticipantIds', []):
                     ev_pos = event.get('position')
                     ev_type = 'KILL_PARTICIPATION'
            
            # WARD PLACED
            elif event['type'] == 'WARD_PLACED':
                if event.get('creatorId') == participant_id:
                    ev_type = 'WARD_PLACED'
                    extra_info = event.get('wardType')
                    # Wards usually don't have position in modern API events, interpolate
                    ev_pos = get_position_at_timestamp(frames, event['timestamp'], participant_id)

            # SKILL LEVEL UP
            elif event['type'] == 'SKILL_LEVEL_UP':
                if event.get('participantId') == participant_id:
                    ev_type = 'SKILL_LEVEL_UP'
                    extra_info = f"Level Up: {event.get('skillSlot')}"
                    ev_pos = get_position_at_timestamp(frames, event['timestamp'], participant_id)

            # ITEM PURCHASED (Proxy for Backs/Buys)
            elif event['type'] == 'ITEM_PURCHASED':
                if event.get('participantId') == participant_id:
                     ev_type = 'ITEM_PURCHASED'
                     extra_info = f"Buy: {event.get('itemId')}"
                     ev_pos = get_position_at_timestamp(frames, event['timestamp'], participant_id)

            # Add Point if Event Found
            if ev_type:
                 if not ev_pos:
                     # Fallback to interpolation if event didn't provide position
                     ev_pos = get_position_at_timestamp(frames, event['timestamp'], participant_id)
                 
                 if ev_pos:
                     path_points.append({
                         'timestamp': event['timestamp'],
                         'x': ev_pos['x'],
                         'y': ev_pos['y'],
                         'type': ev_type,
                         'info': extra_info
                     })

    return pd.DataFrame(path_points)
