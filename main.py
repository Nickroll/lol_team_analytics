import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.api.riot_client import RiotClient, ApiError
from src.api.match_fetcher import MatchFetcher
from src.api.match_cache import MatchCache
from src.analysis.basic_stats import get_team_stats
from src.analysis.common import compute_advanced_stats
from src.analysis.jungle_pathing import extract_jungle_path
from src.analysis.team_trends import analyze_team_trends, analyze_player_trends
from src.analysis.objectives import analyze_objective_setup, detect_objective_throw
from src.analysis.game_summary import generate_game_summary
from src.analysis.teamfights import detect_teamfights, analyze_teamfight
from src.analysis.report_export import generate_report_image
from src.discord_integration import send_to_discord
from src.config import ConfigManager
import os

# Catppuccin Mocha palette
CP_BLUE = "#89b4fa"
CP_RED = "#f38ba8"
CP_GREEN = "#a6e3a1"
CP_YELLOW = "#f9e2af"
CP_MAUVE = "#cba6f7"
CP_COLORS = [CP_BLUE, CP_MAUVE, CP_GREEN, CP_YELLOW, CP_RED]

# Page Config
st.set_page_config(page_title="LoL Team Analytics", layout="wide")

st.title("League of Legends Team Analytics")

# Load Config
config_manager = ConfigManager()
config = config_manager.load_config()

# Analysis Mode Selection
# We place this at the top of the sidebar for visibility
analysis_mode = st.sidebar.radio("Analysis Mode", ["Single Match", "Team Trends (Beta)"], index=0)
st.sidebar.markdown("---")

# Cache Stats
st.sidebar.subheader("💾 Cache")
_cache = MatchCache()
_stats = _cache.get_stats()
st.sidebar.caption(f"Matches: {_stats['matches_cached']} · Timelines: {_stats['timelines_cached']} · Size: {_stats['db_size_mb']} MB")
if st.sidebar.button("🗑️ Clear Cache"):
    _cache.clear()
    st.sidebar.success("Cache cleared!")
    st.rerun()
st.sidebar.markdown("---")

# Sidebar for specific player inputs
st.sidebar.header("Team Configuration")
regions = ['na1', 'euw1', 'kr', 'br1']
default_region = config.get('region', 'na1')
region_index = regions.index(default_region) if default_region in regions else 0
region = st.sidebar.selectbox("Region", regions, index=region_index) 

default_api_key = config.get('api_key', '')
api_key = st.sidebar.text_input("Riot API Key", value=default_api_key, type="password", help="Get one from developer.riotgames.com")

default_webhook = config.get('discord_webhook', '')
discord_webhook = st.sidebar.text_input("Discord Webhook URL", value=default_webhook, type="password", help="Paste a Discord channel webhook URL to enable sharing")

st.sidebar.subheader("Summoner Names (Name#Tag)")
player_inputs = []
default_players = config.get('players', [''] * 5)
for i in range(5):
    default_val = default_players[i] if i < len(default_players) else ''
    player_inputs.append(st.sidebar.text_input(f"Player {i+1}", value=default_val, key=f"p{i}"))

if st.sidebar.button("Save Configuration"):
    config_data = {
        'api_key': api_key,
        'region': region,
        'players': player_inputs,
        'discord_webhook': discord_webhook,
    }
    if config_manager.save_config(config_data):
        st.sidebar.success("Configuration saved!")
    else:
        st.sidebar.error("Failed to save configuration.")

# Initialize session state for persistent results
if 'team_matches' not in st.session_state:
    st.session_state.team_matches = None
if 'puuids' not in st.session_state:
    st.session_state.puuids = None

if st.sidebar.button("Analyze Games"):
    if not api_key:
        st.error("Please provide a Riot API Key.")
    elif not all(player_inputs):
        st.error("Please enter all 5 summoner names.")
    else:
        try:
            # Initialize Client
            client = RiotClient(api_key=api_key, region=region)
            fetcher = MatchFetcher(client)
            
            with st.spinner("Resolving Summoners..."):
                puuids = fetcher.get_puuids_from_names(player_inputs)
                st.session_state.puuids = puuids
                
            if len(puuids) < 5:
                st.warning(f"Could only resolve {len(puuids)}/5 summoners. Check names and try again.")
                st.write(puuids)
                st.session_state.team_matches = None
            else:
                st.success("All summoners resolved!")
                
                with st.spinner("Finding Team Games (this may take a moment)..."):
                    # Fetch matches (limit to last 20 for speed)
                    team_matches = fetcher.find_games_with_team(puuids, count=20)
                    st.session_state.team_matches = team_matches
                
                if not team_matches:
                    st.info("No recent games found with all 5 players together.")

        except Exception as e:
            st.error(f"An error occurred: {e}")

# Render Results from Session State (Persists across reruns from other widgets)
if st.session_state.team_matches and st.session_state.puuids:
    team_matches = st.session_state.team_matches
    puuids = st.session_state.puuids
    
    # Initialize Fetcher
    client = RiotClient(api_key=api_key, region=region)
    fetcher = MatchFetcher(client)

    if analysis_mode == "Team Trends (Beta)":
        st.header("📈 Team Trends (Last 20 Games)")
        
        with st.spinner("Analyzing Team Trends..."):
            trend_df = analyze_team_trends(team_matches, list(puuids.values()), fetcher)
        
        if not trend_df.empty:
            # 1. Gold Diff @ 15
            st.subheader("Early Game Performance (Gold Diff @ 15m)")
            fig_gd = px.line(trend_df, x='game_creation', y='gold_diff_15', markers=True,
                             title="Gold Difference at 15 Minutes",
                             labels={'gold_diff_15': 'Gold Difference', 'game_creation': 'Date'},
                             template='plotly_dark')
            fig_gd.add_hline(y=0, line_dash="dash", line_color="white")
            st.plotly_chart(fig_gd, use_container_width=True)
            
            # 2. Side Selection Win Rate
            st.subheader("Win Rate by Side")
            side_wr = trend_df.groupby('side')['win'].mean().reset_index()
            side_wr['win'] = side_wr['win'] * 100
            fig_side = px.bar(side_wr, x='side', y='win', title="Win Rate % by Side", 
                              color='side', color_discrete_map={'Blue': '#89b4fa', 'Red': '#f38ba8'},
                              template='plotly_dark')
            st.plotly_chart(fig_side, use_container_width=True)
            
        else:
            st.warning("Could not calculate team trends.")

        # ═══════════════════════════════════════════
        # Per-Player Trends
        # ═══════════════════════════════════════════
        st.markdown("---")
        st.header("👤 Player Trends Over Time")

        with st.spinner("Calculating player stats across all games..."):
            player_trend_df = analyze_player_trends(team_matches, puuids, fetcher)

        if not player_trend_df.empty:
            all_players = sorted(player_trend_df['player'].unique().tolist())
            selected_players = st.multiselect(
                "Select Players", all_players, default=all_players, key="trend_player_select"
            )
            filtered_df = player_trend_df[player_trend_df['player'].isin(selected_players)]

            if not filtered_df.empty:
                tab_basic, tab_laning, tab_advanced = st.tabs([
                    "📊 Basic Performance", "⚔️ Laning & Efficiency", "🛡️ Advanced & Vision"
                ])

                # --- Basic Performance ---
                with tab_basic:
                    col1, col2 = st.columns(2)
                    with col1:
                        fig = px.line(filtered_df, x='game_num', y='kda_ratio', color='player', markers=True,
                                      title="KDA Ratio", labels={'game_num': 'Game #', 'kda_ratio': 'KDA'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_kda")

                        fig = px.line(filtered_df, x='game_num', y='dpm', color='player', markers=True,
                                      title="Damage Per Minute", labels={'game_num': 'Game #', 'dpm': 'DPM'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_dpm")

                        fig = px.line(filtered_df, x='game_num', y='deaths', color='player', markers=True,
                                      title="Deaths", labels={'game_num': 'Game #', 'deaths': 'Deaths'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_deaths")

                    with col2:
                        fig = px.line(filtered_df, x='game_num', y='kp_%', color='player', markers=True,
                                      title="Kill Participation %", labels={'game_num': 'Game #', 'kp_%': 'KP%'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_kp")

                        fig = px.line(filtered_df, x='game_num', y='dmg_%', color='player', markers=True,
                                      title="Damage Share %", labels={'game_num': 'Game #', 'dmg_%': 'Dmg%'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_dmg")

                        fig = px.line(filtered_df, x='game_num', y='gold_%', color='player', markers=True,
                                      title="Gold Share %", labels={'game_num': 'Game #', 'gold_%': 'Gold%'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_gold")

                # --- Laning & Efficiency ---
                with tab_laning:
                    col1, col2 = st.columns(2)
                    with col1:
                        fig = px.line(filtered_df, x='game_num', y='cspm', color='player', markers=True,
                                      title="CS Per Minute", labels={'game_num': 'Game #', 'cspm': 'CS/M'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_cspm")

                        fig = px.line(filtered_df, x='game_num', y='harass_score', color='player', markers=True,
                                      title="Harass Score (Dmg Dealt / Taken @ 14m)",
                                      labels={'game_num': 'Game #', 'harass_score': 'Score'},
                                      template='plotly_dark')
                        fig.add_hline(y=1.0, line_dash="dash", line_color="#a6e3a1", annotation_text="Even")
                        st.plotly_chart(fig, use_container_width=True, key="trend_harass")

                    with col2:
                        fig = px.line(filtered_df, x='game_num', y='dpg', color='player', markers=True,
                                      title="Damage Per Gold (Efficiency)",
                                      labels={'game_num': 'Game #', 'dpg': 'DPG'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_dpg")

                        fig = px.line(filtered_df, x='game_num', y='jungle_prox', color='player', markers=True,
                                      title="Jungle Proximity % (0-14m)",
                                      labels={'game_num': 'Game #', 'jungle_prox': 'Prox%'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_jprox")

                # --- Advanced & Vision ---
                with tab_advanced:
                    col1, col2 = st.columns(2)
                    with col1:
                        fig = px.line(filtered_df, x='game_num', y='greed_index', color='player', markers=True,
                                      title="Greed Index (Deep / Hoard / Overstay Deaths)",
                                      labels={'game_num': 'Game #', 'greed_index': 'Greedy Events'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_greed")

                        fig = px.line(filtered_df, x='game_num', y='gank_deaths', color='player', markers=True,
                                      title="Gank Deaths (Killed by Enemy JG @ 14m)",
                                      labels={'game_num': 'Game #', 'gank_deaths': 'Deaths'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_gank")

                    with col2:
                        fig = px.line(filtered_df, x='game_num', y='vspm', color='player', markers=True,
                                      title="Vision Score Per Minute",
                                      labels={'game_num': 'Game #', 'vspm': 'VS/M'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_vspm")

                        fig = px.line(filtered_df, x='game_num', y='early_wards', color='player', markers=True,
                                      title="Wards Placed (Pre-14m)",
                                      labels={'game_num': 'Game #', 'early_wards': 'Wards'},
                                      template='plotly_dark')
                        st.plotly_chart(fig, use_container_width=True, key="trend_wards")

                # Player Averages Table
                st.markdown("---")
                st.subheader("📋 Player Averages Across All Games")
                avg_cols = ['kda_ratio', 'dpm', 'cspm', 'vspm', 'kp_%', 'dmg_%', 'gold_%',
                            'harass_score', 'greed_index', 'jungle_prox', 'gank_deaths', 'early_wards']
                avail = [c for c in avg_cols if c in filtered_df.columns]
                avg_df = filtered_df.groupby('player')[avail].mean().round(2).reset_index()
                avg_df.columns = ['Player', 'Avg KDA', 'Avg DPM', 'Avg CS/M', 'Avg VS/M',
                                  'Avg KP%', 'Avg Dmg%', 'Avg Gold%',
                                  'Avg Harass', 'Avg Greed', 'Avg JG Prox%', 'Avg Gank Deaths', 'Avg Wards<14m'][:len(avail)+1]
                st.dataframe(avg_df, use_container_width=True)

            else:
                st.info("Select at least one player to view trends.")
        else:
            st.warning("Could not calculate player trends.")

    else:
        st.write(f"Found {len(team_matches)} games together.")
        
        # Display Games
        for match in team_matches:
            match_id = match['metadata']['matchId']
            game_creation = match['info']['gameCreation']
            game_duration = match['info']['gameDuration']
            mode = match['info']['gameMode']
            
            with st.expander(f"{mode} - {match_id}"):
                # Define Tabs
                tab_overview, tab_laning, tab_vision, tab_jungle, tab_objectives, tab_teamfights = st.tabs(["📊 Overview", "⚔️ Laning", "👁️ Vision", "🌲 Jungle Pathing", "🐲 Objectives", "⚔️ Teamfights"])
                
                # --- Tab 1: Overview ---
                with tab_overview:
                    # Basic Stats
                    stats_df = get_team_stats(match, puuids.values())
                    
                    st.subheader("Team Overview")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.caption("Damage Per Minute")
                        fig_dpm = px.bar(stats_df, x='summonerName', y='dpm', color='role', title="DPM by Player", 
                                         color_discrete_sequence=CP_COLORS, template='plotly_dark')
                        st.plotly_chart(fig_dpm, use_container_width=True, key=f"dpm_{match_id}")
                        
                        st.caption("Kill Participation %")
                        fig_kp = px.bar(stats_df, x='summonerName', y='kp_%', color='role', title="Kill Participation %", 
                                        color_discrete_sequence=CP_COLORS, template='plotly_dark')
                        st.plotly_chart(fig_kp, use_container_width=True, key=f"kp_{match_id}")
        
                    with col2:
                        st.caption("Gold Share %")
                        fig_gold = px.pie(stats_df, values='gold', names='summonerName', title="Gold Distribution", 
                                          color_discrete_sequence=CP_COLORS, template='plotly_dark')
                        st.plotly_chart(fig_gold, use_container_width=True, key=f"gold_{match_id}")
        
                        st.caption("Vision Score Per Minute")
                        fig_vspm = px.bar(stats_df, x='summonerName', y='vspm', color='role', title="Vision Score / Min", 
                                          color_discrete_sequence=CP_COLORS, template='plotly_dark')
                        st.plotly_chart(fig_vspm, use_container_width=True, key=f"vspm_{match_id}")
                    
                    with st.expander("View Full Stats Table"):
                        st.dataframe(stats_df)

                # --- Deep Analysis (Fetch Timeline) ---
                try:
                    with st.spinner("Fetching Detailed Match Analysis..."):
                        timeline = fetcher.get_match_timeline(match_id)
                    
                    if timeline:
                        adv_df, found_team_pids = compute_advanced_stats(match, timeline, puuids, stats_df)
                        jungler_row = stats_df[stats_df['role'] == 'JUNGLE']
                        jun_puuid = None
                        if not jungler_row.empty:
                            from src.analysis.common import identify_jungler
                            jun_puuid = identify_jungler(stats_df, puuids, match['info']['participants'])

                        # --- Tab 2: Laning Phase ---
                        with tab_laning:
                            if not adv_df.empty:
                                col_l1, col_l2 = st.columns(2)
                                with col_l1:
                                    st.caption("Laning Harass Score (Dmg/Taken @ 14m)")
                                    fig_h = px.bar(adv_df, x='summonerName', y='harass_score', title="Harass Score", 
                                                   color='harass_score', color_continuous_scale='RdYlGn', template='plotly_dark')
                                    st.plotly_chart(fig_h, use_container_width=True, key=f"harass_{match_id}")
                                with col_l2:
                                    st.caption("Jungle Proximity % (0-14m)")
                                    j_prox_df = adv_df[adv_df['jungle_prox'] > 0]
                                    if not j_prox_df.empty:
                                        fig_j = px.bar(j_prox_df, x='summonerName', y='jungle_prox', title="Jungle Prox %", 
                                                       color='jungle_prox', color_continuous_scale='Blues', template='plotly_dark')
                                        st.plotly_chart(fig_j, use_container_width=True, key=f"prox_{match_id}")
                                    else:
                                        st.info("No meaningful jungle proximity detected.")

                        # --- Tab 3: Vision & Deaths ---
                        with tab_vision:
                            if not adv_df.empty:
                                col_v1, col_v2 = st.columns(2)
                                with col_v1:
                                    st.caption("Greedy Plays (Deep/Hoard/Overstay)")
                                    fig_g = px.bar(adv_df, x='summonerName', y='greed_index', title="Greed Index", 
                                                   color='greed_index', color_continuous_scale='Reds', template='plotly_dark')
                                    st.plotly_chart(fig_g, use_container_width=True, key=f"greed_{match_id}")

                                    st.caption("Vision Mortality (Gank Deaths vs Early Wards)")
                                    fig_v = px.scatter(adv_df, x='early_wards', y='gank_deaths', text='summonerName', 
                                                       title="Gank Susceptibility", size_max=60,
                                                       labels={'early_wards': 'Wards Placed (0-14m)', 'gank_deaths': 'Deaths to Ganks'},
                                                       template='plotly_dark')
                                    fig_v.update_traces(textposition='top center', marker=dict(size=12, color=CP_RED))
                                    fig_v.update_layout(xaxis=dict(autorange="reversed"))
                                    st.plotly_chart(fig_v, use_container_width=True, key=f"vis_{match_id}")

                                with col_v2:
                                    st.caption("Gank Visibility (Spotted vs Unspotted)")
                                    fig_s = px.bar(adv_df, x='summonerName', y=['spotted_deaths', 'unspotted_deaths'], 
                                                   title="Gank Detection",
                                                   labels={'value': 'Deaths', 'variable': 'Type'},
                                                   color_discrete_map={'spotted_deaths': CP_RED, 'unspotted_deaths': '#7f849c'},
                                                   template='plotly_dark')
                                    new_names = {'spotted_deaths': 'Spotted (Awareness)', 'unspotted_deaths': 'Unspotted (Vision)'}
                                    fig_s.for_each_trace(lambda t: t.update(name = new_names[t.name]))
                                    st.plotly_chart(fig_s, use_container_width=True, key=f"spotted_{match_id}")

                        # --- Tab 4: Jungle Pathing ---
                        with tab_jungle:
                            if jun_puuid:
                                path_df = extract_jungle_path(timeline, jun_puuid)
                                if not path_df.empty:
                                    j_name = jungler_row.iloc[0]['summonerName']
                                    j_champ = jungler_row.iloc[0]['championName']
                                    
                                    fig = go.Figure()
                                    fig.add_trace(go.Scatter(x=path_df['x'], y=path_df['y'], mode='lines', name='Path',
                                                             line=dict(color=CP_YELLOW, width=2), opacity=0.4, hoverinfo='skip'))
                                    pos_df = path_df[path_df['type'] == 'POSITION']
                                    if not pos_df.empty:
                                        fig.add_trace(go.Scatter(x=pos_df['x'], y=pos_df['y'], mode='markers+text', name='Minute',
                                                                 marker=dict(size=6, color=CP_YELLOW, opacity=0.7),
                                                                 text=(pos_df['timestamp'] / 60000).astype(int),
                                                                 textposition="top center", textfont=dict(color='white', size=9), hoverinfo='skip'))
                                    kills_df = path_df[path_df['type'].isin(['KILL_PARTICIPATION'])]
                                    if not kills_df.empty:
                                        fig.add_trace(go.Scatter(x=kills_df['x'], y=kills_df['y'], mode='markers', name='Kill/Assist',
                                                                 marker=dict(symbol='x', size=10, color=CP_RED),
                                                                 text=kills_df['timestamp'].apply(lambda x: f"{x/60000:.1f}m"),
                                                                 hovertemplate="Kil/Ast: %{text}<extra></extra>"))
                                    elite_df = path_df[path_df['type'] == 'ELITE_KILL']
                                    if not elite_df.empty:
                                        fig.add_trace(go.Scatter(x=elite_df['x'], y=elite_df['y'], mode='markers', name='Elite',
                                                                 marker=dict(symbol='star', size=15, color=CP_MAUVE),
                                                                 text=elite_df['info'], hovertemplate="Elite: %{text}<extra></extra>"))

                                    fig.update_layout(title=f"Pathing - {j_name} ({j_champ})", width=600, height=600, showlegend=True,
                                                      images=[dict(source="https://ddragon.leagueoflegends.com/cdn/16.3.1/img/map/map11.png",
                                                                   xref="x", yref="y", x=0, y=15000, sizex=15000, sizey=15000,
                                                                   sizing="stretch", opacity=0.8, layer="below")],
                                                      xaxis=dict(showgrid=False, zeroline=False, visible=False, range=[0, 15000]),
                                                      yaxis=dict(showgrid=False, zeroline=False, visible=False, range=[0, 15000]),
                                                      template='plotly_dark')
                                    st.plotly_chart(fig, use_container_width=True, key=f"path_{match_id}")
                                else:
                                    st.warning("No pathing data found.")
                            else:
                                st.info("No Jungler identified for pathing.")

                        # --- Tab 5: Objectives ---
                        with tab_objectives:
                            st.subheader("Objective Control")
                            obj_events = []
                            if timeline and 'info' in timeline and 'frames' in timeline['info']:
                                for frame in timeline['info']['frames']:
                                    for event in frame.get('events', []):
                                        if event['type'] == 'ELITE_MONSTER_KILL':
                                            obj_events.append(event)
                            
                            if obj_events:
                                obj_stats = []
                                for ev in obj_events:
                                    setup_data = analyze_objective_setup(timeline, ev, found_team_pids)
                                    killer_team = 0
                                    killer_id = ev.get('killerId')
                                    if killer_id:
                                        k_p = next((p for p in match['info']['participants'] if p['participantId'] == killer_id), None)
                                        if k_p: killer_team = k_p['teamId']

                                    our_team_id = next((p['teamId'] for p in match['info']['participants'] if p['puuid'] in puuids.values()), 100)
                                    we_secured = (killer_team == our_team_id)
                                    
                                    obj_stats.append({
                                        'Time': f"{ev['timestamp']/60000:.1f}m",
                                        'Type': ev.get('monsterType'),
                                        'Secured': "✅" if we_secured else "❌",
                                        'Wards Placed (60s pre)': setup_data['wards_placed_60s']
                                    })
                                st.table(pd.DataFrame(obj_stats))
                            else:
                                st.info("No elite monsters killed.")

                            # Objective Throw Detection
                            throws = detect_objective_throw(timeline, match, found_team_pids)
                            if throws:
                                st.subheader("🚨 Objective Throws")
                                for throw in throws:
                                    reasons_str = ', '.join(throw['reasons'])
                                    st.warning(f"**{throw['monster_type']}** lost at {throw['time_str']} — {reasons_str}")

                        # --- Tab 6: Teamfights ---
                        with tab_teamfights:
                            st.subheader("Teamfight Analysis")
                            teamfight_clusters = detect_teamfights(timeline, match)
                            if teamfight_clusters:
                                for idx, tf_kills in enumerate(teamfight_clusters):
                                    tf_data = analyze_teamfight(tf_kills, timeline, match, found_team_pids)
                                    outcome_emoji = {"Won": "🟢", "Lost": "🔴", "Even": "🟡"}.get(tf_data['outcome'], "⚪")
                                    header = f"{outcome_emoji} Fight #{idx+1} — {tf_data['start_time']/60000:.1f}m ({tf_data['team_kills']}v{tf_data['enemy_kills']} kills)"
                                    with st.expander(header, expanded=(idx == 0)):
                                        col_tf1, col_tf2 = st.columns(2)
                                        with col_tf1:
                                            st.metric("Outcome", tf_data['outcome'])
                                            st.metric("Duration", f"{tf_data['duration_s']:.1f}s")
                                            engage_side = "✅ Our team" if tf_data['engaged_by_team'] else "❌ Enemy"
                                            st.metric("Engaged By", f"{engage_side} ({tf_data['engager']['name']})")
                                        with col_tf2:
                                            st.metric("Our Kills", tf_data['team_kills'])
                                            st.metric("Our Deaths", tf_data['team_deaths'])
                                            st.metric("Players Involved", f"{len(tf_data['team_involved'])}v{len(tf_data['enemy_involved'])}")
                                        if tf_data['team_names']:
                                            st.caption("Our Team Participants:")
                                            st.write(", ".join(tf_data['team_names']))
                            else:
                                st.info("No teamfights detected (requires 3+ kills within 15s & 4000 units).")

                        # --- Game Summary (injected into Overview) ---
                        with tab_overview:
                            summary_lines = generate_game_summary(match, timeline, puuids, adv_df)
                            if summary_lines:
                                st.markdown("---")
                                st.subheader("📝 Match Summary")
                                for line in summary_lines:
                                    st.markdown(line)
                            
                            # Export & Share Buttons
                            st.markdown("---")
                            col_exp, col_disc = st.columns(2)
                            with col_exp:
                                if st.button("📸 Export Report as Image", key=f"export_{match_id}"):
                                    with st.spinner("Generating report image..."):
                                        filepath = generate_report_image(stats_df, adv_df, summary_lines, match_id)
                                    if filepath and os.path.exists(filepath):
                                        with open(filepath, 'rb') as f:
                                            st.download_button(
                                                label="⬇️ Download Report PNG",
                                                data=f,
                                                file_name=f"report_{match_id}.png",
                                                mime="image/png",
                                                key=f"dl_{match_id}"
                                            )
                                    else:
                                        st.error("Failed to generate report image. Make sure `kaleido` is installed.")
                            with col_disc:
                                if discord_webhook:
                                    if st.button("📤 Share to Discord", key=f"discord_{match_id}"):
                                        with st.spinner("Sending to Discord..."):
                                            # Generate report image for attachment
                                            img_path = generate_report_image(stats_df, adv_df, summary_lines, match_id)
                                            success, msg = send_to_discord(
                                                discord_webhook, summary_lines, stats_df, match_id,
                                                adv_df=adv_df, report_image_path=img_path
                                            )
                                        if success:
                                            st.success(msg)
                                        else:
                                            st.error(msg)
                                else:
                                    st.caption("💬 Add a Discord Webhook URL in the sidebar to enable sharing.")

                except Exception as e:
                    st.error(f"Error in Advanced Analysis: {e}")
