import pandas as pd


def generate_game_summary(match_data, timeline, puuids, adv_df=None):
    """
    Generates a list of natural-language bullet points summarizing a match.
    """
    info = match_data['info']
    participants = info['participants']
    duration_min = info['gameDuration'] / 60.0

    # Find our team's participants
    team_players = [p for p in participants if p['puuid'] in puuids.values()]
    if not team_players:
        return ["⚠️ Could not identify team players in this match."]

    summary = []

    # 1. Win/Loss + Duration
    won = team_players[0]['win']
    result_emoji = "🏆" if won else "💀"
    summary.append(f"{result_emoji} **{'Victory' if won else 'Defeat'}** in {duration_min:.0f} minutes.")

    # 2. Team KDA
    total_kills = sum(p['kills'] for p in team_players)
    total_deaths = sum(p['deaths'] for p in team_players)
    total_assists = sum(p['assists'] for p in team_players)
    summary.append(f"📊 Team KDA: **{total_kills}/{total_deaths}/{total_assists}**")

    # 3. MVP — highest KDA ratio
    best = max(team_players, key=lambda p: (p['kills'] + p['assists']) / max(1, p['deaths']))
    best_name = best.get('riotIdGameName', best.get('summonerName', '?'))
    best_champ = best['championName']
    best_kda = f"{best['kills']}/{best['deaths']}/{best['assists']}"
    summary.append(f"⭐ **MVP**: {best_name} ({best_champ}) — {best_kda}")

    # 4. Most Deaths
    worst = max(team_players, key=lambda p: p['deaths'])
    if worst['deaths'] >= 5:
        w_name = worst.get('riotIdGameName', worst.get('summonerName', '?'))
        w_champ = worst['championName']
        summary.append(f"💀 **Most Deaths**: {w_name} ({w_champ}) died **{worst['deaths']}** times.")

    # 5. First Blood
    if timeline and 'info' in timeline:
        for frame in timeline['info'].get('frames', []):
            for event in frame.get('events', []):
                if event['type'] == 'CHAMPION_KILL':
                    killer_id = event.get('killerId')
                    victim_id = event.get('victimId')
                    fb_killer = next((p for p in participants if p['participantId'] == killer_id), None)
                    fb_victim = next((p for p in participants if p['participantId'] == victim_id), None)
                    if fb_killer and fb_victim:
                        k_name = fb_killer.get('riotIdGameName', fb_killer.get('summonerName', '?'))
                        v_name = fb_victim.get('riotIdGameName', fb_victim.get('summonerName', '?'))
                        our_puuids = set(puuids.values())
                        if fb_killer['puuid'] in our_puuids:
                            summary.append(f"🩸 **First Blood** secured by {k_name} onto {v_name} at {event['timestamp']/60000:.1f}m.")
                        else:
                            summary.append(f"🩸 **First Blood** given up — {v_name} killed by {k_name} at {event['timestamp']/60000:.1f}m.")
                    break  # Only first kill
            else:
                continue
            break

    # 6. Gold Diff @ 15 (from timeline)
    if timeline and 'info' in timeline:
        frames = timeline['info'].get('frames', [])
        cutoff = 15 * 60 * 1000
        target_frame = None
        for f in frames:
            if f['timestamp'] >= cutoff:
                target_frame = f
                break
        if target_frame:
            our_gold = 0
            enemy_gold = 0
            our_puuids_set = set(puuids.values())
            pid_to_puuid = {}
            for p_info in timeline['info'].get('participants', []):
                pid_to_puuid[p_info['participantId']] = p_info['puuid']

            for pid_str, pf in target_frame.get('participantFrames', {}).items():
                pid = int(pid_str)
                puuid = pid_to_puuid.get(pid)
                gold = pf.get('totalGold', 0)
                if puuid in our_puuids_set:
                    our_gold += gold
                else:
                    enemy_gold += gold
            diff = our_gold - enemy_gold
            emoji = "📈" if diff > 0 else "📉"
            summary.append(f"{emoji} **Gold @ 15m**: {'+' if diff > 0 else ''}{diff:,}g")

    # 7. Dragon / Baron count
    our_team_id = team_players[0]['teamId']
    for team_obj in info.get('teams', []):
        if team_obj['teamId'] == our_team_id:
            objectives = team_obj.get('objectives', {})
            dragons = objectives.get('dragon', {}).get('kills', 0)
            barons = objectives.get('baron', {}).get('kills', 0)
            heralds = objectives.get('riftHerald', {}).get('kills', 0)
            obj_parts = []
            if dragons > 0:
                obj_parts.append(f"{dragons}🐉")
            if barons > 0:
                obj_parts.append(f"{barons}🟣 Baron")
            if heralds > 0:
                obj_parts.append(f"{heralds}🦀 Herald")
            if obj_parts:
                summary.append(f"🏰 **Objectives Secured**: {', '.join(obj_parts)}")
            else:
                summary.append("🏰 **Objectives**: None secured.")
            break

    # 8. Vision Assessment (from adv_df)
    if adv_df is not None and not adv_df.empty and 'early_wards' in adv_df.columns:
        avg_wards = adv_df['early_wards'].mean()
        if avg_wards < 3:
            summary.append(f"👁️ **Vision**: Poor — avg {avg_wards:.1f} wards placed pre-14m. Need more control!")
        elif avg_wards < 6:
            summary.append(f"👁️ **Vision**: Decent — avg {avg_wards:.1f} wards placed pre-14m.")
        else:
            summary.append(f"👁️ **Vision**: Strong — avg {avg_wards:.1f} wards placed pre-14m.")

    return summary
