"""
Unit tests for full simulation and probability verification.
"""
import pytest
import sys
import os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.sim import Competition


class TestFullSimulation:
    """Test complete tournament simulation."""
    
    def get_test_data_path(self) -> str:
        """Get path to test data file."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'data', 'wc_2026_teams.json'
        )
    
    def test_simulation_completes(self):
        """Test that a full simulation completes without errors."""
        data_path = self.get_test_data_path()
        if not os.path.exists(data_path):
            pytest.skip("Test data file not found")
        
        comp = Competition.from_json_file(data_path, random_seed=42)
        champion = comp.simulate()
        
        assert champion is not None
        assert comp.runner_up is not None
        assert comp.third_place is not None
        assert champion != comp.runner_up
    
    def test_simulation_reproducibility(self):
        """Test that same seed produces same results."""
        data_path = self.get_test_data_path()
        if not os.path.exists(data_path):
            pytest.skip("Test data file not found")
        
        # Run simulation with same seed twice
        comp1 = Competition.from_json_file(data_path, random_seed=12345)
        champion1 = comp1.simulate()
        
        comp2 = Competition.from_json_file(data_path, random_seed=12345)
        champion2 = comp2.simulate()
        
        assert champion1.name == champion2.name, "Same seed should produce same champion"
        assert comp1.runner_up.name == comp2.runner_up.name
    
    def test_different_seeds_different_results(self):
        """Test that different seeds produce different results (probabilistically)."""
        data_path = self.get_test_data_path()
        if not os.path.exists(data_path):
            pytest.skip("Test data file not found")
        
        champions = set()
        for seed in range(50):
            comp = Competition.from_json_file(data_path, random_seed=seed)
            champion = comp.simulate()
            champions.add(champion.name)
        
        # With 50 different seeds, we should see multiple different champions
        assert len(champions) > 1, "Different seeds should produce variety in results"
    
    def test_reset_allows_rerun(self):
        """Test that reset() allows re-running the simulation."""
        data_path = self.get_test_data_path()
        if not os.path.exists(data_path):
            pytest.skip("Test data file not found")
        
        comp = Competition.from_json_file(data_path, random_seed=42)
        
        # Run first simulation
        champion1 = comp.simulate()
        
        # Reset and run again with different seed
        comp.reset(new_seed=999)
        champion2 = comp.simulate()
        
        # Reset and run with same seed as first
        comp.reset(new_seed=42)
        champion3 = comp.simulate()
        
        assert champion1.name == champion3.name, "Same seed should produce same result after reset"
    
    def test_all_groups_have_standings(self):
        """Test that all 12 groups have proper standings after group stage."""
        data_path = self.get_test_data_path()
        if not os.path.exists(data_path):
            pytest.skip("Test data file not found")
        
        comp = Competition.from_json_file(data_path, random_seed=42)
        comp.setup_group_matches()
        comp.play_group_stage()
        
        standings = comp.get_group_standings()
        
        assert len(standings) == 12, "Should have 12 groups"
        for group_name, teams in standings.items():
            assert len(teams) == 4, f"Group {group_name} should have 4 teams"
    
    def test_correct_number_of_matches(self):
        """Test that correct number of matches are played."""
        data_path = self.get_test_data_path()
        if not os.path.exists(data_path):
            pytest.skip("Test data file not found")
        
        comp = Competition.from_json_file(data_path, random_seed=42)
        comp.simulate()
        
        # Group stage: 12 groups × 6 matches = 72
        group_matches = sum(len(g.matches) for g in comp.groups.values())
        assert group_matches == 72, f"Expected 72 group matches, got {group_matches}"
        
        # Round of 32: 16 matches (but our simplified bracket has more due to 3rd place)
        # Just verify knockout stage has matches
        r32 = len(comp.knockout_matches[comp.knockout_matches.keys().__iter__().__next__()])
        assert r32 > 0, "Should have Round of 32 matches"


class TestProbabilityDistribution:
    """
    Test that all teams have equal probability of winning.
    
    With the current random implementation (uniform random scores 0-6),
    all teams should have roughly equal chances.
    """
    
    def test_equal_probability_mini(self):
        """Quick test with small sample size."""
        # Create a minimal 4-team competition
        teams_data = {
            "groups": {
                "A": [
                    {"name": "Team1", "confederation": "UEFA", "fifa_rank": 1, "host": False},
                    {"name": "Team2", "confederation": "UEFA", "fifa_rank": 2, "host": False},
                    {"name": "Team3", "confederation": "AFC", "fifa_rank": 3, "host": False},
                    {"name": "Team4", "confederation": "CAF", "fifa_rank": 4, "host": False},
                ],
            }
        }
        
        # Run 100 simulations
        wins = Counter()
        for seed in range(100):
            comp = Competition(teams_data=teams_data, random_seed=seed)
            comp.setup_group_matches()
            comp.play_group_stage()
            
            standings = comp.get_group_standings()['A']
            wins[standings[0].name] += 1  # Count first place finishes
        
        # Each team should win roughly 25% of the time
        # Allow wide margin due to small sample size
        for team_name in ['Team1', 'Team2', 'Team3', 'Team4']:
            win_rate = wins[team_name] / 100
            assert 0.05 < win_rate < 0.50, f"{team_name} has unusual win rate: {win_rate:.2%}"
    
    @pytest.mark.slow
    def test_equal_probability_full(self):
        """
        Full probability test with 10,000 simulations.
        
        This test verifies that with random match outcomes,
        each team has approximately equal chance of winning.
        
        Mark as slow - run with: pytest -m slow
        """
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'data', 'wc_2026_teams.json'
        )
        if not os.path.exists(data_path):
            pytest.skip("Test data file not found")
        
        num_simulations = 10000
        wins = Counter()
        
        for seed in range(num_simulations):
            comp = Competition.from_json_file(data_path, random_seed=seed)
            champion = comp.simulate()
            wins[champion.name] += 1
        
        # With 48 teams, expected win rate is ~2.08%
        expected_rate = 1.0 / 48
        
        # Use chi-squared-like test: check that no team is too far from expected
        # Allow 3x deviation from expected (very generous)
        max_allowed = expected_rate * 3
        min_allowed = expected_rate / 3
        
        for team_name, win_count in wins.items():
            win_rate = win_count / num_simulations
            assert min_allowed < win_rate < max_allowed, \
                f"{team_name} has unusual win rate: {win_rate:.4f} (expected ~{expected_rate:.4f})"
        
        # Verify all teams won at least once (very likely with 10k simulations)
        # Due to elimination format, some teams may never win, so we just check variety
        assert len(wins) >= 20, f"At least 20 different teams should win sometimes, got {len(wins)}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_host_teams_assigned_correctly(self):
        """Test that host teams are properly marked."""
        teams_data = {
            "groups": {
                "A": [
                    {"name": "Host", "confederation": "CONCACAF", "fifa_rank": 15, "host": True},
                    {"name": "NonHost", "confederation": "UEFA", "fifa_rank": 1, "host": False},
                    {"name": "Team3", "confederation": "AFC", "fifa_rank": 20, "host": False},
                    {"name": "Team4", "confederation": "CAF", "fifa_rank": 30, "host": False},
                ],
            }
        }
        
        comp = Competition(teams_data=teams_data, random_seed=42)
        
        host_teams = [t for t in comp.teams if t.host]
        non_host_teams = [t for t in comp.teams if not t.host]
        
        assert len(host_teams) == 1
        assert host_teams[0].name == "Host"
        assert len(non_host_teams) == 3
    
    def test_all_matches_have_valid_scores(self):
        """Test that all matches have valid score values."""
        teams_data = {
            "groups": {
                "A": [
                    {"name": "T1", "confederation": "UEFA", "fifa_rank": 1, "host": False},
                    {"name": "T2", "confederation": "UEFA", "fifa_rank": 2, "host": False},
                    {"name": "T3", "confederation": "AFC", "fifa_rank": 3, "host": False},
                    {"name": "T4", "confederation": "CAF", "fifa_rank": 4, "host": False},
                ],
            }
        }
        
        for seed in range(100):
            comp = Competition(teams_data=teams_data, random_seed=seed)
            comp.setup_group_matches()
            comp.play_group_stage()
            
            for match in comp.all_matches:
                assert match.home_score is not None
                assert match.away_score is not None
                assert 0 <= match.home_score <= 6
                assert 0 <= match.away_score <= 6


# Configure pytest markers
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (run with -m slow)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
