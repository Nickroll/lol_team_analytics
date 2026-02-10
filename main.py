import streamlit as st
import pandas as pd
import plotly.express as px
from src.api.riot_client import RiotClient, ApiError
from src.api.match_fetcher import MatchFetcher
from src.analysis.basic_stats import get_team_stats
from src.analysis.jungle_pathing import extract_jungle_path
import os

# Page Config
st.set_page_config(page_title="LoL Team Analytics", layout="wide")

st.title("League of Legends Team Analytics")

# Sidebar for specific player inputs
st.sidebar.header("Team Configuration")
region = st.sidebar.selectbox("Region", ['na1', 'euw1', 'kr', 'br1']) # Add more as needed
api_key = st.sidebar.text_input("Riot API Key", type="password", help="Get one from developer.riotgames.com")

st.sidebar.subheader("Summoner Names (Name#Tag)")
player_inputs = []
for i in range(5):
    player_inputs.append(st.sidebar.text_input(f"Player {i+1}", key=f"p{i}"))

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
                            stats_df = get_team_stats(match, puuids.values())
                            st.dataframe(stats_df)
                            
                            # Jungle Pathing Visualization
                            st.subheader("Jungle Pathing")
                            # Identify Jungler for the team
                            jungler_row = stats_df[stats_df['role'] == 'JUNGLE']
                            
                            if not jungler_row.empty:
                                jungler_puuid = None
                                jungler_name = jungler_row.iloc[0]['summonerName']
                                for name, pid in puuids.items():
                                    # This is a bit fuzzy matching if name format differs, 
                                    # but stats_df has summonerName from match data
                                    if name.split('#')[0].lower() == jungler_name.lower(): 
                                        jungler_puuid = pid
                                        break
                                # Fallback: find puuid by iterating participants again or just store it in stats_df
                                # Let's update basic_stats to include PUUID to make this easier next time.
                                # For now, let's just find the generic participant matching the name
                                target_p = next((p for p in match['info']['participants'] if p['summonerName'] == jungler_name), None)
                                if target_p:
                                    jungler_puuid = target_p['puuid']
                                
                                if jungler_puuid:
                                    try:
                                        timeline = client.get_match_timeline(match_id)
                                        path_df = extract_jungle_path(timeline, jungler_puuid)
                                        
                                        if not path_df.empty:
                                            fig = px.scatter(
                                                path_df, 
                                                x='x', 
                                                y='y', 
                                                color='type',
                                                hover_data=['timestamp'],
                                                title=f"Jungle Path - {jungler_name}",
                                                width=600,
                                                height=600
                                            )
                                            # Set limits to typical map size (0 to 15000 approx)
                                            fig.update_xaxes(range=[0, 15000])
                                            fig.update_yaxes(range=[0, 15000])
                                            # Invert Y if needed? No, Summoner's Rift 0,0 is bottom left.
                                            
                                            st.plotly_chart(fig)
                                        else:
                                            st.info("No pathing data available.")
                                    except ApiError as e:
                                        st.warning(f"Could not fetch timeline: {e}")
                            else:
                                st.info("No Jungler detected for your team in this match.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
