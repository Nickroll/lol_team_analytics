import os
from riotwatcher import LolWatcher, RiotWatcher, ApiError
from dotenv import load_dotenv

load_dotenv()

class RiotClient:
    def __init__(self, api_key=None, region='na1'):
        self.api_key = api_key or os.getenv('RIOT_API_KEY')
        if not self.api_key:
            raise ValueError("Riot API Key is required. Set it in .env or pass it to the constructor.")
        
        self.watcher = LolWatcher(self.api_key)
        self.riot_watcher = RiotWatcher(self.api_key)
        self.region = region

    def get_summoner_by_name(self, summoner_name):
        """
        Fetches summoner details by summoner name or Riot ID (Name#Tag).
        """
        try:
            if '#' in summoner_name:
                game_name, tag_line = summoner_name.split('#')
                # Account API requires regional routing (americas, europe, asia)
                routing = self._get_routing_value(self.region)
                account = self.riot_watcher.account.by_riot_id(routing, game_name, tag_line)
                # Summoner API uses platform routing (na1, euw1, etc.)
                return self.watcher.summoner.by_puuid(self.region, account['puuid'])
            else:
                # Fallback to old behavior if no tag provided (Summoner V4)
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
            return self.watcher.match.timeline_by_match(routing, match_id)
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
