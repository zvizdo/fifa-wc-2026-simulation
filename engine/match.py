import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.stats import poisson

from engine import Match


# Cache for the trained model (loaded once on first use)
_MODEL_CACHE = None


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
