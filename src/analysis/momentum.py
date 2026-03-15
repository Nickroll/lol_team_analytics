def compute_gold_timeline(timeline, team_participant_ids):
    """
    Computes per-frame gold difference between our team and the enemy.
    Returns list of {minute, gold_diff, team_gold, enemy_gold}.
    """
    team_pids = set(team_participant_ids)
    gold_timeline = []

    for frame in timeline['info']['frames']:
        minute = frame['timestamp'] / 60000
        team_gold = 0
        enemy_gold = 0

        for pid_str, pf in frame.get('participantFrames', {}).items():
            pid = int(pid_str)
            total_gold = pf.get('totalGold', 0)
            if pid in team_pids:
                team_gold += total_gold
            else:
                enemy_gold += total_gold

        gold_timeline.append({
            'minute': round(minute, 1),
            'gold_diff': team_gold - enemy_gold,
            'team_gold': team_gold,
            'enemy_gold': enemy_gold,
        })

    return gold_timeline


def classify_game(gold_timeline, won):
    """
    Classifies a game based on gold swings and outcome.
    Threshold: 3000g.

    Returns dict with classification, peak_lead, peak_lead_minute,
    peak_deficit, peak_deficit_minute.
    """
    threshold = 3000

    peak_lead = 0
    peak_lead_minute = 0
    peak_deficit = 0
    peak_deficit_minute = 0

    for frame in gold_timeline:
        diff = frame['gold_diff']
        if diff > peak_lead:
            peak_lead = diff
            peak_lead_minute = frame['minute']
        if diff < peak_deficit:
            peak_deficit = diff
            peak_deficit_minute = frame['minute']

    was_up_3k = peak_lead >= threshold
    was_down_3k = peak_deficit <= -threshold

    if not was_up_3k and not was_down_3k:
        classification = "Close Game"
    elif won and was_down_3k:
        classification = "Comeback Win"
    elif won:
        classification = "Clean Win"
    elif not won and was_up_3k:
        classification = "Throw Loss"
    else:
        classification = "Clean Loss"

    return {
        'classification': classification,
        'peak_lead': peak_lead,
        'peak_lead_minute': peak_lead_minute,
        'peak_deficit': peak_deficit,
        'peak_deficit_minute': peak_deficit_minute,
    }


def analyze_game_momentum(timeline, match_data, team_participant_ids):
    """
    Top-level wrapper: computes gold timeline and classifies the game.
    Returns dict with gold_timeline list and classification info.
    """
    # Determine if team won
    team_pids = set(team_participant_ids)
    won = False
    for p in match_data['info']['participants']:
        if p['participantId'] in team_pids:
            won = p['win']
            break

    gold_timeline = compute_gold_timeline(timeline, team_participant_ids)
    classification = classify_game(gold_timeline, won)

    return {
        'gold_timeline': gold_timeline,
        **classification,
    }
