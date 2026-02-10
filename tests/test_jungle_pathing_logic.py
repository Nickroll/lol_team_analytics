import unittest
import pandas as pd
from src.analysis.jungle_pathing import extract_jungle_path

class TestJunglePathingLogic(unittest.TestCase):
    def test_pathing_cutoff_15_min(self):
        # Mock timeline with frames spanning 20 minutes
        # We expect points up to 15 min (900000ms)
        puuid = 'p1'
        
        timeline_data = {
            'info': {
                'participants': [{'participantId': 1, 'puuid': 'p1'}],
                'frames': [
                    {'timestamp': 0, 'events': [], 'participantFrames': {'1': {'position': {'x': 0, 'y': 0}}}},
                    {'timestamp': 300000, 'events': [], 'participantFrames': {'1': {'position': {'x': 0, 'y': 0}}}}, # 5m
                    {'timestamp': 600000, 'events': [], 'participantFrames': {'1': {'position': {'x': 0, 'y': 0}}}}, # 10m
                    {'timestamp': 900000, 'events': [], 'participantFrames': {'1': {'position': {'x': 0, 'y': 0}}}}, # 15m - Last included
                    {'timestamp': 1200000, 'events': [], 'participantFrames': {'1': {'position': {'x': 0, 'y': 0}}}}, # 20m - Excluded
                ]
            }
        }
        
        df = extract_jungle_path(timeline_data, puuid)
        
        # Should include frames 0, 5, 10, 15
        self.assertEqual(len(df), 4)
        self.assertEqual(df.iloc[-1]['timestamp'], 900000)

    def test_pathing_short_game(self):
        # Mock timeline for a 10 min game
        # Should include all frames
        puuid = 'p1'
        
        timeline_data = {
            'info': {
                'participants': [{'participantId': 1, 'puuid': 'p1'}],
                'frames': [
                    {'timestamp': 0, 'events': [], 'participantFrames': {'1': {'position': {'x': 0, 'y': 0}}}},
                    {'timestamp': 300000, 'events': [], 'participantFrames': {'1': {'position': {'x': 0, 'y': 0}}}}, # 5m
                    {'timestamp': 600000, 'events': [], 'participantFrames': {'1': {'position': {'x': 0, 'y': 0}}}}, # 10m
                ]
            }
        }
        
        df = extract_jungle_path(timeline_data, puuid)
        
        self.assertEqual(len(df), 3)
        self.assertEqual(df.iloc[-1]['timestamp'], 600000)

    def test_ward_interpolation(self):
        # Mock timeline with a Ward placed between frames
        puuid = 'p1'
        participant_id = 1
        
        timeline_data = {
            'info': {
                'participants': [{'participantId': 1, 'puuid': 'p1'}],
                'frames': [
                    {
                        'timestamp': 0, 
                        'events': [], 
                        'participantFrames': {'1': {'position': {'x': 0, 'y': 0}}}
                    },
                    {
                        'timestamp': 1000, 
                        'events': [
                            {
                                'type': 'WARD_PLACED',
                                'timestamp': 500, # Halfway
                                'creatorId': 1,
                                'wardType': 'YELLOW_TRINKET'
                            }
                        ], 
                        'participantFrames': {'1': {'position': {'x': 100, 'y': 100}}}
                    }
                ]
            }
        }
        
        df = extract_jungle_path(timeline_data, puuid)
        
        # Expect:
        # 1. Position at 0 (0,0)
        # 2. Ward at 500 (interpolated: 50, 50)
        # 3. Position at 1000 (100, 100)
        
        self.assertEqual(len(df), 3)
        
        ward_row = df[df['type'] == 'WARD_PLACED'].iloc[0]
        self.assertEqual(ward_row['timestamp'], 500)
        self.assertEqual(ward_row['x'], 50)
        self.assertEqual(ward_row['y'], 50)

if __name__ == '__main__':
    unittest.main()
