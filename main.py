import streamlit as st
import pandas as pd
import plotly.express as px
from src.api.riot_client import RiotClient, ApiError
from src.api.match_fetcher import MatchFetcher
from src.analysis.basic_stats import get_team_stats
from src.analysis.jungle_pathing import extract_jungle_path
from src.config import ConfigManager
import os

# Page Config
st.set_page_config(page_title="LoL Team Analytics", layout="wide")

st.title("League of Legends Team Analytics")

# Load Config
config_manager = ConfigManager()
config = config_manager.load_config()

# Sidebar for specific player inputs
st.sidebar.header("Team Configuration")
regions = ['na1', 'euw1', 'kr', 'br1']
default_region = config.get('region', 'na1')
region_index = regions.index(default_region) if default_region in regions else 0
region = st.sidebar.selectbox("Region", regions, index=region_index) 

default_api_key = config.get('api_key', '')
api_key = st.sidebar.text_input("Riot API Key", value=default_api_key, type="password", help="Get one from developer.riotgames.com")

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
        'players': player_inputs
    }
    if config_manager.save_config(config_data):
        st.sidebar.success("Configuration saved!")
    else:
        st.sidebar.error("Failed to save configuration.")

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
                
            if len(puuids) < 5:
                st.warning(f"Could only resolve {len(puuids)}/5 summoners. Check names and try again.")
                st.write(puuids)
            else:
                st.success("All summoners resolved!")
                
                with st.spinner("Finding Team Games (this may take a moment)..."):
                    # Fetch matches (limit to last 20 for speed)
                    team_matches = fetcher.find_games_with_team(puuids, count=20)
                
                if not team_matches:
                    st.info("No recent games found with all 5 players together.")
                else:
                    st.write(f"Found {len(team_matches)} games together.")
                    
                    # Display Games
                    for match in team_matches:
                        match_id = match['metadata']['matchId']
                        game_creation = match['info']['gameCreation']
                        game_duration = match['info']['gameDuration']
                        mode = match['info']['gameMode']
                        
                        with st.expander(f"{mode} - {match_id}"):
                            # Basic Stats
                            # Basic Stats
                            stats_df = get_team_stats(match, puuids.values())
                            
                            st.subheader("Team Overview")
                            
                            # KPI Comparisons
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.caption("Damage Per Minute")
                                fig_dpm = px.bar(stats_df, x='summonerName', y='dpm', color='role', title="DPM by Player", barmode='group')
                                st.plotly_chart(fig_dpm, use_container_width=True)
                                
                                st.caption("Kill Participation %")
                                fig_kp = px.bar(stats_df, x='summonerName', y='kp_%', color='role', title="Kill Participation %", barmode='group')
                                st.plotly_chart(fig_kp, use_container_width=True)

                            with col2:
                                st.caption("Gold Share %")
                                fig_gold = px.pie(stats_df, values='gold', names='summonerName', title="Gold Distribution")
                                st.plotly_chart(fig_gold, use_container_width=True)

                                st.caption("Vision Score Per Minute")
                                fig_vspm = px.bar(stats_df, x='summonerName', y='vspm', color='role', title="Vision Score / Min", barmode='group')
                                st.plotly_chart(fig_vspm, use_container_width=True)
                            
                            with st.expander("View Full Stats Table"):
                                st.dataframe(stats_df)
                            
                            # Jungle Pathing Visualization
                            st.subheader("Jungle Pathing")
                            # Identify Jungler for the team
                            jungler_row = stats_df[stats_df['role'] == 'JUNGLE']
                            
                            if not jungler_row.empty:
                                jungler_puuid = None
                                jungler_name = jungler_row.iloc[0]['summonerName']
                                jungler_champ = jungler_row.iloc[0]['championName']
                                
                                for name, pid in puuids.items():
                                    # This is a bit fuzzy matching if name format differs, 
                                    # but stats_df has summonerName from match data
                                    if name.split('#')[0].lower() == jungler_name.split('#')[0].lower(): 
                                        jungler_puuid = pid
                                        break
                                
                                # Fallback: find puuid by iterating participants again or just store it in stats_df
                                if not jungler_puuid:
                                     target_p = next((p for p in match['info']['participants'] if p['championName'] == jungler_champ), None)
                                     if target_p:
                                         jungler_puuid = target_p['puuid']
                                
                                if jungler_puuid:
                                    try:
                                        # DEBUG: Show who we are tracking
                                        st.caption(f"Debug: Tracking Jungler: **{jungler_name}** ({jungler_champ})") 
                                        st.caption(f"PUUID: `{jungler_puuid}`")
                                        
                                        timeline = fetcher.get_match_timeline(match_id)
                                        if timeline:
                                            path_df = extract_jungle_path(timeline, jungler_puuid)
                                            
                                            if not path_df.empty:
                                                # Define colors/shapes for event types
                                                color_map = {
                                                    'POSITION': 'blue',
                                                    'ELITE_KILL': 'red',
                                                    'KILL_PARTICIPATION': 'orange',
                                                    'WARD_PLACED': 'green',
                                                    'SKILL_LEVEL_UP': 'purple',
                                                    'ITEM_PURCHASED': 'gold'
                                                }
                                                
                                                # Custom hover data
                                                fig = px.scatter(
                                                    path_df, 
                                                    x='x', 
                                                    y='y', 
                                                    color='type',
                                                    symbol='type', # Use different shapes
                                                    hover_data=['timestamp', 'info'],
                                                    title=f"Jungle Path - {jungler_name}",
                                                    color_discrete_map=color_map,
                                                    width=600,
                                                    height=600,
                                                )
                                                # Set limits to typical map size (0 to 15000 approx)
                                                # Summoner's Rift is roughly 15000x15000 units.
                                                # We need to add the map image as a layout image.
                                                # Image URL: https://ddragon.leagueoflegends.com/cdn/16.3.1/img/map/map11.png
                                                
                                                fig.update_layout(
                                                    images=[dict(
                                                        source="https://ddragon.leagueoflegends.com/cdn/16.3.1/img/map/map11.png",
                                                        xref="x",
                                                        yref="y",
                                                        x=0,
                                                        y=15000,
                                                        sizex=15000,
                                                        sizey=15000,
                                                        sizing="stretch",
                                                        opacity=0.8,
                                                        layer="below"
                                                    )],
                                                    xaxis=dict(range=[0, 15000], showgrid=False, zeroline=False, visible=False),
                                                    yaxis=dict(range=[0, 15000], showgrid=False, zeroline=False, visible=False),
                                                    width=600,
                                                    height=600,
                                                    margin=dict(l=0, r=0, t=30, b=0)
                                                )
                                                
                                                st.plotly_chart(fig)
                                            else:
                                                st.info("No pathing data available.")
                                        else:
                                            st.warning("Could not fetch timeline.")
                                    except ApiError as e:
                                        st.warning(f"Could not fetch timeline: {e}")
                            else:
                                st.info("No Jungler detected for your team in this match.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
