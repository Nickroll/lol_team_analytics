import requests
import json
import os
from datetime import datetime


def build_match_embed(summary_lines, stats_df, match_id, adv_df=None):
    """
    Builds a Discord embed object from match data.
    """
    # Determine win/loss from summary
    is_win = any("Victory" in line for line in summary_lines) if summary_lines else False
    color = 0xa6e3a1 if is_win else 0xf38ba8  # Green for win, red for loss

    description = "\n".join(summary_lines) if summary_lines else "No summary available."

    embed = {
        "title": f"{'🏆' if is_win else '💀'} Match Report — {match_id}",
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "LoL Team Analytics"},
    }

    # Add basic stats as fields
    fields = []
    if stats_df is not None and not stats_df.empty:
        # Player scorelines
        scorelines = []
        for _, row in stats_df.iterrows():
            name = str(row.get('summonerName', '?'))
            champ = str(row.get('championName', '?'))
            k = int(row.get('kills', 0))
            d = int(row.get('deaths', 0))
            a = int(row.get('assists', 0))
            dpm = row.get('dpm', 0)
            scorelines.append(f"**{name}** ({champ}): {k}/{d}/{a} — {dpm:.0f} DPM")

        fields.append({
            "name": "📊 Player Stats",
            "value": "\n".join(scorelines),
            "inline": False,
        })

    # Add advanced stats if available
    if adv_df is not None and not adv_df.empty:
        adv_lines = []
        for _, row in adv_df.iterrows():
            name = str(row.get('summonerName', '?'))
            harass = row.get('harass_score', 0)
            greed = int(row.get('greed_index', 0))
            wards = int(row.get('early_wards', 0))
            ganks = int(row.get('gank_deaths', 0))
            adv_lines.append(f"**{name}**: Harass {harass:.1f} | Greed {greed} | Wards {wards} | Gank Deaths {ganks}")

        fields.append({
            "name": "🛡️ Advanced Stats",
            "value": "\n".join(adv_lines),
            "inline": False,
        })

        # Laning phase stats (only if the new columns are present)
        if 'gold_diff_15' in adv_df.columns:
            lane_lines = []
            for _, row in adv_df.iterrows():
                name = str(row.get('summonerName', '?'))
                gold_d  = int(row.get('gold_diff_15', 0))
                cs_d    = int(row.get('cs_diff_15', 0))
                xp_d    = int(row.get('xp_diff_15', 0))
                solo    = int(row.get('solo_kills', 0))
                ganks2  = int(row.get('gank_deaths', 0))
                multi   = int(row.get('multi_deaths', 0))
                gold_str = f"{gold_d:+,}"
                cs_str   = f"{cs_d:+}"
                xp_str   = f"{xp_d:+,}"
                lane_lines.append(
                    f"**{name}**: Gold {gold_str} | CS {cs_str} | XP {xp_str} | "
                    f"Solo {solo} / Gank {ganks2} / Multi {multi} deaths"
                )

            fields.append({
                "name": "⚔️ Laning Phase (@15m)",
                "value": "\n".join(lane_lines),
                "inline": False,
            })

    embed["fields"] = fields
    return embed


def send_to_discord(webhook_url, summary_lines, stats_df, match_id, adv_df=None, report_image_path=None):
    """
    Sends a match report to Discord via webhook.
    
    Args:
        webhook_url: Discord webhook URL
        summary_lines: List of summary bullet strings
        stats_df: DataFrame of basic player stats
        match_id: The match ID string
        adv_df: Optional DataFrame of advanced stats
        report_image_path: Optional path to report PNG
        
    Returns:
        (success: bool, message: str)
    """
    if not webhook_url:
        return False, "No webhook URL configured."

    embed = build_match_embed(summary_lines, stats_df, match_id, adv_df)
    payload = {"embeds": [embed]}

    try:
        # If we have a report image, send as multipart with file attachment
        if report_image_path and os.path.exists(report_image_path):
            # Reference the attachment in the embed
            embed["image"] = {"url": "attachment://report.png"}
            payload = {"embeds": [embed]}

            with open(report_image_path, 'rb') as f:
                files = {
                    "file": ("report.png", f, "image/png"),
                }
                form_data = {
                    "payload_json": (None, json.dumps(payload), "application/json"),
                }
                response = requests.post(webhook_url, files={**form_data, **files}, timeout=15)
        else:
            headers = {"Content-Type": "application/json"}
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=15)

        if response.status_code in (200, 204):
            return True, "Successfully sent to Discord!"
        else:
            return False, f"Discord returned status {response.status_code}: {response.text[:200]}"

    except requests.exceptions.Timeout:
        return False, "Request timed out. Check your webhook URL."
    except requests.exceptions.ConnectionError:
        return False, "Connection error. Check your webhook URL and network."
    except Exception as e:
        return False, f"Error: {str(e)}"
