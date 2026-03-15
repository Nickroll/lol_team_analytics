import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def generate_report_image(stats_df, adv_df, summary_lines, match_id,
                          momentum_data=None, conversion_data=None):
    """
    Generates a clean match report image as PNG.
    3-row layout: scoreboard, gold timeline chart, key callouts.
    Returns the file path.
    """
    export_dir = 'data/exports'
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, f"report_{match_id}.png")

    # Catppuccin Mocha palette
    bg_base = '#1e1e2e'
    bg_surface = '#313244'
    bg_mantle = '#181825'
    text_main = '#cdd6f4'
    text_sub = '#bac2de'
    cp_blue = '#89b4fa'
    cp_red = '#f38ba8'
    cp_green = '#a6e3a1'

    has_momentum = momentum_data is not None and 'gold_timeline' in momentum_data
    has_laning = adv_df is not None and not adv_df.empty and 'gold_diff_15' in adv_df.columns

    # Build title string: "Victory · Clean Win · 32 min"
    title_parts = []
    is_win = any("Victory" in line for line in summary_lines) if summary_lines else False
    title_parts.append("🏆 Victory" if is_win else "💀 Defeat")
    if has_momentum:
        title_parts.append(momentum_data['classification'])
    if summary_lines:
        for line in summary_lines:
            if "minutes" in line.lower():
                import re
                m = re.search(r'(\d+)\s*minutes', line)
                if m:
                    title_parts.append(f"{m.group(1)} min")
                break
    title_text = " · ".join(title_parts)

    # Layout: scoreboard → laning (if available) → gold timeline (if available) → callouts
    specs = [[{"type": "table"}]]
    row_heights = []

    if has_laning:
        specs.append([{"type": "table"}])
    if has_momentum:
        specs.append([{"type": "scatter"}])
    specs.append([{"type": "table"}])

    if has_laning and has_momentum:
        row_heights = [0.22, 0.18, 0.38, 0.22]
    elif has_laning:
        row_heights = [0.35, 0.30, 0.35]
    elif has_momentum:
        row_heights = [0.35, 0.40, 0.25]
    else:
        row_heights = [0.60, 0.40]

    fig = make_subplots(
        rows=len(specs), cols=1,
        specs=specs,
        vertical_spacing=0.05,
        row_heights=row_heights,
    )

    # Track which row each section goes in
    _row = [1]
    def next_row():
        r = _row[0]
        _row[0] += 1
        return r

    # ═══════════════════════════════════════════
    # Row: Compact Scoreboard
    # ═══════════════════════════════════════════
    scoreboard_row = next_row()
    if not stats_df.empty:
        display_cols = ['championName', 'summonerName', 'kills', 'deaths', 'assists', 'dpm', 'cspm', 'kp_%']
        available_cols = [c for c in display_cols if c in stats_df.columns]
        header_labels = {
            'championName': 'Champ', 'summonerName': 'Player',
            'kills': 'K', 'deaths': 'D', 'assists': 'A',
            'dpm': 'DPM', 'cspm': 'CS/M', 'kp_%': 'KP%',
        }
        headers = [header_labels.get(c, c) for c in available_cols]
        values = [stats_df[c].tolist() for c in available_cols]

        for i, c in enumerate(available_cols):
            if c in ('dpm', 'cspm', 'kp_%'):
                values[i] = [f"{v:.1f}" if isinstance(v, (int, float)) else v for v in values[i]]

        cell_font_colors = []
        for i, c in enumerate(available_cols):
            if c == 'deaths':
                cell_font_colors.append([cp_red if v >= 5 else text_main for v in stats_df[c]])
            else:
                cell_font_colors.append([text_main] * len(stats_df))

        fig.add_trace(
            go.Table(
                header=dict(
                    values=headers, fill_color=bg_base,
                    font=dict(color=text_main, size=12), align='center',
                    line_color=bg_mantle,
                ),
                cells=dict(
                    values=values, fill_color=bg_surface,
                    font=dict(color=cell_font_colors, size=11), align='center',
                    line_color=bg_mantle, height=26,
                ),
            ),
            row=scoreboard_row, col=1,
        )

    # ═══════════════════════════════════════════
    # Row: Laning Stats (if available)
    # ═══════════════════════════════════════════
    if has_laning:
        laning_row = next_row()
        lane_display = ['summonerName', 'gold_diff_15', 'cs_diff_15', 'xp_diff_15',
                        'solo_kills', 'gank_deaths', 'multi_deaths', 'dive_deaths']
        lane_avail = [c for c in lane_display if c in adv_df.columns]
        lane_headers_map = {
            'summonerName': 'Player',
            'gold_diff_15': 'Gold Δ@15', 'cs_diff_15': 'CS Δ@15', 'xp_diff_15': 'XP Δ@15',
            'solo_kills': 'Solo Deaths', 'gank_deaths': 'Gank Deaths',
            'multi_deaths': 'Multi Deaths', 'dive_deaths': 'Dive Deaths',
        }
        lane_headers = [lane_headers_map.get(c, c) for c in lane_avail]
        lane_values = []
        lane_font_colors = []
        diff_cols = {'gold_diff_15', 'cs_diff_15', 'xp_diff_15'}
        for c in lane_avail:
            col_vals = adv_df[c].tolist()
            if c in diff_cols:
                formatted = [f"{int(v):+,}" if isinstance(v, (int, float)) else v for v in col_vals]
                colors = [cp_green if v >= 0 else cp_red for v in col_vals]
            else:
                formatted = [str(int(v)) if isinstance(v, (int, float)) else v for v in col_vals]
                colors = [text_main] * len(col_vals)
            lane_values.append(formatted)
            lane_font_colors.append(colors)

        fig.add_trace(
            go.Table(
                header=dict(
                    values=lane_headers, fill_color=bg_base,
                    font=dict(color=text_main, size=11), align='center',
                    line_color=bg_mantle,
                ),
                cells=dict(
                    values=lane_values, fill_color=bg_mantle,
                    font=dict(color=lane_font_colors, size=11), align='center',
                    line_color=bg_mantle, height=24,
                ),
            ),
            row=laning_row, col=1,
        )

    # ═══════════════════════════════════════════
    # Row: Gold Timeline Chart (if momentum data available)
    # ═══════════════════════════════════════════
    if has_momentum:
        timeline_row = next_row()
        gold_tl = momentum_data['gold_timeline']
        minutes = [f['minute'] for f in gold_tl]
        diffs = [f['gold_diff'] for f in gold_tl]
        pos_diffs = [max(0, d) for d in diffs]
        neg_diffs = [min(0, d) for d in diffs]

        fig.add_trace(
            go.Scatter(
                x=minutes, y=pos_diffs, fill='tozeroy',
                fillcolor='rgba(137, 180, 250, 0.3)',
                line=dict(color=cp_blue, width=2),
                name='Our Lead', showlegend=False,
            ),
            row=timeline_row, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=minutes, y=neg_diffs, fill='tozeroy',
                fillcolor='rgba(243, 139, 168, 0.3)',
                line=dict(color=cp_red, width=2),
                name='Enemy Lead', showlegend=False,
            ),
            row=timeline_row, col=1,
        )

        fig.add_hline(y=3000, line_dash="dash", line_color="rgba(166, 227, 161, 0.4)",
                      row=timeline_row, col=1)
        fig.add_hline(y=-3000, line_dash="dash", line_color="rgba(243, 139, 168, 0.4)",
                      row=timeline_row, col=1)
        fig.add_hline(y=0, line_color="white", line_width=1, row=timeline_row, col=1)

        if momentum_data['peak_lead'] > 0:
            fig.add_annotation(
                x=momentum_data['peak_lead_minute'], y=momentum_data['peak_lead'],
                text=f"+{momentum_data['peak_lead']:,}g",
                showarrow=True, arrowcolor=cp_green,
                font=dict(color=cp_green, size=10),
                row=timeline_row, col=1,
            )
        if momentum_data['peak_deficit'] < 0:
            fig.add_annotation(
                x=momentum_data['peak_deficit_minute'], y=momentum_data['peak_deficit'],
                text=f"{momentum_data['peak_deficit']:,}g",
                showarrow=True, arrowcolor=cp_red,
                font=dict(color=cp_red, size=10),
                row=timeline_row, col=1,
            )

    # ═══════════════════════════════════════════
    # Row: Key Callouts
    # ═══════════════════════════════════════════
    callout_row = next_row()

    callout_headers = []
    callout_values = []

    # MVP
    if summary_lines:
        for line in summary_lines:
            if "MVP" in line:
                clean = line.replace('**', '').replace('⭐ ', '')
                callout_headers.append('⭐ MVP')
                callout_values.append(clean.replace('MVP: ', ''))
                break

    # Objectives
    if summary_lines:
        for line in summary_lines:
            if "Objectives" in line:
                clean = line.replace('**', '').replace('🏰 ', '')
                callout_headers.append('🏰 Objectives')
                callout_values.append(clean.replace('Objectives Secured: ', '').replace('Objectives: ', ''))
                break

    # Gold @ 15
    if summary_lines:
        for line in summary_lines:
            if "Gold @" in line or "Gold@" in line:
                clean = line.replace('**', '').replace('📈 ', '').replace('📉 ', '')
                callout_headers.append('💰 Gold@15')
                callout_values.append(clean.replace('Gold @ 15m: ', ''))
                break

    # Fight conversion
    if conversion_data is not None:
        callout_headers.append('⚔️ Fight Conversion')
        callout_values.append(
            f"Ours: {conversion_data['team_conversion_rate']}% · Theirs: {conversion_data['enemy_conversion_rate']}%"
        )

    if callout_headers:
        fig.add_trace(
            go.Table(
                header=dict(
                    values=callout_headers, fill_color=bg_base,
                    font=dict(color=text_main, size=11), align='center',
                    line_color=bg_mantle,
                ),
                cells=dict(
                    values=[[v] for v in callout_values], fill_color=bg_mantle,
                    font=dict(color=text_sub, size=11), align='center',
                    line_color=bg_mantle, height=28,
                ),
            ),
            row=callout_row, col=1,
        )
    else:
        fig.add_trace(
            go.Table(
                header=dict(values=['Summary'], fill_color=bg_base, font=dict(color=text_sub, size=11)),
                cells=dict(values=[['No summary data']], fill_color=bg_mantle, font=dict(color=text_sub, size=11)),
            ),
            row=callout_row, col=1,
        )

    # ═══════════════════════════════════════════
    # Layout
    # ═══════════════════════════════════════════
    if has_laning and has_momentum:
        height = 1000
    elif has_laning or has_momentum:
        height = 700
    else:
        height = 500
    fig.update_layout(
        title=dict(text=title_text, font=dict(color=text_main, size=16)),
        width=1200,
        height=height,
        paper_bgcolor=bg_base,
        plot_bgcolor=bg_base,
        font=dict(color=text_main),
        margin=dict(t=50, b=15, l=25, r=25),
    )

    # Style chart axes (for gold timeline)
    if has_momentum:
        fig.update_xaxes(
            title_text="Minutes", title_font=dict(color=text_sub, size=10),
            tickfont=dict(color=text_sub, size=9), gridcolor='#45475a',
            row=timeline_row, col=1,
        )
        fig.update_yaxes(
            title_text="Gold Diff", title_font=dict(color=text_sub, size=10),
            tickfont=dict(color=text_sub, size=9), gridcolor='#45475a',
            row=timeline_row, col=1,
        )

    try:
        fig.write_image(filepath, engine='kaleido')
        return filepath
    except Exception as e:
        print(f"Error generating report image: {e}")
        return None
