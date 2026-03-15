
import pandas as pd
import numpy as np
from src.analysis.basic_stats import get_team_stats
from src.analysis.common import compute_advanced_stats


def calculate_gold_diff_at_15(match_timeline, team_id):
    """
    Calculates the gold difference for the specified team at 15 minutes.
    """
    try:
        frames = match_timeline['info']['frames']
        
        # Target frame is 15 minutes (or last frame if game ended early)
        target_frame_idx = 15
        if len(frames) <= target_frame_idx:
            target_frame_idx = len(frames) - 1
            
        frame = frames[target_frame_idx]
        
        team_gold = 0
        enemy_gold = 0
        
        for pid in range(1, 11):
            participant_frame = frame['participantFrames'].get(str(pid))
            if participant_frame:
                gold = participant_frame['totalGold']
                pid_team = 100 if pid <= 5 else 200
                
                if pid_team == team_id:
                    team_gold += gold
                else:
                    enemy_gold += gold
                    
        return team_gold - enemy_gold
        
    except Exception as e:
        print(f"Error calculating gold diff: {e}")
        return 0

def analyze_team_trends(matches, team_puuids_list, fetcher):
    """
    Analyzes trends across a list of matches for the tracked team.
    """
    trend_data = []
    
    for match in matches:
        try:
            match_id = match['metadata']['matchId']
            first_puuid = team_puuids_list[0]
            participant = next((p for p in match['info']['participants'] if p['puuid'] == first_puuid), None)
            
            if not participant:
                continue
                
            team_id = participant['teamId']
            win = participant['win']
            side = 'Blue' if team_id == 100 else 'Red'
            
            timeline = fetcher.get_match_timeline(match_id)
            gold_diff_15 = 0
            if timeline:
                gold_diff_15 = calculate_gold_diff_at_15(timeline, team_id)
            
            trend_data.append({
                'match_id': match_id,
                'win': win,
                'side': side,
                'gold_diff_15': gold_diff_15,
                'game_creation': match['info']['gameCreation']
            })
            
        except Exception as e:
            print(f"Error processing match {match_id}: {e}")
            
    return pd.DataFrame(trend_data)


def analyze_player_trends(matches, puuids_dict, fetcher):
    """
    Collects per-player basic + advanced stats across all matches for trend analysis.
    
    Args:
        matches: List of match DTOs
        puuids_dict: Dict of {name#tag: puuid}
        fetcher: MatchFetcher instance
        
    Returns:
        DataFrame with one row per player per match, containing:
        - Basic: KDA, DPM, CSPM, VSPM, KP%, Dmg%, Gold%
        - Advanced: harass_score, greed_index, jungle_prox, gank_deaths,
                    early_wards, spotted_deaths, unspotted_deaths
    """
    all_rows = []
    puuid_list = list(puuids_dict.values())
    
    for match in matches:
        try:
            match_id = match['metadata']['matchId']
            game_creation = match['info']['gameCreation']
            
            # Get basic stats
            stats_df = get_team_stats(match, puuid_list)
            if stats_df.empty:
                continue

            # Fetch timeline for advanced stats
            timeline = fetcher.get_match_timeline(match_id)

            # Build advanced stats if timeline available
            adv_map = {}
            if timeline:
                adv_df, _ = compute_advanced_stats(match, timeline, puuids_dict, stats_df)
                if not adv_df.empty:
                    for _, row in adv_df.iterrows():
                        adv_map[row['summonerName']] = {
                            'harass_score': row['harass_score'],
                            'greed_index': row['greed_index'],
                            'jungle_prox': row['jungle_prox'],
                            'gank_deaths': row['gank_deaths'],
                            'early_wards': row['early_wards'],
                            'spotted_deaths': row['spotted_deaths'],
                            'unspotted_deaths': row['unspotted_deaths'],
                        }

            # Combine basic + advanced into rows
            for _, row in stats_df.iterrows():
                player_name = row['summonerName']
                entry = {
                    'match_id': match_id,
                    'game_creation': game_creation,
                    'player': player_name,
                    'champion': row.get('championName', ''),
                    'role': row.get('role', ''),
                    'win': row.get('win', False),
                    # Basic stats
                    'kda_ratio': row.get('kda_ratio', 0),
                    'kills': row.get('kills', 0),
                    'deaths': row.get('deaths', 0),
                    'assists': row.get('assists', 0),
                    'dpm': row.get('dpm', 0),
                    'cspm': row.get('cspm', 0),
                    'vspm': row.get('vspm', 0),
                    'kp_%': row.get('kp_%', 0),
                    'dmg_%': row.get('dmg_%', 0),
                    'gold_%': row.get('gold_%', 0),
                    'dpg': row.get('dpg', 0),
                }

                # Merge advanced stats by matching name
                adv = None
                for adv_name, adv_data in adv_map.items():
                    if adv_name.split('#')[0].lower() == player_name.split('#')[0].lower():
                        adv = adv_data
                        break
                
                if adv:
                    entry.update(adv)
                else:
                    entry.update({
                        'harass_score': 0, 'greed_index': 0, 'jungle_prox': 0,
                        'gank_deaths': 0, 'early_wards': 0, 'spotted_deaths': 0, 'unspotted_deaths': 0,
                    })

                all_rows.append(entry)

        except Exception as e:
            print(f"Error in player trend for match: {e}")

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = df.sort_values('game_creation').reset_index(drop=True)
        # Add a game number per player for x-axis
        df['game_num'] = df.groupby('player').cumcount() + 1
    return df
