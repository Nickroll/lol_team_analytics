import unittest
import pandas as pd
from src.analysis.basic_stats import get_team_stats

class TestAdvancedStats(unittest.TestCase):
    def test_advanced_stats_calculation(self):
        # Mock match data
        # Game duration: 20 minutes (1200 seconds)
        mock_match = {
            'info': {
                'gameDuration': 1200,
                'participants': [
                    {
                        'puuid': 'p1', 'summonerName': 'Player1', 'championName': 'Champ1', 'teamPosition': 'TOP', 'win': True,
                        'kills': 5, 'deaths': 0, 'assists': 5, 'totalDamageDealtToChampions': 20000, 'goldEarned': 10000,
                        'totalMinionsKilled': 180, 'neutralMinionsKilled': 0, 'visionScore': 20
                    },
                    {
                        'puuid': 'p2', 'summonerName': 'Player2', 'championName': 'Champ2', 'teamPosition': 'JUNGLE', 'win': True,
                        'kills': 2, 'deaths': 2, 'assists': 8, 'totalDamageDealtToChampions': 10000, 'goldEarned': 8000,
                        'totalMinionsKilled': 20, 'neutralMinionsKilled': 140, 'visionScore': 40
                    },
                    # Add dummy players 3-5 to valid team logic but keep math simple
                    {'puuid': 'p3', 'summonerName': 'P3', 'championName': 'C3', 'teamPosition': 'MID', 'win': True, 'kills': 0, 'deaths': 0, 'assists': 0, 'totalDamageDealtToChampions': 10000, 'goldEarned': 5000, 'totalMinionsKilled': 0, 'neutralMinionsKilled': 0, 'visionScore': 0},
                    {'puuid': 'p4', 'summonerName': 'P4', 'championName': 'C4', 'teamPosition': 'BOT', 'win': True, 'kills': 0, 'deaths': 0, 'assists': 0, 'totalDamageDealtToChampions': 10000, 'goldEarned': 5000, 'totalMinionsKilled': 0, 'neutralMinionsKilled': 0, 'visionScore': 0},
                    {'puuid': 'p5', 'summonerName': 'P5', 'championName': 'C5', 'teamPosition': 'SUP', 'win': True, 'kills': 0, 'deaths': 0, 'assists': 0, 'totalDamageDealtToChampions': 0, 'goldEarned': 5000, 'totalMinionsKilled': 0, 'neutralMinionsKilled': 0, 'visionScore': 0},
                ]
            }
        }
        
        team_puuids = ['p1', 'p2', 'p3', 'p4', 'p5']
        
        df = get_team_stats(mock_match, team_puuids)
        
        # Player 1 Stats Integration
        p1 = df[df['summonerName'] == 'Player1'].iloc[0]
        
        # DPM: 20000 / 20 = 1000
        self.assertAlmostEqual(p1['dpm'], 1000.0)
        # CSPM: 180 / 20 = 9.0
        self.assertAlmostEqual(p1['cspm'], 9.0)
        # VSPM: 20 / 20 = 1.0
        self.assertAlmostEqual(p1['vspm'], 1.0)
        # KP%: (5 + 5) / (5+2+0+0+0) = 10/7 ... wait totals are 7 kills total for team.
        # Team Total Kills: 5 (p1) + 2 (p2) = 7
        # P1 KP: 10/7 * 100 = 142%?? No, assists count towards participation but max is 100% usually if you participate in all kills.
        # Formula: (K+A) / TeamKills. Yes, can be > 100% if assists logic is weird or I misunderstood formula?
        # Standard KP IS (K+A) / TeamKills. Wait, TeamKills is total kills by the team.
        # If I get a kill, I get 1 kill. If I assist, I get 1 assist.
        # The sum of Kills for the team is 7.
        # P1 participated in 5+5=10 events? That implies P1 got credit for more deaths than happened?
        # Ah, in real data, Kills + Assists for a player <= Team Kills + Team Deaths? No.
        # KP is (Player Kills + Player Assists) / Team Total Kills.
        # In this mock, P1 has 5 kills, 5 assists. P2 has 2 kills, 8 assists.
        # This implies at least 5+2=7 deaths on enemy team.
        # P1 participated in 10 kills? But team only got 7?
        # Correct, my mock data is inconsistent mathematically for a real game (P1 claims to participate in 10 kills but team only got 7).
        # But the function should just compute the ratio blindly.
        # So 10 / 7 * 100 = 142.85%
        self.assertAlmostEqual(p1['kp_%'], (10/7)*100)
        
        # Damage Share
        # Total Team Damage: 20k + 10k + 10k + 10k + 0 = 50k
        # P1 Dmg: 20k
        # Share: 20/50 = 40%
        self.assertAlmostEqual(p1['dmg_%'], 40.0)
        
        # Gold Share
        # Total Gold: 10k + 8k + 5k + 5k + 5k = 33k
        # P1 Gold: 10k
        # Share: 10/33 * 100 = 30.30%
        self.assertAlmostEqual(p1['gold_%'], (10000/33000)*100)

if __name__ == '__main__':
    unittest.main()
