import os
from riotwatcher import LolWatcher, ApiError
from dotenv import load_dotenv

load_dotenv()

class RiotClient:
    def __init__(self, api_key=None, region='na1'):
        self.api_key = api_key or os.getenv('RIOT_API_KEY')
        if not self.api_key:
            raise ValueError("Riot API Key is required. Set it in .env or pass it to the constructor.")
        
        self.watcher = LolWatcher(self.api_key)
        self.region = region

    def get_summoner_by_name(self, summoner_name):
        """
        Fetches summoner details by summoner name.
        """
        try:
            # Riot API now uses name + tag, but for simplicity we'll assume the old way 
            # or expect name#tag format if supported by watcher, 
            # actually RiotWatcher might still use the old endpoint for some regions or we need to use AccountV1
            # Let's use AccountV1 to get PUUID if possible, or SummonerV4 if name is simple.
            # Given the recent changes, it's safer to use Account API for Riot ID (Name + Tag)
            
            if '#' in summoner_name:
                game_name, tag_line = summoner_name.split('#')
                account = self.watcher.account.by_riot_id(self.region, game_name, tag_line)
                # Then get summoner by PUUID to get summoner ID if needed, but PUUID is best for match history
                return self.watcher.summoner.by_puuid(self.region, account['puuid'])
            else:
                # Fallback to old behavior if no tag provided (might fail in some regions)
                return self.watcher.summoner.by_name(self.region, summoner_name)
        except ApiError as err:
            if err.response.status_code == 429:
                print('We should retry in {} seconds.'.format(err.response.headers['Retry-After']))
            elif err.response.status_code == 404:
                print('Summoner not found.')
            raise

    def get_match_ids(self, puuid, count=20, start=0, queue=None):
        """
        Fetches match IDs for a given PUUID.
        """
        try:
            # Match V5 routing is usually by AMERICAS, EUROPE, ASIA, etc.
            # We need to map region to routing value.
            routing = self._get_routing_value(self.region)
            return self.watcher.match.matchlist_by_puuid(routing, puuid, count=count, start=start, queue=queue)
        except ApiError as err:
            raise

    def get_match_details(self, match_id):
        """
        Fetches detailed information for a specific match.
        """
        try:
            routing = self._get_routing_value(self.region)
            return self.watcher.match.by_id(routing, match_id)
        except ApiError as err:
            raise

    def get_match_timeline(self, match_id):
        """
        Fetches the timeline for a specific match.
        """
        try:
            routing = self._get_routing_value(self.region)
            return self.watcher.match.timeline_by_match_id(routing, match_id)
        except ApiError as err:
            raise

    def _get_routing_value(self, region):
        # Simple mapping, can be expanded
        if region in ['na1', 'br1', 'la1', 'la2']:
            return 'americas'
        elif region in ['euw1', 'eun1', 'tr1', 'ru']:
            return 'europe'
        elif region in ['kr', 'jp1']:
            return 'asia'
        return 'americas' # Default fallback
