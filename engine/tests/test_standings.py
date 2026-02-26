"""
Unit tests for group stage standings and tiebreaker logic.
"""
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.core import STAGE, Team, Match, Group


class TestGroupStandings:
    """Test group stage standings calculations."""
    
    def create_group_with_teams(self) -> tuple[Group, list[Team]]:
        """Helper to create a group with 4 teams."""
        group = Group("A")
        teams = [
            Team("Spain", "UEFA", 1),
            Team("Germany", "UEFA", 10),
            Team("Japan", "AFC", 19),
            Team("Costa Rica", "CONCACAF", 51),
        ]
        for team in teams:
            group.add_team(team)
        return group, teams
    
    def play_match(self, group: Group, home: Team, away: Team, 
                   home_score: int, away_score: int):
        """Helper to create and play a match with specific scores."""
        match = Match(1, None, STAGE.GROUP_STAGE, group)
        match.assign_teams(home, away)
        match.home_score = home_score
        match.away_score = away_score
        group.add_match(match)
        return match
    
    def test_basic_standings_by_points(self):
        """Teams should be ranked by points (3 for win, 1 for draw, 0 for loss)."""
        group, teams = self.create_group_with_teams()
        spain, germany, japan, costa_rica = teams
        
        # Spain wins all (9 pts)
        self.play_match(group, spain, germany, 2, 0)
        self.play_match(group, spain, japan, 3, 1)
        self.play_match(group, spain, costa_rica, 7, 0)
        
        # Germany wins 2 (6 pts)
        self.play_match(group, germany, japan, 1, 0)
        self.play_match(group, germany, costa_rica, 4, 2)
        
        # Japan beats Costa Rica (3 pts)
        self.play_match(group, japan, costa_rica, 2, 0)
        
        standings = group.get_standings()
        
        assert standings[0] == spain, "Spain should be 1st with 9 pts"
        assert standings[1] == germany, "Germany should be 2nd with 6 pts"
        assert standings[2] == japan, "Japan should be 3rd with 3 pts"
        assert standings[3] == costa_rica, "Costa Rica should be 4th with 0 pts"
    
    def test_tiebreaker_goal_difference(self):
        """When points are equal, goal difference should break the tie."""
        group, teams = self.create_group_with_teams()
        spain, germany, japan, costa_rica = teams
        
        # Spain and Germany both get 6 pts, but Spain has better GD
        self.play_match(group, spain, germany, 1, 1)  # Draw
        self.play_match(group, spain, japan, 4, 0)     # Spain wins big
        self.play_match(group, spain, costa_rica, 3, 0)
        
        self.play_match(group, germany, japan, 2, 1)
        self.play_match(group, germany, costa_rica, 1, 0)
        
        self.play_match(group, japan, costa_rica, 0, 0)
        
        standings = group.get_standings()
        
        # Spain: 7 pts (2W 1D), GD +7
        # Germany: 7 pts (2W 1D), GD +2
        assert standings[0] == spain, "Spain should be 1st (better GD)"
        assert standings[1] == germany, "Germany should be 2nd"
    
    def test_tiebreaker_goals_scored(self):
        """When points and GD are equal, goals scored should break the tie."""
        group, teams = self.create_group_with_teams()
        spain, germany, japan, costa_rica = teams
        
        # Both get same points and GD, but Spain scores more
        self.play_match(group, spain, germany, 2, 2)
        self.play_match(group, spain, japan, 3, 0)
        self.play_match(group, spain, costa_rica, 2, 1)
        
        self.play_match(group, germany, japan, 2, 0)
        self.play_match(group, germany, costa_rica, 2, 0)
        
        self.play_match(group, japan, costa_rica, 0, 0)
        
        standings = group.get_standings()
        
        # Spain: 7 pts, GD +4, GF 7
        # Germany: 7 pts, GD +4, GF 6
        assert standings[0] == spain, "Spain should be 1st (more goals scored)"
        assert standings[1] == germany, "Germany should be 2nd"
    
    def test_tiebreaker_head_to_head(self):
        """Head-to-head results should be primary tiebreaker for same points."""
        group, teams = self.create_group_with_teams()
        spain, germany, japan, costa_rica = teams
        
        # Spain beats Germany head-to-head
        self.play_match(group, spain, germany, 2, 1)
        
        # Both lose to Japan
        self.play_match(group, japan, spain, 2, 1)
        self.play_match(group, japan, germany, 2, 1)
        
        # Both beat Costa Rica with same margin
        self.play_match(group, spain, costa_rica, 2, 0)
        self.play_match(group, germany, costa_rica, 2, 0)
        
        # Japan and Costa Rica draw
        self.play_match(group, japan, costa_rica, 0, 0)
        
        standings = group.get_standings()
        
        # Japan: 7 pts (2W 1D)
        # Spain: 6 pts (2W 1L), beat Germany H2H
        # Germany: 6 pts (2W 1L)
        # Costa Rica: 1 pt (1D 2L)
        assert standings[0] == japan, "Japan should be 1st with 7 pts"
        assert standings[1] == spain, "Spain should be 2nd (H2H vs Germany)"
        assert standings[2] == germany, "Germany should be 3rd"
    
    def test_tiebreaker_fifa_ranking_fallback(self):
        """FIFA ranking should be used when all other criteria are equal."""
        group, teams = self.create_group_with_teams()
        spain, germany, japan, costa_rica = teams
        
        # All teams draw all matches
        self.play_match(group, spain, germany, 0, 0)
        self.play_match(group, spain, japan, 0, 0)
        self.play_match(group, spain, costa_rica, 0, 0)
        self.play_match(group, germany, japan, 0, 0)
        self.play_match(group, germany, costa_rica, 0, 0)
        self.play_match(group, japan, costa_rica, 0, 0)
        
        standings = group.get_standings()
        
        # All have 3 pts, 0 GD, 0 GF -> rank by FIFA ranking
        assert standings[0] == spain, "Spain should be 1st (rank 1)"
        assert standings[1] == germany, "Germany should be 2nd (rank 10)"
        assert standings[2] == japan, "Japan should be 3rd (rank 19)"
        assert standings[3] == costa_rica, "Costa Rica should be 4th (rank 51)"


class TestTeamStats:
    """Test team statistics calculations."""
    
    def test_get_group_stats(self):
        """Test that team stats are calculated correctly."""
        group = Group("A")
        team1 = Team("Team1", "UEFA", 1)
        team2 = Team("Team2", "UEFA", 2)
        group.add_team(team1)
        group.add_team(team2)
        
        match = Match(1, None, STAGE.GROUP_STAGE, group)
        match.assign_teams(team1, team2)
        match.home_score = 3
        match.away_score = 1
        group.add_match(match)
        
        stats1 = team1.get_group_stats()
        stats2 = team2.get_group_stats()
        
        assert stats1['played'] == 1
        assert stats1['wins'] == 1
        assert stats1['goals_for'] == 3
        assert stats1['goals_against'] == 1
        assert stats1['goal_difference'] == 2
        assert stats1['points'] == 3
        
        assert stats2['played'] == 1
        assert stats2['losses'] == 1
        assert stats2['goals_for'] == 1
        assert stats2['goals_against'] == 3
        assert stats2['goal_difference'] == -2
        assert stats2['points'] == 0
    
    def test_draw_gives_one_point(self):
        """Test that a draw gives 1 point to each team."""
        group = Group("A")
        team1 = Team("Team1", "UEFA", 1)
        team2 = Team("Team2", "UEFA", 2)
        group.add_team(team1)
        group.add_team(team2)
        
        match = Match(1, None, STAGE.GROUP_STAGE, group)
        match.assign_teams(team1, team2)
        match.home_score = 2
        match.away_score = 2
        group.add_match(match)
        
        stats1 = team1.get_group_stats()
        stats2 = team2.get_group_stats()
        
        assert stats1['draws'] == 1
        assert stats1['points'] == 1
        assert stats2['draws'] == 1
        assert stats2['points'] == 1


class TestMatchPlay:
    """Test match simulation."""
    
    def test_match_play_generates_scores(self):
        """Match.play() should generate valid scores."""
        import random
        rng = random.Random(42)
        match = Match(1, None, STAGE.GROUP_STAGE, rng=rng)
        team1 = Team("Team1", "UEFA", 1)
        team2 = Team("Team2", "UEFA", 2)
        match.assign_teams(team1, team2)
        
        home_score, away_score = match.play()
        
        assert 0 <= home_score <= 6
        assert 0 <= away_score <= 6
        assert match.home_score == home_score
        assert match.away_score == away_score
    
    def test_knockout_match_no_draw(self):
        """Knockout matches should not end in a draw."""
        import random
        
        # Run multiple times to ensure no draws occur
        for seed in range(100):
            rng = random.Random(seed)
            match = Match(1, None, STAGE.ROUND_OF_16, rng=rng)
            team1 = Team("Team1", "UEFA", 1)
            team2 = Team("Team2", "UEFA", 2)
            match.assign_teams(team1, team2)
            
            home_score, away_score = match.play()
            
            assert home_score != away_score, f"Knockout match should not draw (seed={seed})"
    
    def test_reproducible_with_seed(self):
        """Same seed should produce same results."""
        import random
        
        results1 = []
        results2 = []
        
        for match_num in range(5):
            rng1 = random.Random(42)
            match1 = Match(match_num, None, STAGE.GROUP_STAGE, rng=rng1)
            match1.assign_teams(Team("A", "UEFA", 1), Team("B", "UEFA", 2))
            results1.append(match1.play())
            
            rng2 = random.Random(42)
            match2 = Match(match_num, None, STAGE.GROUP_STAGE, rng=rng2)
            match2.assign_teams(Team("A", "UEFA", 1), Team("B", "UEFA", 2))
            results2.append(match2.play())
        
        assert results1 == results2, "Same seed should produce same results"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
