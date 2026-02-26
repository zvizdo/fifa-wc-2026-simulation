"""
Unit tests for third-place team rankings.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.core import STAGE, Team, Match, Group
from engine.sim import Competition


class TestThirdPlaceRanking:
    """Test third-place team ranking logic."""
    
    def create_mock_competition(self) -> Competition:
        """Create a competition with simplified group data."""
        teams_data = {
            "groups": {
                "A": [
                    {"name": "A1", "confederation": "UEFA", "fifa_rank": 1, "host": False},
                    {"name": "A2", "confederation": "UEFA", "fifa_rank": 10, "host": False},
                    {"name": "A3", "confederation": "AFC", "fifa_rank": 20, "host": False},
                    {"name": "A4", "confederation": "CAF", "fifa_rank": 30, "host": False},
                ],
                "B": [
                    {"name": "B1", "confederation": "UEFA", "fifa_rank": 2, "host": False},
                    {"name": "B2", "confederation": "UEFA", "fifa_rank": 11, "host": False},
                    {"name": "B3", "confederation": "AFC", "fifa_rank": 21, "host": False},
                    {"name": "B4", "confederation": "CAF", "fifa_rank": 31, "host": False},
                ],
                "C": [
                    {"name": "C1", "confederation": "UEFA", "fifa_rank": 3, "host": False},
                    {"name": "C2", "confederation": "UEFA", "fifa_rank": 12, "host": False},
                    {"name": "C3", "confederation": "AFC", "fifa_rank": 22, "host": False},
                    {"name": "C4", "confederation": "CAF", "fifa_rank": 32, "host": False},
                ],
                "D": [
                    {"name": "D1", "confederation": "UEFA", "fifa_rank": 4, "host": False},
                    {"name": "D2", "confederation": "UEFA", "fifa_rank": 13, "host": False},
                    {"name": "D3", "confederation": "AFC", "fifa_rank": 23, "host": False},
                    {"name": "D4", "confederation": "CAF", "fifa_rank": 33, "host": False},
                ],
            }
        }
        return Competition(teams_data=teams_data, random_seed=42)
    
    def setup_group_results(self, group: Group, third_place_stats: dict):
        """
        Set up group matches to give the third-place team specific stats.
        
        third_place_stats should have: points, gd, gf
        """
        teams = group.teams
        t1, t2, t3, t4 = teams
        
        # T1 wins all (9 pts) - 1st place
        # T2 wins 2, loses 1 (6 pts) - 2nd place
        # T3 gets the specified stats - 3rd place
        # T4 loses all (0 pts) - 4th place
        
        pts = third_place_stats['points']
        
        def add_match(home, away, h_score, a_score):
            match = Match(len(group.matches) + 1, None, STAGE.GROUP_STAGE, group)
            match.assign_teams(home, away)
            match.home_score = h_score
            match.away_score = a_score
            group.add_match(match)
        
        # Standard results for 1st and 4th
        add_match(t1, t2, 2, 1)  # T1 beats T2
        add_match(t1, t3, 3, 1)  # T1 beats T3
        add_match(t1, t4, 2, 0)  # T1 beats T4
        
        add_match(t2, t3, 2, 1)  # T2 beats T3
        add_match(t2, t4, 1, 0)  # T2 beats T4
        
        # T3 vs T4 - adjust for desired T3 stats
        if pts >= 3:  # T3 beats T4
            gf = third_place_stats.get('gf', 2)
            ga = gf - third_place_stats.get('gd', 0) - 2  # offset for other losses
            add_match(t3, t4, max(1, gf), max(0, ga))
        else:  # T3 draws or loses to T4
            add_match(t3, t4, 0, 0)
    
    def test_third_place_ranked_by_points(self):
        """Third-place teams should be ranked by points first."""
        comp = self.create_mock_competition()
        comp.setup_group_matches()
        
        # Manually set up matches with controlled outcomes
        # Clear auto-generated matches
        for group in comp.groups.values():
            group.matches = []
            for team in group.teams:
                team.matches = []
        
        # Group A third place: 4 points
        self.setup_group_results(comp.groups['A'], {'points': 4, 'gd': 1, 'gf': 3})
        # Group B third place: 3 points
        self.setup_group_results(comp.groups['B'], {'points': 3, 'gd': 0, 'gf': 2})
        # Group C third place: 3 points
        self.setup_group_results(comp.groups['C'], {'points': 3, 'gd': -1, 'gf': 1})
        # Group D third place: 1 point
        self.setup_group_results(comp.groups['D'], {'points': 1, 'gd': -2, 'gf': 0})
        
        ranked = comp.rank_third_place_teams()
        
        # Should be ordered by points: A3 (4) > B3 (3) > C3 (3) > D3 (1)
        assert ranked[0].name == 'A3', "A3 should be first (4 pts)"
        assert ranked[-1].name == 'D3', "D3 should be last (1 pt)"
    
    def test_third_place_tiebreaker_goal_difference(self):
        """When points are equal, GD should break the tie."""
        comp = self.create_mock_competition()
        comp.setup_group_matches()
        
        for group in comp.groups.values():
            group.matches = []
            for team in group.teams:
                team.matches = []
        
        # All third-place teams get 3 points, different GD
        self.setup_group_results(comp.groups['A'], {'points': 3, 'gd': 2, 'gf': 3})
        self.setup_group_results(comp.groups['B'], {'points': 3, 'gd': 0, 'gf': 2})
        self.setup_group_results(comp.groups['C'], {'points': 3, 'gd': -1, 'gf': 1})
        self.setup_group_results(comp.groups['D'], {'points': 3, 'gd': -2, 'gf': 0})
        
        ranked = comp.rank_third_place_teams()
        
        assert ranked[0].name == 'A3', "A3 should be first (GD +2)"
        assert ranked[1].name == 'B3', "B3 should be second (GD 0)"
        assert ranked[2].name == 'C3', "C3 should be third (GD -1)"
        assert ranked[3].name == 'D3', "D3 should be fourth (GD -2)"
    
    def test_third_place_tiebreaker_goals_scored(self):
        """When points and GD are equal, goals scored should break the tie."""
        comp = self.create_mock_competition()
        comp.setup_group_matches()
        
        for group in comp.groups.values():
            group.matches = []
            for team in group.teams:
                team.matches = []
        
        # All get 3 points, same GD (-1), different GF
        self.setup_group_results(comp.groups['A'], {'points': 3, 'gd': -1, 'gf': 4})
        self.setup_group_results(comp.groups['B'], {'points': 3, 'gd': -1, 'gf': 3})
        self.setup_group_results(comp.groups['C'], {'points': 3, 'gd': -1, 'gf': 2})
        self.setup_group_results(comp.groups['D'], {'points': 3, 'gd': -1, 'gf': 1})
        
        ranked = comp.rank_third_place_teams()
        
        assert ranked[0].name == 'A3', "A3 should be first (GF 4)"
        assert ranked[1].name == 'B3', "B3 should be second (GF 3)"
    
    def test_third_place_tiebreaker_fifa_ranking(self):
        """When all stats are equal, FIFA ranking should break the tie."""
        comp = self.create_mock_competition()
        comp.setup_group_matches()
        
        for group in comp.groups.values():
            group.matches = []
            for team in group.teams:
                team.matches = []
        
        # All identical stats
        for g_name in ['A', 'B', 'C', 'D']:
            self.setup_group_results(comp.groups[g_name], {'points': 3, 'gd': 0, 'gf': 2})
        
        ranked = comp.rank_third_place_teams()
        
        # Should be sorted by FIFA ranking (A3=20, B3=21, C3=22, D3=23)
        assert ranked[0].name == 'A3', "A3 should be first (rank 20)"
        assert ranked[1].name == 'B3', "B3 should be second (rank 21)"
        assert ranked[2].name == 'C3', "C3 should be third (rank 22)"
        assert ranked[3].name == 'D3', "D3 should be fourth (rank 23)"
    
    def test_best_eight_advance(self):
        """Only the best 8 third-place teams should advance."""
        # Create a competition with 12 groups
        teams_data = {"groups": {}}
        for i, letter in enumerate("ABCDEFGHIJKL"):
            teams_data["groups"][letter] = [
                {"name": f"{letter}1", "confederation": "UEFA", "fifa_rank": i*4 + 1, "host": False},
                {"name": f"{letter}2", "confederation": "UEFA", "fifa_rank": i*4 + 2, "host": False},
                {"name": f"{letter}3", "confederation": "AFC", "fifa_rank": i*4 + 3, "host": False},
                {"name": f"{letter}4", "confederation": "CAF", "fifa_rank": i*4 + 4, "host": False},
            ]
        
        comp = Competition(teams_data=teams_data, random_seed=42)
        comp.setup_group_matches()
        comp.play_group_stage()
        
        ranked = comp.rank_third_place_teams()
        
        assert len(ranked) == 12, "Should have 12 third-place teams"
        assert len(comp.advancing_third_place) == 8, "Only 8 should advance"
        
        # Verify the advancing teams are the top 8
        for team in comp.advancing_third_place:
            assert team in ranked[:8], f"{team.name} should be in top 8"


class TestCompetitionFlow:
    """Test competition setup and flow."""
    
    def test_competition_from_json(self):
        """Test loading competition from JSON file."""
        import json
        import tempfile
        
        data = {
            "groups": {
                "A": [
                    {"name": "Team1", "confederation": "UEFA", "fifa_rank": 1, "host": True},
                    {"name": "Team2", "confederation": "UEFA", "fifa_rank": 10, "host": False},
                    {"name": "Team3", "confederation": "AFC", "fifa_rank": 20, "host": False},
                    {"name": "Team4", "confederation": "CAF", "fifa_rank": 30, "host": False},
                ]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        
        try:
            comp = Competition.from_json_file(temp_path, random_seed=42)
            assert len(comp.groups) == 1
            assert len(comp.teams) == 4
            assert comp.teams[0].host == True
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
