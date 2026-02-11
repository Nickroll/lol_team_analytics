import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def generate_report_image(stats_df, adv_df, summary_lines, match_id):
    """
    Generates a composite match report image as PNG.
    Includes basic stats, advanced stats, charts, and text summary.
    Returns the file path.
    """
    export_dir = 'data/exports'
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, f"report_{match_id}.png")

    # Catppuccin palette
    colors = ['#89b4fa', '#cba6f7', '#a6e3a1', '#f9e2af', '#f38ba8']
    bg_base = '#1e1e2e'
    bg_surface = '#313244'
    bg_mantle = '#181825'
    text_main = '#cdd6f4'
    text_sub = '#bac2de'

    has_adv = adv_df is not None and not adv_df.empty

    fig = make_subplots(
        rows=5, cols=2,
        specs=[
            [{"colspan": 2, "type": "table"}, None],          # Row 1: Basic stats table
            [{"type": "bar"}, {"type": "bar"}],                # Row 2: DPM + KP charts
            [{"colspan": 2, "type": "table"}, None],          # Row 3: Advanced stats table
            [{"type": "bar"}, {"type": "bar"}],                # Row 4: Harass + Greed charts
            [{"colspan": 2, "type": "table"}, None],          # Row 5: Summary text
        ],
        subplot_titles=[
            "Team Stats",
            "Damage Per Minute", "Kill Participation %",
            "Advanced Stats",
            "Harass Score", "Greed Index",
            "Match Summary",
        ],
        vertical_spacing=0.04,
        row_heights=[0.20, 0.18, 0.20, 0.18, 0.24],
    )

    # ═══════════════════════════════════════════
    # Row 1: Basic Stats Table
    # ═══════════════════════════════════════════
    if not stats_df.empty:
        display_cols = ['summonerName', 'championName', 'role', 'kills', 'deaths', 'assists',
                        'cs', 'gold', 'damage', 'dpm', 'vspm', 'kp_%', 'dmg_%', 'gold_%']
        available_cols = [c for c in display_cols if c in stats_df.columns]
        header_labels = {
            'summonerName': 'Player', 'championName': 'Champ', 'role': 'Role',
            'kills': 'K', 'deaths': 'D', 'assists': 'A',
            'cs': 'CS', 'gold': 'Gold', 'damage': 'Dmg',
            'dpm': 'DPM', 'vspm': 'VS/M',
            'kp_%': 'KP%', 'dmg_%': 'Dmg%', 'gold_%': 'Gold%',
        }
        headers = [header_labels.get(c, c) for c in available_cols]
        values = [stats_df[c].tolist() for c in available_cols]

        # Format numeric columns
        for i, c in enumerate(available_cols):
            if c in ('dpm', 'vspm', 'kp_%', 'dmg_%', 'gold_%'):
                values[i] = [f"{v:.1f}" if isinstance(v, (int, float)) else v for v in values[i]]
            elif c in ('gold', 'damage'):
                values[i] = [f"{v:,.0f}" if isinstance(v, (int, float)) else v for v in values[i]]

        fig.add_trace(
            go.Table(
                header=dict(values=headers, fill_color=bg_base, font=dict(color=text_main, size=11), align='center'),
                cells=dict(values=values, fill_color=bg_surface, font=dict(color=text_main, size=10), align='center'),
            ),
            row=1, col=1,
        )

    # ═══════════════════════════════════════════
    # Row 2: DPM + KP Bar Charts
    # ═══════════════════════════════════════════
    if not stats_df.empty and 'dpm' in stats_df.columns:
        fig.add_trace(
            go.Bar(x=stats_df['summonerName'], y=stats_df['dpm'],
                   marker_color=colors[:len(stats_df)], showlegend=False),
            row=2, col=1,
        )

    if not stats_df.empty and 'kp_%' in stats_df.columns:
        fig.add_trace(
            go.Bar(x=stats_df['summonerName'], y=stats_df['kp_%'],
                   marker_color=colors[:len(stats_df)], showlegend=False),
            row=2, col=2,
        )

    # ═══════════════════════════════════════════
    # Row 3: Advanced Stats Table
    # ═══════════════════════════════════════════
    if has_adv:
        adv_cols = ['summonerName', 'harass_score', 'greed_index', 'jungle_prox',
                    'gank_deaths', 'early_wards', 'spotted_deaths', 'unspotted_deaths']
        avail_adv = [c for c in adv_cols if c in adv_df.columns]
        adv_headers_map = {
            'summonerName': 'Player', 'harass_score': 'Harass', 'greed_index': 'Greed',
            'jungle_prox': 'JG Prox%', 'gank_deaths': 'Gank Deaths',
            'early_wards': 'Wards<14m', 'spotted_deaths': 'Spotted', 'unspotted_deaths': 'Unspotted',
        }
        adv_headers = [adv_headers_map.get(c, c) for c in avail_adv]
        adv_values = [adv_df[c].tolist() for c in avail_adv]

        # Format
        for i, c in enumerate(avail_adv):
            if c in ('harass_score', 'jungle_prox'):
                adv_values[i] = [f"{v:.1f}" if isinstance(v, (int, float)) else v for v in adv_values[i]]

        fig.add_trace(
            go.Table(
                header=dict(values=adv_headers, fill_color=bg_base, font=dict(color=text_main, size=11), align='center'),
                cells=dict(values=adv_values, fill_color=bg_surface, font=dict(color=text_main, size=10), align='center'),
            ),
            row=3, col=1,
        )
    else:
        fig.add_trace(
            go.Table(
                header=dict(values=['Advanced Stats'], fill_color=bg_base, font=dict(color=text_sub, size=11)),
                cells=dict(values=[['No advanced data available']], fill_color=bg_surface, font=dict(color=text_sub, size=10)),
            ),
            row=3, col=1,
        )

    # ═══════════════════════════════════════════
    # Row 4: Harass Score + Greed Index Charts
    # ═══════════════════════════════════════════
    if has_adv and 'harass_score' in adv_df.columns:
        harass_colors = ['#a6e3a1' if v >= 1.0 else '#f38ba8' for v in adv_df['harass_score']]
        fig.add_trace(
            go.Bar(x=adv_df['summonerName'], y=adv_df['harass_score'],
                   marker_color=harass_colors, showlegend=False),
            row=4, col=1,
        )

    if has_adv and 'greed_index' in adv_df.columns:
        greed_colors = ['#f38ba8' if v >= 2 else '#f9e2af' if v >= 1 else '#a6e3a1' for v in adv_df['greed_index']]
        fig.add_trace(
            go.Bar(x=adv_df['summonerName'], y=adv_df['greed_index'],
                   marker_color=greed_colors, showlegend=False),
            row=4, col=2,
        )

    # ═══════════════════════════════════════════
    # Row 5: Match Summary Text
    # ═══════════════════════════════════════════
    if summary_lines:
        clean_lines = [line.replace('**', '') for line in summary_lines]
        fig.add_trace(
            go.Table(
                header=dict(values=['Match Summary'], fill_color=bg_base, font=dict(color=text_main, size=13), align='left'),
                cells=dict(values=[clean_lines], fill_color=bg_mantle, font=dict(color=text_sub, size=11), align='left', height=22),
            ),
            row=5, col=1,
        )
    else:
        fig.add_trace(
            go.Table(
                header=dict(values=['Match Summary'], fill_color=bg_base, font=dict(color=text_sub, size=13)),
                cells=dict(values=[['No summary available']], fill_color=bg_mantle, font=dict(color=text_sub, size=11)),
            ),
            row=5, col=1,
        )

    fig.update_layout(
        title=dict(text=f"Match Report — {match_id}", font=dict(color=text_main, size=18)),
        width=1400,
        height=1400,
        paper_bgcolor=bg_base,
        plot_bgcolor=bg_base,
        font=dict(color=text_main),
        margin=dict(t=60, b=20, l=30, r=30),
    )

    # Style chart axes
    for i in range(1, 9):
        axis_x = f'xaxis{i}' if i > 1 else 'xaxis'
        axis_y = f'yaxis{i}' if i > 1 else 'yaxis'
        if axis_x in fig.layout:
            fig.layout[axis_x].update(tickfont=dict(color=text_sub, size=9))
        if axis_y in fig.layout:
            fig.layout[axis_y].update(tickfont=dict(color=text_sub, size=9), gridcolor='#45475a')

    try:
        fig.write_image(filepath, engine='kaleido')
        return filepath
    except Exception as e:
        print(f"Error generating report image: {e}")
        return None
