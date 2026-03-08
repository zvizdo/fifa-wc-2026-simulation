"""
FIFA World Cup 2026 Competition Simulation.
Updated to use exact bracket structure and venue assignments per FIFA.
"""
import json
from typing import Dict, List, Optional, Tuple, Type

import duckdb

from .utils import SecureRandom
from .core import STAGE, Team, Match, Group
from .venues import HOST_CITIES, HostCity, get_city_by_name
from .schedule import (
    GROUP_STAGE_SCHEDULE,
    ROUND_OF_32_BRACKET,
    ROUND_OF_16_BRACKET,
    QUARTER_FINALS_BRACKET,
    SEMI_FINALS_BRACKET,
    THIRD_PLACE_MATCH,
    FINAL_MATCH,
    THIRD_PLACE_POOLS,
    VENUE_MAP,
)


class Competition:
    """
    Main class for simulating the FIFA World Cup 2026.
    
    Tournament structure:
    - 48 teams in 12 groups (A-L), 4 teams per group
    - Group stage: Each team plays 3 matches
    - Top 2 from each group + 8 best third-placed teams advance (32 total)
    - Knockout: Round of 32 → Round of 16 → Quarter-finals → Semi-finals → Final
    
    This implementation uses the EXACT FIFA bracket structure and venue assignments.
    """
    
    def __init__(self, teams_data: Optional[Dict] = None, random_seed: Optional[int] = None,
                 match_class: Optional[Type[Match]] = None,
                 match_kwargs: Optional[Dict] = None):
        """
        Initialize the competition.
        
        Args:
            teams_data: Dictionary with group assignments, or None to load default.
            random_seed: Seed for reproducible simulations (None = secure random).
            match_class: Optional custom Match class (e.g., PredictedMatch). Must have
                         same interface as Match: __init__(number, city, stage, group, rng),
                         assign_teams(), play(), get_winner(), get_loser().
            match_kwargs: Optional dict of extra kwargs passed to every match constructor.
        """
        self.random_seed = random_seed
        self._rng = SecureRandom(random_seed)
        
        # Store the match class to use (default: Match from core)
        self._match_class = match_class if match_class is not None else Match
        self._match_kwargs = match_kwargs or {}
        
        self.groups: Dict[str, Group] = {}
        self.teams: List[Team] = []
        self.all_matches: List[Match] = []
        self.matches_by_number: Dict[int, Match] = {}  # Lookup by match number
        self.match_counter = 0
        
        # Knockout stage results
        self.third_place_teams: List[Team] = []  # All third-place teams ranked
        self.advancing_third_place: List[Team] = []  # Best 8 third-place teams
        self.advancing_third_groups: set = set()  # Groups whose 3rd place advanced
        self.knockout_matches: Dict[STAGE, List[Match]] = {
            STAGE.ROUND_OF_32: [],
            STAGE.ROUND_OF_16: [],
            STAGE.QUARTER_FINALS: [],
            STAGE.SEMI_FINALS: [],
            STAGE.THIRD_PLACE: [],
            STAGE.FINAL: [],
        }
        
        self.champion: Optional[Team] = None
        self.runner_up: Optional[Team] = None
        self.third_place: Optional[Team] = None
        self._cached_standings: Optional[Dict[str, List[Team]]] = None
        
        if teams_data:
            self._setup_from_data(teams_data)
    
    @classmethod
    def from_json_file(cls, filepath: str, random_seed: Optional[int] = None,
                       match_class: Optional[Type[Match]] = None,
                       match_kwargs: Optional[Dict] = None) -> 'Competition':
        """Load competition from a JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(teams_data=data, random_seed=random_seed, match_class=match_class,
                   match_kwargs=match_kwargs)
    
    def _setup_from_data(self, data: Dict):
        """Set up groups and teams from data dictionary."""
        groups_data = data.get('groups', data)
        
        for group_name, team_list in groups_data.items():
            group = Group(group_name)
            self.groups[group_name] = group
            
            for team_data in team_list:
                team = Team(
                    name=team_data['name'],
                    confederation=team_data['confederation'],
                    fifa_rank=team_data['fifa_rank'],
                    host=team_data.get('host', False)
                )
                group.add_team(team)
                self.teams.append(team)
    
    def _get_venue(self, city_name: str) -> HostCity:
        """Get HostCity object for a city name."""
        if city_name in VENUE_MAP:
            return VENUE_MAP[city_name]
        
        # If venue is unknown, pick a deterministic fallback instead of pulling 
        # from the global random stream to prevent bracket-butterfly effects.
        fallback_idx = sum(ord(c) for c in city_name) % len(HOST_CITIES)
        return get_city_by_name(city_name) or HOST_CITIES[fallback_idx]
    
    def _create_match(self, match_number: int, stage: STAGE, 
                      city: Optional[HostCity] = None,
                      group: Optional[Group] = None) -> Match:
        """Create a new match with specific match number using the configured match class."""
        # Create an isolated RNG for this specific match based on the competition seed
        # This prevents the order of events or tiebreakers in earlier matches from 
        # shifting the global random stream and artificially changing unrelated matches
        if self.random_seed is not None:
            match_seed = self.random_seed + (match_number * 10000)
            match_rng = SecureRandom(match_seed)
        else:
            match_rng = self._rng
            
        match = self._match_class(
            number=match_number,
            city=city,
            stage=stage,
            group=group,
            rng=match_rng,
            **self._match_kwargs
        )
        self.all_matches.append(match)
        self.matches_by_number[match_number] = match
        return match
    
    def setup_group_matches(self):
        """
        Create all group stage matches.
        
        For full competitions (12 groups), uses the EXACT FIFA schedule with proper venues.
        For partial competitions (testing), uses simple round-robin scheduling.
        """
        # Check if this is a full 12-group competition
        expected_groups = set('ABCDEFGHIJKL')
        actual_groups = set(self.groups.keys())
        
        if actual_groups == expected_groups:
            # Use exact FIFA schedule
            self._setup_group_matches_exact()
        else:
            # Use simple round-robin for partial competitions (testing)
            self._setup_group_matches_simple()
    
    def _setup_group_matches_exact(self):
        """Set up matches using exact FIFA schedule for full 12-group competition."""
        for match_num, (group_name, match_day, city_name, home_pos, away_pos) in GROUP_STAGE_SCHEDULE.items():
            group = self.groups[group_name]
            city = self._get_venue(city_name)
            
            # Get teams by seeding position (1-4)
            teams = group.teams
            home_team = teams[home_pos - 1]
            away_team = teams[away_pos - 1]
            
            match = self._create_match(match_num, STAGE.GROUP_STAGE, city, group)
            match.assign_teams(home_team, away_team)
            group.add_match(match)
        
        self.match_counter = 72  # Group stage complete
    
    def _setup_group_matches_simple(self):
        """Simple round-robin setup for partial competitions (testing)."""
        for group in self.groups.values():
            teams = group.teams
            # Each team plays the other 3: 6 matches per group
            matchups = []
            for i in range(len(teams)):
                for j in range(i + 1, len(teams)):
                    matchups.append((teams[i], teams[j]))
            
            for home, away in matchups:
                self.match_counter += 1
                city = self._rng.choice(HOST_CITIES)
                match = self._create_match(self.match_counter, STAGE.GROUP_STAGE, city, group)
                match.assign_teams(home, away)
                group.add_match(match)
    
    def play_group_stage(self):
        """Play all group stage matches."""
        for group in self.groups.values():
            for match in group.matches:
                match.play()
    
    def get_group_standings(self) -> Dict[str, List[Team]]:
        """Get standings for all groups (cached after first call)."""
        if self._cached_standings is not None:
            return self._cached_standings
        standings = {name: group.get_standings() for name, group in self.groups.items()}
        self._cached_standings = standings
        return standings
    
    def rank_third_place_teams(self) -> List[Team]:
        """
        Rank all third-place teams across groups.
        
        Criteria:
        1. Points
        2. Goal difference
        3. Goals scored
        4. FIFA ranking (skipping fair play)
        """
        standings = self.get_group_standings()
        third_place = []
        
        for group_name, teams in standings.items():
            if len(teams) >= 3:
                third_team = teams[2]  # Index 2 = third place
                stats = third_team.get_group_stats()
                third_place.append((third_team, stats, group_name))
        
        # Sort by ranking criteria
        third_place.sort(key=lambda x: (
            x[1]['points'],
            x[1]['goal_difference'],
            x[1]['goals_for'],
            -x[0].fifa_rank  # Lower rank is better
        ), reverse=True)
        
        self.third_place_teams = [t[0] for t in third_place]
        self.advancing_third_place = self.third_place_teams[:8]  # Best 8 advance
        self.advancing_third_groups = {t.group.name for t in self.advancing_third_place}
        
        return self.third_place_teams
    
    def _get_third_place_for_match(self, match_number: int) -> Team:
        """
        Get which third-place team plays in a specific R32 match.
        Uses the FIFA pool system.
        """
        if match_number not in THIRD_PLACE_POOLS:
            raise ValueError(f"Match {match_number} does not involve a 3rd place team")
        
        pool = THIRD_PLACE_POOLS[match_number]
        candidates = pool & self.advancing_third_groups
        
        if not candidates:
            # Fallback to any available 3rd place team
            available = {t.group.name for t in self.advancing_third_place 
                        if not any(m.away_team == t or m.home_team == t 
                                  for m in self.knockout_matches[STAGE.ROUND_OF_32])}
            candidates = available
        
        # Use priority order (FIFA rules prefer certain groups)
        priority_order = list('ABCDEFGHIJKL')
        for group in priority_order:
            if group in candidates:
                # Find the team from this group
                for team in self.advancing_third_place:
                    if team.group.name == group:
                        return team
        
        # Ultimate fallback
        return self.advancing_third_place[0]
    
    def _get_team_from_source(self, source: str, standings: Dict[str, List[Team]]) -> Optional[Team]:
        """
        Get a team from a source string like "1A" (winner group A) or "2B" (runner-up B).
        """
        if len(source) >= 2:
            pos = source[0]
            group = source[1]
            
            if pos == '1':
                return standings[group][0]  # Winner
            elif pos == '2':
                return standings[group][1]  # Runner-up
            elif pos == '3':
                # Third place - handled by pool system
                return None
        return None
    
    def build_round_of_32(self) -> List[Match]:
        """
        Build the EXACT Round of 32 bracket per FIFA rules.
        Uses the official pairings and venues.
        """
        standings = self.get_group_standings()
        matches = []
        used_third_place = set()  # Track which groups' 3rd place teams are used
        
        # Build matches 73-88 following exact FIFA bracket
        for match_num in sorted(ROUND_OF_32_BRACKET.keys()):
            city_name, pairing_type, source1, source2 = ROUND_OF_32_BRACKET[match_num]
            city = self._get_venue(city_name)
            
            match = self._create_match(match_num, STAGE.ROUND_OF_32, city)
            
            if pairing_type == "2v2":
                # Runner-up vs Runner-up
                team1 = self._get_team_from_source(source1, standings)
                team2 = self._get_team_from_source(source2, standings)
            elif pairing_type == "1v2":
                # Winner vs Runner-up
                team1 = self._get_team_from_source(source1, standings)
                team2 = self._get_team_from_source(source2, standings)
            elif pairing_type == "1v3":
                # Winner vs 3rd place (from pool)
                team1 = self._get_team_from_source(source1, standings)
                team2 = self._get_third_place_for_match_with_tracking(match_num, used_third_place)
            else:
                raise ValueError(f"Unknown pairing type: {pairing_type}")
            
            match.assign_teams(team1, team2)
            matches.append(match)
        
        self.knockout_matches[STAGE.ROUND_OF_32] = matches
        self.match_counter = 88
        return matches
    
    def _get_third_place_for_match_with_tracking(self, match_number: int, 
                                                   used_groups: set) -> Team:
        """Get third-place team for a match, tracking which are already used."""
        if match_number not in THIRD_PLACE_POOLS:
            raise ValueError(f"Match {match_number} does not involve a 3rd place team")
        
        pool = THIRD_PLACE_POOLS[match_number]
        
        # Available candidates: in the pool, qualified, and not yet assigned
        candidates = pool & self.advancing_third_groups - used_groups
        
        if not candidates:
            # Widen search if pool is exhausted
            candidates = self.advancing_third_groups - used_groups
        
        if not candidates:
            raise ValueError(f"No available 3rd place team for match {match_number}")
        
        # Use priority order
        for group in 'ABCDEFGHIJKL':
            if group in candidates:
                used_groups.add(group)
                for team in self.advancing_third_place:
                    if team.group.name == group:
                        return team
        
        raise ValueError(f"Could not find team for match {match_number}")
    
    def play_knockout_round(self, stage: STAGE) -> List[Team]:
        """Play all matches in a knockout round and return winners."""
        matches = self.knockout_matches[stage]
        winners = []
        
        for match in matches:
            match.play()
            winners.append(match.get_winner())
        
        return winners
    
    def build_round_of_16(self):
        """Build Round of 16 using exact FIFA bracket and venues."""
        matches = []
        
        for match_num, (city_name, m1, m2) in ROUND_OF_16_BRACKET.items():
            city = self._get_venue(city_name)
            match = self._create_match(match_num, STAGE.ROUND_OF_16, city)
            
            # Get winners from R32 matches
            team1 = self.matches_by_number[m1].get_winner()
            team2 = self.matches_by_number[m2].get_winner()
            
            match.assign_teams(team1, team2)
            matches.append(match)
        
        self.knockout_matches[STAGE.ROUND_OF_16] = matches
        self.match_counter = 96
    
    def build_quarter_finals(self):
        """Build quarter-finals using exact FIFA bracket and venues."""
        matches = []
        
        for match_num, (city_name, m1, m2) in QUARTER_FINALS_BRACKET.items():
            city = self._get_venue(city_name)
            match = self._create_match(match_num, STAGE.QUARTER_FINALS, city)
            
            team1 = self.matches_by_number[m1].get_winner()
            team2 = self.matches_by_number[m2].get_winner()
            
            match.assign_teams(team1, team2)
            matches.append(match)
        
        self.knockout_matches[STAGE.QUARTER_FINALS] = matches
        self.match_counter = 100
    
    def build_semi_finals(self):
        """Build semi-finals using exact FIFA bracket and venues."""
        matches = []
        
        for match_num, (city_name, m1, m2) in SEMI_FINALS_BRACKET.items():
            city = self._get_venue(city_name)
            match = self._create_match(match_num, STAGE.SEMI_FINALS, city)
            
            team1 = self.matches_by_number[m1].get_winner()
            team2 = self.matches_by_number[m2].get_winner()
            
            match.assign_teams(team1, team2)
            matches.append(match)
        
        self.knockout_matches[STAGE.SEMI_FINALS] = matches
        self.match_counter = 102
    
    def run_knockout_stage(self):
        """Run the entire knockout stage with exact FIFA bracket."""
        # Round of 32
        self.build_round_of_32()
        self.play_knockout_round(STAGE.ROUND_OF_32)
        
        # Round of 16
        self.build_round_of_16()
        self.play_knockout_round(STAGE.ROUND_OF_16)
        
        # Quarter-finals
        self.build_quarter_finals()
        self.play_knockout_round(STAGE.QUARTER_FINALS)
        
        # Semi-finals
        self.build_semi_finals()
        semi_winners = self.play_knockout_round(STAGE.SEMI_FINALS)
        
        # Get semi-final losers for third-place playoff
        semi_matches = self.knockout_matches[STAGE.SEMI_FINALS]
        semi_losers = [m.get_loser() for m in semi_matches]
        
        # Third-place playoff (Match 103)
        match_num, city_name = THIRD_PLACE_MATCH
        city = self._get_venue(city_name)
        third_match = self._create_match(match_num, STAGE.THIRD_PLACE, city)
        third_match.assign_teams(semi_losers[0], semi_losers[1])
        self.knockout_matches[STAGE.THIRD_PLACE] = [third_match]
        third_match.play()
        self.third_place = third_match.get_winner()
        
        # Final (Match 104)
        match_num, city_name = FINAL_MATCH
        city = self._get_venue(city_name)
        final_match = self._create_match(match_num, STAGE.FINAL, city)
        final_match.assign_teams(semi_winners[0], semi_winners[1])
        self.knockout_matches[STAGE.FINAL] = [final_match]
        final_match.play()
        self.champion = final_match.get_winner()
        self.runner_up = final_match.get_loser()
    
    def simulate(self) -> Team:
        """
        Run the complete tournament simulation.
        
        Returns:
            The tournament champion.
        """
        # Set up and play group stage
        self.setup_group_matches()
        self.play_group_stage()
        
        # Rank third-place teams
        self.rank_third_place_teams()
        
        # Run knockout stage
        self.run_knockout_stage()
        
        return self.champion
    
    def reset(self, new_seed: Optional[int] = None):
        """Reset the competition for a new simulation."""
        if new_seed is not None:
            self.random_seed = new_seed
        self._rng = SecureRandom(self.random_seed)
        
        # Reset teams
        for team in self.teams:
            team.reset_matches()
        
        # Clear groups' matches
        for group in self.groups.values():
            group.matches = []
        
        # Clear knockout data
        self.all_matches = []
        self.matches_by_number = {}
        self.match_counter = 0
        self.third_place_teams = []
        self.advancing_third_place = []
        self.advancing_third_groups = set()
        self.knockout_matches = {stage: [] for stage in self.knockout_matches}
        self.champion = None
        self.runner_up = None
        self.third_place = None
        self._cached_standings = None
    
    def get_final_standings(self) -> Dict:
        """Get the final tournament standings."""
        return {
            'champion': self.champion,
            'runner_up': self.runner_up,
            'third_place': self.third_place,
            'fourth_place': self.knockout_matches[STAGE.THIRD_PLACE][0].get_loser() if self.knockout_matches[STAGE.THIRD_PLACE] else None,
        }
    
    def print_results(self):
        """Print tournament results summary."""
        print("=" * 50)
        print("FIFA WORLD CUP 2026 RESULTS")
        print("=" * 50)
        
        # Group standings
        print("\nGROUP STAGE STANDINGS:")
        print("-" * 40)
        standings = self.get_group_standings()
        for group_name in sorted(standings.keys()):
            print(f"\nGroup {group_name}:")
            for i, team in enumerate(standings[group_name], 1):
                stats = team.get_group_stats()
                print(f"  {i}. {team.name:20s} Pts:{stats['points']:2d} GD:{stats['goal_difference']:+3d}")
        
        # Third place ranking
        print("\n" + "-" * 40)
        print("THIRD-PLACE RANKING (Top 8 advance):")
        for i, team in enumerate(self.third_place_teams, 1):
            stats = team.get_group_stats()
            advancing = "✓" if team in self.advancing_third_place else " "
            print(f"  {i:2d}. [{advancing}] {team.name:20s} Pts:{stats['points']:2d} GD:{stats['goal_difference']:+3d}")
        
        # Final results
        print("\n" + "=" * 50)
        print("FINAL STANDINGS:")
        print(f"  🥇 CHAMPION: {self.champion.name if self.champion else 'TBD'}")
        print(f"  🥈 Runner-up: {self.runner_up.name if self.runner_up else 'TBD'}")
        print(f"  🥉 Third Place: {self.third_place.name if self.third_place else 'TBD'}")
        print("=" * 50)
        
        # Show Final venue
        if self.knockout_matches[STAGE.FINAL]:
            final = self.knockout_matches[STAGE.FINAL][0]
            if final.city:
                print(f"\n  Final played at: {final.city.stadium}, {final.city.name}")

    # ── DuckDB export ───────────────────────────────────────────────────

    @staticmethod
    def init_db(db_path: str) -> duckdb.DuckDBPyConnection:
        """
        Create (or open) a DuckDB database and ensure all tables exist.

        Tables created:
          - matches:           every match with scores, venue, stage info
          - group_standings:   final group-stage table for each team
          - third_place_ranks: ranked list of all 3rd-placed teams

        Call this once before running batches of simulations.
        """
        con = duckdb.connect(db_path)

        con.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                sim_id           VARCHAR NOT NULL,
                match_number     INTEGER NOT NULL,
                stage            VARCHAR NOT NULL,
                group_name       VARCHAR,
                home_team        VARCHAR NOT NULL,
                away_team        VARCHAR NOT NULL,
                home_score       INTEGER,
                away_score       INTEGER,
                winner           VARCHAR,
                city             VARCHAR,
                stadium          VARCHAR,
                country          VARCHAR,
                PRIMARY KEY (sim_id, match_number)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS group_standings (
                sim_id           VARCHAR NOT NULL,
                group_name       VARCHAR NOT NULL,
                position         INTEGER NOT NULL,
                team             VARCHAR NOT NULL,
                confederation    VARCHAR NOT NULL,
                fifa_rank        INTEGER NOT NULL,
                played           INTEGER NOT NULL,
                wins             INTEGER NOT NULL,
                draws            INTEGER NOT NULL,
                losses           INTEGER NOT NULL,
                goals_for        INTEGER NOT NULL,
                goals_against    INTEGER NOT NULL,
                goal_difference  INTEGER NOT NULL,
                points           INTEGER NOT NULL,
                advanced         BOOLEAN NOT NULL,
                PRIMARY KEY (sim_id, group_name, position)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS third_place_ranks (
                sim_id           VARCHAR NOT NULL,
                rank             INTEGER NOT NULL,
                team             VARCHAR NOT NULL,
                group_name       VARCHAR NOT NULL,
                points           INTEGER NOT NULL,
                goal_difference  INTEGER NOT NULL,
                goals_for        INTEGER NOT NULL,
                advanced         BOOLEAN NOT NULL,
                PRIMARY KEY (sim_id, rank)
            )
        """)

        con.close()
        return duckdb.connect(db_path)

    def extract_rows(self, sim_id: str) -> Tuple[list, list, list]:
        """
        Extract all simulation results as plain tuples (no DB connection needed).

        Returns:
            (match_rows, standing_rows, third_place_rows) ready for batch insert.
        """
        match_rows = []
        for m in self.all_matches:
            winner = m.get_winner()
            match_rows.append((
                sim_id,
                m.number,
                m.stage.value,
                m.group.name if m.group else None,
                m.home_team.name,
                m.away_team.name,
                int(m.home_score) if m.home_score is not None else None,
                int(m.away_score) if m.away_score is not None else None,
                winner.name if winner else None,
                m.city.name if m.city else None,
                m.city.stadium if m.city else None,
                m.city.country if m.city else None,
            ))

        standings = self.get_group_standings()
        advancing_teams = {t.name for t in self.advancing_third_place}
        standing_rows = []
        for group_name in sorted(standings):
            for pos, team in enumerate(standings[group_name], 1):
                stats = team.get_group_stats()
                advanced = pos <= 2 or team.name in advancing_teams
                standing_rows.append((
                    sim_id,
                    group_name,
                    pos,
                    team.name,
                    team.confederation,
                    int(team.fifa_rank),
                    int(stats['played']),
                    int(stats['wins']),
                    int(stats['draws']),
                    int(stats['losses']),
                    int(stats['goals_for']),
                    int(stats['goals_against']),
                    int(stats['goal_difference']),
                    int(stats['points']),
                    advanced,
                ))

        third_rows = []
        for rank, team in enumerate(self.third_place_teams, 1):
            stats = team.get_group_stats()
            third_rows.append((
                sim_id,
                rank,
                team.name,
                team.group.name,
                int(stats['points']),
                int(stats['goal_difference']),
                int(stats['goals_for']),
                team in self.advancing_third_place,
            ))

        return match_rows, standing_rows, third_rows

    def dump_to_db(self, con: duckdb.DuckDBPyConnection, sim_id: str) -> None:
        """
        Write this simulation's results into the open DuckDB connection.

        Args:
            con: An open DuckDB connection (from ``init_db``).
            sim_id: Unique string identifier for this simulation run.
        """
        match_rows, standing_rows, third_rows = self.extract_rows(sim_id)
        con.executemany(
            "INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            match_rows,
        )
        con.executemany(
            "INSERT INTO group_standings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            standing_rows,
        )
        con.executemany(
            "INSERT INTO third_place_ranks VALUES (?,?,?,?,?,?,?,?)",
            third_rows,
        )

    @staticmethod
    def insert_rows(con: duckdb.DuckDBPyConnection,
                    match_rows: list, standing_rows: list, third_rows: list) -> None:
        """Batch-insert pre-extracted rows into the database."""
        con.executemany(
            "INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            match_rows,
        )
        con.executemany(
            "INSERT INTO group_standings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            standing_rows,
        )
        con.executemany(
            "INSERT INTO third_place_ranks VALUES (?,?,?,?,?,?,?,?)",
            third_rows,
        )

    @staticmethod
    def create_db_indexes(con: duckdb.DuckDBPyConnection) -> None:
        """
        Create indexes for fast UI queries.

        Call this **once** after all simulations have been written,
        so bulk inserts aren't slowed down by index maintenance.
        """
        con.execute("CREATE INDEX IF NOT EXISTS idx_matches_sim        ON matches (sim_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_matches_stage      ON matches (stage)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_matches_team_home  ON matches (home_team)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_matches_team_away  ON matches (away_team)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_matches_winner     ON matches (winner)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_standings_sim      ON group_standings (sim_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_standings_team     ON group_standings (team)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_third_sim          ON third_place_ranks (sim_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_third_team         ON third_place_ranks (team)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_matches_city       ON matches (city)")