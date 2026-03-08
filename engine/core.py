"""
Core classes for FIFA World Cup 2026 simulation.
"""
import random
from enum import Enum
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .venues import HostCity


class STAGE(Enum):
    """Tournament stages."""
    GROUP_STAGE = "GROUP_STAGE"
    ROUND_OF_32 = "ROUND_OF_32"
    ROUND_OF_16 = "ROUND_OF_16"
    QUARTER_FINALS = "QUARTER_FINALS"
    SEMI_FINALS = "SEMI_FINALS"
    THIRD_PLACE = "THIRD_PLACE"
    FINAL = "FINAL"


class Team:
    """Represents a national team in the World Cup."""
    
    def __init__(self, name: str, confederation: str, fifa_rank: int, host: bool = False):
        self.name = name
        self.confederation = confederation
        self.fifa_rank = fifa_rank
        self.host = host
        self.group: Optional['Group'] = None
        self.matches: List['Match'] = []

        self.current_rank = fifa_rank
        self.current_off_rank = fifa_rank
        self.current_def_rank = fifa_rank

        self._group_stats_cache: Optional[dict] = None

    def assign_group(self, group: 'Group'):
        """Assign this team to a group."""
        self.group = group

    def add_match(self, match: 'Match'):
        """Add a match to this team's history."""
        self.matches.append(match)
        self._group_stats_cache = None  # invalidate cache

    def get_group_matches(self) -> List['Match']:
        """Get only group stage matches."""
        return [m for m in self.matches if m.stage == STAGE.GROUP_STAGE]

    def get_group_stats(self) -> dict:
        """Calculate group stage statistics for this team (cached)."""
        if self._group_stats_cache is not None:
            return self._group_stats_cache

        stats = {
            'played': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'goal_difference': 0,
            'points': 0
        }

        for match in self.get_group_matches():
            if match.home_score is None or match.away_score is None:
                continue  # Match not played yet

            stats['played'] += 1
            is_home = match.home_team == self

            if is_home:
                gf, ga = match.home_score, match.away_score
            else:
                gf, ga = match.away_score, match.home_score

            stats['goals_for'] += gf
            stats['goals_against'] += ga

            if gf > ga:
                stats['wins'] += 1
                stats['points'] += 3
            elif gf == ga:
                stats['draws'] += 1
                stats['points'] += 1
            else:
                stats['losses'] += 1

        stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
        self._group_stats_cache = stats
        return stats

    def reset_matches(self):
        """Clear all match history and reset dynamic ranks."""
        self.matches = []
        self._group_stats_cache = None
        self.current_rank = self.fifa_rank
        self.current_off_rank = self.fifa_rank
        self.current_def_rank = self.fifa_rank

    def __repr__(self):
        return f"Team({self.name}, {self.confederation}, rank={self.fifa_rank})"
    
    def __eq__(self, other):
        if not isinstance(other, Team):
            return False
        return self.name == other.name
    
    def __hash__(self):
        return hash(self.name)


class Match:
    """Represents a single match in the tournament."""
    
    def __init__(self, number: int, city: Optional['HostCity'], stage: STAGE, 
                 group: Optional['Group'] = None, rng: Optional[random.Random] = None,
                 **kwargs):
        self.number = number
        self.city = city
        self.stage = stage
        self.group = group
        
        self.home_team: Optional[Team] = None
        self.away_team: Optional[Team] = None
        self.home_score: Optional[int] = None
        self.away_score: Optional[int] = None
        
        # Use provided RNG or create new one
        self._rng = rng if rng is not None else random.Random()

    def assign_teams(self, home_team: Team, away_team: Team):
        """Assign teams to this match."""
        self.home_team = home_team
        self.away_team = away_team
        home_team.add_match(self)
        away_team.add_match(self)

    def play(self) -> Tuple[int, int]:
        """
        Simulate the match and return (home_score, away_score).
        In knockout stages, ensures no draws.
        """
        self.home_score = self._rng.randint(0, 6)
        self.away_score = self._rng.randint(0, 6)

        if self.stage != STAGE.GROUP_STAGE:
            # No draws allowed in knockout stages
            while self.home_score == self.away_score:
                self.home_score = self._rng.randint(0, 6)
                self.away_score = self._rng.randint(0, 6)
        
        return self.home_score, self.away_score
    
    def get_winner(self) -> Optional[Team]:
        """Get the winner of this match (None for group stage draws)."""
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return self.home_team
        elif self.away_score > self.home_score:
            return self.away_team
        return None  # Draw
    
    def get_loser(self) -> Optional[Team]:
        """Get the loser of this match (None for group stage draws)."""
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score < self.away_score:
            return self.home_team
        elif self.away_score < self.home_score:
            return self.away_team
        return None  # Draw

    def __repr__(self):
        if self.home_team and self.away_team:
            if self.home_score is not None:
                return f"Match({self.home_team.name} {self.home_score} - {self.away_score} {self.away_team.name})"
            return f"Match({self.home_team.name} vs {self.away_team.name})"
        return f"Match(#{self.number}, {self.stage.value})"


class Group:
    """
    Represents a group in the group stage.
    Contains 4 teams and 6 matches (each team plays the other 3).
    """
    
    def __init__(self, name: str):
        self.name = name
        self.stage = STAGE.GROUP_STAGE
        self.teams: List[Team] = []
        self.matches: List[Match] = []

    def add_team(self, team: Team):
        """Add a team to this group."""
        if len(self.teams) >= 4:
            raise ValueError(f"Group {self.name} already has 4 teams")
        self.teams.append(team)
        team.assign_group(self)

    def add_match(self, match: Match):
        """Add a match to this group."""
        self.matches.append(match)

    def get_head_to_head_stats(self, teams: List[Team]) -> dict:
        """
        Calculate head-to-head statistics for a subset of teams.
        Used for tiebreaking when multiple teams have same points.
        """
        h2h_stats = {team: {'points': 0, 'gd': 0, 'gf': 0} for team in teams}
        
        for match in self.matches:
            if match.home_score is None:
                continue
            
            # Only consider matches between the tied teams
            if match.home_team in teams and match.away_team in teams:
                home, away = match.home_team, match.away_team
                home_gf, away_gf = match.home_score, match.away_score
                
                h2h_stats[home]['gf'] += home_gf
                h2h_stats[away]['gf'] += away_gf
                h2h_stats[home]['gd'] += home_gf - away_gf
                h2h_stats[away]['gd'] += away_gf - home_gf
                
                if home_gf > away_gf:
                    h2h_stats[home]['points'] += 3
                elif home_gf < away_gf:
                    h2h_stats[away]['points'] += 3
                else:
                    h2h_stats[home]['points'] += 1
                    h2h_stats[away]['points'] += 1
        
        return h2h_stats

    def get_standings(self) -> List[Team]:
        """
        Return teams sorted by group standings.
        
        Tiebreaker criteria (FIFA World Cup 2026):
        1. Points in head-to-head matches
        2. Goal difference in head-to-head matches
        3. Goals scored in head-to-head matches
        4. (If still tied, reapply 1-3 to remaining tied teams)
        5. Goal difference in all group matches
        6. Goals scored in all group matches
        7. FIFA World Ranking (skip fair play)
        """
        # Get overall stats for each team
        team_stats = [(team, team.get_group_stats()) for team in self.teams]
        
        # Initial sort by points, then GD, then GF
        team_stats.sort(key=lambda x: (
            x[1]['points'],
            x[1]['goal_difference'],
            x[1]['goals_for'],
            -x[0].fifa_rank  # Lower rank is better
        ), reverse=True)
        
        # Apply tiebreakers for teams with same points
        result = []
        i = 0
        while i < len(team_stats):
            # Find all teams with the same points
            same_points = [team_stats[i]]
            j = i + 1
            while j < len(team_stats) and team_stats[j][1]['points'] == team_stats[i][1]['points']:
                same_points.append(team_stats[j])
                j += 1
            
            if len(same_points) == 1:
                result.append(same_points[0][0])
            else:
                # Apply head-to-head tiebreakers
                tied_teams = [t[0] for t in same_points]
                sorted_tied = self._break_ties(tied_teams, same_points)
                result.extend(sorted_tied)
            
            i = j
        
        return result

    def _break_ties(self, tied_teams: List[Team], team_stats: List[Tuple[Team, dict]]) -> List[Team]:
        """Apply tiebreaker rules to sort tied teams.

        FIFA rules require recursive re-application: after h2h criteria
        separate some teams, the remaining subset must be re-evaluated
        using only their mutual h2h results.
        """
        if len(tied_teams) <= 1:
            return tied_teams

        h2h = self.get_head_to_head_stats(tied_teams)
        stats_map = {t[0]: t[1] for t in team_stats}

        def _sort_key(team):
            return (
                h2h[team]['points'],
                h2h[team]['gd'],
                h2h[team]['gf'],
                stats_map[team]['goal_difference'],
                stats_map[team]['goals_for'],
                -team.fifa_rank,
            )

        # Stable sort: alphabetical first, then by criteria descending
        teams_sorted = sorted(tied_teams, key=lambda t: t.name)
        teams_sorted = sorted(teams_sorted, key=_sort_key, reverse=True)

        # Recursively resolve sub-groups that remain tied
        result = []
        i = 0
        while i < len(teams_sorted):
            j = i + 1
            while j < len(teams_sorted) and _sort_key(teams_sorted[j]) == _sort_key(teams_sorted[i]):
                j += 1
            sub = teams_sorted[i:j]
            if len(sub) > 1 and len(sub) < len(tied_teams):
                # Re-evaluate with h2h among only this subset
                sub_stats = [(t, stats_map[t]) for t in sub]
                sub = self._break_ties(sub, sub_stats)
            result.extend(sub)
            i = j

        return result

    def __repr__(self):
        team_names = [t.name for t in self.teams]
        return f"Group({self.name}: {team_names})"
