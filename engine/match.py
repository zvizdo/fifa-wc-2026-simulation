import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.stats import poisson

from engine import Match, STAGE
from model.preprocessing import (
    STRONG_CONFEDS,
    calculate_rank_shift,
    calculate_off_rank_shift,
    calculate_def_rank_shift,
)


# Cache for the trained model (loaded once on first use)
_MODEL_CACHE = None
_EXPANDED_MODEL_CACHE = None


def _load_model():
    """Load the win expectation model from disk (cached)."""
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        # Add model directory to path for WinExpTransformer import
        model_dir = Path(__file__).parent.parent / "model"
        if str(model_dir) not in sys.path:
            sys.path.insert(0, str(model_dir))

        # Import WinExpTransformer and inject into __main__ namespace
        # (needed because pickle references __main__.WinExpTransformer)
        from win_exp_model_train import WinExpTransformer

        import __main__
        __main__.WinExpTransformer = WinExpTransformer

        model_path = model_dir / "win_exp_model.pkl"
        with open(model_path, "rb") as f:
            _MODEL_CACHE = pickle.load(f)

    return _MODEL_CACHE


def _load_expanded_model():
    """Load the expanded model from disk (cached)."""
    global _EXPANDED_MODEL_CACHE
    if _EXPANDED_MODEL_CACHE is None:
        model_path = Path(__file__).parent.parent / "model" / "expanded_model.pkl"
        with open(model_path, "rb") as f:
            _EXPANDED_MODEL_CACHE = pickle.load(f)
    return _EXPANDED_MODEL_CACHE


# Map engine STAGE enum to stage_weight matching training data
STAGE_WEIGHT_MAP = {
    STAGE.GROUP_STAGE: 0,
    STAGE.ROUND_OF_32: 1,
    STAGE.ROUND_OF_16: 1,
    STAGE.QUARTER_FINALS: 1,
    STAGE.THIRD_PLACE: 1,
    STAGE.SEMI_FINALS: 2,
    STAGE.FINAL: 2,
}


def dixon_coles_adjustment(home_goals, away_goals, lambda_home, lambda_away, rho=-0.1):
    """
    Apply Dixon-Coles adjustment to low-scoring probabilities.

    The adjustment corrects for correlation in low-scoring matches (0-0, 1-0, 0-1, 1-1).
    A negative rho increases the probability of draws, compensating for the known
    under-prediction of draws by independent Poisson models.

    Args:
        home_goals: Number of home team goals
        away_goals: Number of away team goals
        lambda_home: Expected goals for home team
        lambda_away: Expected goals for away team
        rho: Correlation parameter (typically ~ -0.1, must be negative to inflate draws)

    Returns:
        Adjustment factor to multiply with Poisson probability (floored at 0.0001)
    """
    if home_goals == 0 and away_goals == 0:
        res = 1 - lambda_home * lambda_away * rho
    elif home_goals == 0 and away_goals == 1:
        res = 1 + lambda_home * rho
    elif home_goals == 1 and away_goals == 0:
        res = 1 + lambda_away * rho
    elif home_goals == 1 and away_goals == 1:
        res = 1 - rho
    else:
        return 1.0
    return max(0.0001, res)


class RankMatch(Match):
    def play(self):
        self.home_score = (
            1 if self.home_team.fifa_rank < self.away_team.fifa_rank else 0
        )
        self.away_score = (
            1 if self.away_team.fifa_rank < self.home_team.fifa_rank else 0
        )

        return self.home_score, self.away_score


class WinExpMatch(Match):
    """Match simulation using the win expectation Poisson regression model."""

    def __init__(self, *args, rho=-0.1, **kwargs):
        """
        Initialize WinExpMatch.

        Args:
            rho: Dixon-Coles correlation parameter (default: -0.1)
        """
        super().__init__(*args, **kwargs)
        self.rho = rho

    def play(self):
        """
        Simulate the match using the win expectation model.

        Returns:
            Tuple[int, int]: (home_score, away_score)
        """
        # Load model (cached after first load)
        model = _load_model()

        # Prepare features for both teams
        home_features = np.array([[self.home_team.fifa_rank, self.away_team.fifa_rank]])
        away_features = np.array([[self.away_team.fifa_rank, self.home_team.fifa_rank]])

        # Predict expected goals (lambda parameters)
        lambda_home = model.predict(home_features)[0]
        lambda_away = model.predict(away_features)[0]

        # Create probability matrix for scores 0-6
        max_goals = 7
        prob_matrix = np.zeros((max_goals, max_goals))

        for home_goals in range(max_goals):
            for away_goals in range(max_goals):
                # Base Poisson probability
                prob = poisson.pmf(home_goals, lambda_home) * poisson.pmf(away_goals, lambda_away)

                # Apply Dixon-Coles adjustment
                adjustment = dixon_coles_adjustment(
                    home_goals, away_goals, lambda_home, lambda_away, self.rho
                )
                prob_matrix[home_goals, away_goals] = prob * adjustment

        # Normalize probabilities
        prob_matrix = prob_matrix / prob_matrix.sum()

        # Sample a score from the probability distribution using cumulative sum method
        # This works with any RNG type (random.Random, SecureRandom, etc.)
        flat_probs = prob_matrix.flatten()
        cumsum = np.cumsum(flat_probs)
        rand_val = self._rng.random()
        sampled_index = np.searchsorted(cumsum, rand_val)

        # Convert flat index back to (home_goals, away_goals)
        self.home_score = sampled_index // max_goals
        self.away_score = sampled_index % max_goals

        # Handle knockout stage draws (50-50 random winner)
        if self.stage != self.stage.GROUP_STAGE and self.home_score == self.away_score:
            if self._rng.random() < 0.5:
                self.home_score += 1
            else:
                self.away_score += 1

        return self.home_score, self.away_score


class ModeledMatch(Match):
    """Match simulation using the expanded Poisson regression model.

    Uses the full feature set (15 features) matching model/train.py's
    FEATURE_COLUMNS order. Tracks and updates dynamic ranks (cur_rank,
    off_rank, def_rank) on Team objects after each match, mirroring the
    logic in model/preprocessing.process_tournament_history.
    """

    def __init__(self, *args, rho=-0.1, **kwargs):
        super().__init__(*args, **kwargs)
        self.rho = rho

    def _build_feature_row(self, team, opponent):
        """Build the 15-element feature vector for one team perspective.

        Column order must match model/train.py FEATURE_COLUMNS:
            rank, opp_rank, cur_rank, opp_cur_rank,
            rank_shift, opp_rank_shift,
            off_rank, opp_off_rank, def_rank, opp_def_rank,
            host, is_strong_confed, opp_is_strong_confed,
            rest_diff, stage_weight
        """
        rank = float(team.fifa_rank)
        opp_rank = float(opponent.fifa_rank)
        cur_rank = float(team.current_rank)
        opp_cur_rank = float(opponent.current_rank)
        rank_shift = cur_rank - rank
        opp_rank_shift = opp_cur_rank - opp_rank
        off_rank = float(team.current_off_rank)
        opp_off_rank = float(opponent.current_off_rank)
        def_rank = float(team.current_def_rank)
        opp_def_rank = float(opponent.current_def_rank)
        host = float(team.host)
        is_strong_confed = 1.0 if team.confederation in STRONG_CONFEDS else 0.0
        opp_is_strong_confed = 1.0 if opponent.confederation in STRONG_CONFEDS else 0.0
        rest_diff = 0.0
        stage_weight = float(STAGE_WEIGHT_MAP.get(self.stage, 1))

        return np.array([[
            rank, opp_rank,
            cur_rank, opp_cur_rank,
            rank_shift, opp_rank_shift,
            off_rank, opp_off_rank,
            def_rank, opp_def_rank,
            host,
            is_strong_confed, opp_is_strong_confed,
            rest_diff,
            stage_weight,
        ]])

    def _update_ranks(self, team, opp_cur_rank_snapshot, goals_scored,
                      goals_conceded, result):
        """Update dynamic ranks on team after match, matching preprocessing logic.

        Uses the opponent's current_rank snapshot taken before any updates,
        matching how process_tournament_history records kickoff values first.
        """
        artifact = _load_expanded_model()
        pp = artifact["preprocess_params"]

        # General rank shift
        gen_shift = calculate_rank_shift(
            team.current_rank, opp_cur_rank_snapshot,
            result, shape=pp["shape"], k_mul=pp["k_mul"],
        )
        team.current_rank = max(1.0, round(team.current_rank + gen_shift, 1))

        # Offensive rank shift (uses opponent's current general rank at kickoff)
        off_shift = calculate_off_rank_shift(
            team.current_off_rank, opp_cur_rank_snapshot,
            goals_scored, shape=pp["shape"],
            k_off_mul=pp["k_off_mul"], goal_cap=pp["goal_cap"],
        )
        team.current_off_rank = max(1.0, round(team.current_off_rank + off_shift, 1))

        # Defensive rank shift (uses opponent's current general rank at kickoff)
        def_shift = calculate_def_rank_shift(
            team.current_def_rank, opp_cur_rank_snapshot,
            goals_conceded, shape=pp["shape"],
            k_def_mul=pp["k_def_mul"], goal_cap=pp["goal_cap"],
        )
        team.current_def_rank = max(1.0, round(team.current_def_rank + def_shift, 1))

    def play(self):
        """Simulate the match using the expanded model.

        Returns:
            Tuple[int, int]: (home_score, away_score)
        """
        artifact = _load_expanded_model()
        pipeline = artifact["pipeline"]

        # Build feature vectors for each team perspective
        home_features = self._build_feature_row(self.home_team, self.away_team)
        away_features = self._build_feature_row(self.away_team, self.home_team)

        # Predict expected goals
        lambda_home = pipeline.predict(home_features)[0]
        lambda_away = pipeline.predict(away_features)[0]

        # Build Dixon-Coles probability matrix (scores 0-6)
        max_goals = 7
        prob_matrix = np.zeros((max_goals, max_goals))

        for hg in range(max_goals):
            for ag in range(max_goals):
                prob = (poisson.pmf(hg, lambda_home)
                        * poisson.pmf(ag, lambda_away))
                adj = dixon_coles_adjustment(
                    hg, ag, lambda_home, lambda_away, self.rho
                )
                prob_matrix[hg, ag] = prob * adj

        # Normalize and sample
        prob_matrix /= prob_matrix.sum()
        flat_probs = prob_matrix.flatten()
        cumsum = np.cumsum(flat_probs)
        rand_val = self._rng.random()
        sampled_index = np.searchsorted(cumsum, rand_val)

        self.home_score = sampled_index // max_goals
        self.away_score = sampled_index % max_goals

        # Handle knockout stage draws
        if self.stage != STAGE.GROUP_STAGE and self.home_score == self.away_score:
            if self._rng.random() < 0.5:
                self.home_score += 1
            else:
                self.away_score += 1

        # Update dynamic ranks for both teams
        # Snapshot opponent ranks at kickoff before any updates
        home_opp_cur_rank = self.away_team.current_rank
        away_opp_cur_rank = self.home_team.current_rank

        home_result = (1.0 if self.home_score > self.away_score
                       else 0.0 if self.home_score < self.away_score
                       else 0.5)
        away_result = 1.0 - home_result

        self._update_ranks(
            self.home_team, home_opp_cur_rank,
            goals_scored=self.home_score,
            goals_conceded=self.away_score,
            result=home_result,
        )
        self._update_ranks(
            self.away_team, away_opp_cur_rank,
            goals_scored=self.away_score,
            goals_conceded=self.home_score,
            result=away_result,
        )

        return self.home_score, self.away_score
