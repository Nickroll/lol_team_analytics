from .riot_client import RiotClient
from .match_cache import MatchCache
import time

class MatchFetcher:
    def __init__(self, riot_client: RiotClient):
        self.client = riot_client
        self.cache = MatchCache()

    def get_puuids_from_names(self, summoner_names):
        """
        Resolves a list of summoner names (Name#Tag) to PUUIDs.
        """
        puuids = {}
        for name in summoner_names:
            try:
                summoner = self.client.get_summoner_by_name(name)
                puuids[name] = summoner['puuid']
            except Exception as e:
                print(f"Error resolving {name}: {e}")
        return puuids

    def find_games_with_team(self, puuids, count=20, queue=None):
        """
        Finds matches where ALL given PUUIDs are present.
        """
        if not puuids:
            return []
        
        # We only need to fetch match history for one player, then filter.
        # It's best to pick the one with the most recent games if possible, 
        # but for now we just pick the first one.
        first_puuid = list(puuids.values())[0]
        
        # Get match IDs
        match_ids = self.client.get_match_ids(first_puuid, count=count, queue=queue)
        
        team_matches = []
        target_puuids = set(puuids.values())

        for match_id in match_ids:
            try:
                # Check Cache
                details = self.cache.get_match(match_id)
                if not details:
                    # Fetch from API
                    details = self.client.get_match_details(match_id)
                    # Save to Cache
                    self.cache.save_match(match_id, details)
                
                participants = details['metadata']['participants']
                
                # Check if all target PUUIDs are in this match
                if target_puuids.issubset(set(participants)):
                    team_matches.append(details)
                    
            except Exception as e:
                print(f"Error fetching details for {match_id}: {e}")
                
                
        return team_matches

    def get_match_timeline(self, match_id):
        """
        Fetches match timeline, checking cache first.
        """
        timeline = self.cache.get_timeline(match_id)
        if not timeline:
            try:
                timeline = self.client.get_match_timeline(match_id)
                self.cache.save_timeline(match_id, timeline)
            except Exception as e:
                print(f"Error fetching timeline for {match_id}: {e}")
                return None
        return timeline
