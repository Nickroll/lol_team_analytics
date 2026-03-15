import pandas as pd
from src.analysis.advanced_stats import (
    calculate_harass_score, calculate_greed_index, calculate_jungle_proximity,
    calculate_gank_susceptibility, calculate_early_ward_count, calculate_spotted_ganks,
    calculate_laning_diffs, classify_early_deaths,
)
from src.analysis.jungle_pathing import extract_jungle_path


def build_puuid_to_pid(timeline):
    """Builds a {puuid: participantId} lookup from timeline participants."""
    return {p['puuid']: p['participantId'] for p in timeline['info']['participants']}


def identify_jungler(stats_df, puuids_dict, match_participants):
    """Returns the PUUID of our team's jungler, or None."""
    jungler_row = stats_df[stats_df['role'] == 'JUNGLE']
    if jungler_row.empty:
        return None

    j_name = jungler_row.iloc[0]['summonerName']
    for name, pid in puuids_dict.items():
        if name.split('#')[0].lower() == j_name.split('#')[0].lower():
            return pid

    target_p = next(
        (p for p in match_participants if p['championName'] == jungler_row.iloc[0]['championName']),
        None
    )
    return target_p['puuid'] if target_p else None


def find_lane_opponent_id(puuid, participants):
    """Returns participantId of the same-role player on the opposing team, or None."""
    our_p = next((p for p in participants if p['puuid'] == puuid), None)
    if not our_p:
        return None
    role    = our_p.get('teamPosition', '')
    team_id = our_p.get('teamId', 0)
    if not role:
        return None
    opp = next(
        (p for p in participants if p.get('teamPosition') == role and p['teamId'] != team_id),
        None
    )
    return opp['participantId'] if opp else None


def identify_enemy_jungler(match_participants, team_puuid_set):
    """Returns (participantId, puuid) of the enemy jungler, or (None, None)."""
    for p in match_participants:
        if p['teamPosition'] == 'JUNGLE' and p['puuid'] not in team_puuid_set:
            return p['participantId'], p['puuid']
    return None, None


def compute_advanced_stats(match, timeline, puuids_dict, stats_df):
    """
    Computes advanced stats for all players in a match.
    Returns a DataFrame with columns: summonerName, harass_score, greed_index,
    jungle_prox, gank_deaths, early_wards, spotted_deaths, unspotted_deaths,
    gold_diff_15, cs_diff_15, xp_diff_15, solo_kills, multi_deaths, dive_deaths.
    """
    puuid_set = set(puuids_dict.values())
    puuid_to_pid = build_puuid_to_pid(timeline)
    participants = match['info']['participants']

    jun_puuid = identify_jungler(stats_df, puuids_dict, participants)
    jun_pid = puuid_to_pid.get(jun_puuid) if jun_puuid else None

    enemy_jun_id, enemy_jun_puuid = identify_enemy_jungler(participants, puuid_set)

    enemy_j_path = pd.DataFrame()
    if enemy_jun_puuid:
        enemy_j_path = extract_jungle_path(timeline, enemy_jun_puuid)

    found_team_pids = [puuid_to_pid[pid] for pid in puuids_dict.values() if pid in puuid_to_pid]

    adv_stats = []
    for name, puuid in puuids_dict.items():
        p_id = puuid_to_pid.get(puuid)
        if not p_id:
            continue

        h_score = calculate_harass_score(timeline, p_id)
        p_team = next((p['teamId'] for p in participants if p['puuid'] == puuid), 100)
        g_index = calculate_greed_index(timeline, p_id, p_team)

        j_prox = 0.0
        if jun_pid and puuid != jun_puuid:
            j_prox = calculate_jungle_proximity(timeline, p_id, jun_pid)

        gank_deaths = calculate_gank_susceptibility(timeline, p_id, enemy_jun_id)
        early_wards = calculate_early_ward_count(timeline, p_id)
        spotted, unspotted = calculate_spotted_ganks(timeline, p_id, enemy_jun_id, enemy_j_path, found_team_pids)

        # Laning diffs vs lane opponent
        opp_pid = find_lane_opponent_id(puuid, participants)
        laning = {'gold_diff_15': 0, 'cs_diff_15': 0, 'xp_diff_15': 0}
        if opp_pid:
            laning = calculate_laning_diffs(timeline, p_id, opp_pid)

        # Death classification
        is_blue = (p_team == 100)
        death_classes = classify_early_deaths(timeline, p_id, enemy_jun_id, is_blue)

        adv_stats.append({
            'summonerName': name,
            'harass_score': h_score,
            'greed_index': g_index,
            'jungle_prox': j_prox,
            'gank_deaths': gank_deaths,
            'early_wards': early_wards,
            'spotted_deaths': spotted,
            'unspotted_deaths': unspotted,
            'gold_diff_15': laning['gold_diff_15'],
            'cs_diff_15':   laning['cs_diff_15'],
            'xp_diff_15':   laning['xp_diff_15'],
            'solo_kills':   death_classes['solo_kill'],
            'multi_deaths': death_classes['multi_death'],
            'dive_deaths':  death_classes['dive_death'],
        })

    return pd.DataFrame(adv_stats), found_team_pids
