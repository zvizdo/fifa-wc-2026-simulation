"""Sklearn-compatible transformers for FIFA World Cup model features."""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class WinExpTransformer(BaseEstimator, TransformerMixin):
    """Baseline transformer: (rank, opp_rank) -> win_exp.

    Input:  X[:, 0] = rank, X[:, 1] = opp_rank
    Output: single column win_exp = 1 / (1 + (rank / opp_rank) ** shape)
    """

    def __init__(self, shape=0.625, host_discount=0.0):
        self.shape = shape
        self.host_discount = host_discount

    def fit(self, X, y=None):
        return self

    def _effective_rank(self, rank, is_host):
        return rank * (1.0 - self.host_discount * is_host)

    def transform(self, X):
        rank = X[:, 0]
        opp_rank = X[:, 1]

        # If we only have 2 columns, it's the baseline — no host advantage.
        if X.shape[1] > 2:
            host = X[:, 2]
            opp_host = X[:, 3]
            rank = self._effective_rank(rank, host)
            opp_rank = self._effective_rank(opp_rank, opp_host)

        win_exp = 1.0 / (1.0 + (rank / opp_rank) ** self.shape)
        return win_exp.reshape(-1, 1)


class FullFeatureTransformer(BaseEstimator, TransformerMixin):
    """Transform preprocessed feature matrix into model-ready features.

    Computes win-expectation variants from rank pairs and passes through
    auxiliary features. Feature flags allow incremental testing.

    Host advantage is modeled as a percentage rank discount:
        eff_rank = rank * (1 - host_discount * is_host)
    This is already nonlinear through the win_exp power formula:
        win_exp = 1 / (1 + (eff_rank / opp_eff_rank) ^ shape)
    The effect is largest for evenly-matched teams (where home crowd
    matters most) and negligible for mismatches.

    Input columns (indices into X):
        0: rank               4: rank_shift        8: def_rank             12: is_strong_confed
        1: opp_rank           5: opp_rank_shift    9: opp_def_rank         13: opp_is_strong_confed
        2: cur_rank           6: off_rank         10: host                 14: stage_weight
        3: opp_cur_rank       7: opp_off_rank     11: opp_host

    Output columns:
        - win_exp:            1/(1+(eff_rank/eff_opp_rank)^shape)
        - cur_win_exp:        1/(1+(eff_cur_rank/eff_opp_cur_rank)^shape)
        - rank_shift:         passthrough  [if include_rank_shift]
        - opp_rank_shift:     passthrough  [if include_rank_shift]
        - off_win_exp:        1/(1+(eff_off_rank/eff_opp_def_rank)^shape)  [if include_off_win_exp]
        - stage_weight:       passthrough [if include_stage_weight]
                              0=group stage, 1=R16/QF/3rd-place, 2=SF/final
    """

    # Column index constants
    RANK = 0
    OPP_RANK = 1
    CUR_RANK = 2
    OPP_CUR_RANK = 3
    RANK_SHIFT = 4
    OPP_RANK_SHIFT = 5
    OFF_RANK = 6
    OPP_OFF_RANK = 7
    DEF_RANK = 8
    OPP_DEF_RANK = 9
    HOST = 10
    OPP_HOST = 11
    IS_STRONG_CONFED = 12
    OPP_IS_STRONG_CONFED = 13
    STAGE_WEIGHT = 14

    def __init__(self, shape=0.625, host_discount=0.0,
                 include_off_win_exp=True, include_rank_shift=False,
                 include_stage_weight=False):
        self.shape = shape
        self.host_discount = host_discount
        self.include_off_win_exp = include_off_win_exp
        self.include_rank_shift = include_rank_shift
        self.include_stage_weight = include_stage_weight

    def fit(self, X, y=None):
        return self

    def _effective_rank(self, rank, is_host):
        """Compute effective rank with host discount.

        A percentage discount on rank that flows nonlinearly through the
        win_exp power formula. Gives biggest boost to evenly-matched teams.
        """
        return rank * (1.0 - self.host_discount * is_host)

    def _win_exp(self, rank, opp_rank, host, opp_host):
        eff_rank = self._effective_rank(rank, host)
        eff_opp_rank = self._effective_rank(opp_rank, opp_host)
        return 1.0 / (1.0 + (eff_rank / eff_opp_rank) ** self.shape)

    def transform(self, X):
        features = []

        host = X[:, self.HOST]
        opp_host = X[:, self.OPP_HOST]

        # Core win expectation features (base rank and current rank)
        features.append(self._win_exp(X[:, self.RANK], X[:, self.OPP_RANK], host, opp_host))
        features.append(self._win_exp(X[:, self.CUR_RANK], X[:, self.OPP_CUR_RANK], host, opp_host))

        # Form features (rank momentum within tournament)
        if self.include_rank_shift:
            features.append(X[:, self.RANK_SHIFT])
            features.append(X[:, self.OPP_RANK_SHIFT])

        # Offensive win expectation (team attack vs opponent defense)
        if self.include_off_win_exp:
            features.append(self._win_exp(X[:, self.OFF_RANK], X[:, self.OPP_DEF_RANK], host, opp_host))

        # Competition stage weight (0=group, 1=R16/QF/3rd, 2=SF/final)
        if self.include_stage_weight:
            features.append(X[:, self.STAGE_WEIGHT])

        return np.column_stack(features)


class OffWinExpTransformer(FullFeatureTransformer):
    """Single feature: off_win_exp (team offense vs opponent defense)."""

    def __init__(self, shape=0.625, host_discount=0.0):
        super().__init__(
            shape=shape,
            host_discount=host_discount,
            include_off_win_exp=True,
            include_rank_shift=False,
            include_stage_weight=False,
        )

    def transform(self, X):
        host = X[:, self.HOST]
        opp_host = X[:, self.OPP_HOST]
        off_win_exp = self._win_exp(
            X[:, self.OFF_RANK], X[:, self.OPP_DEF_RANK], host, opp_host,
        )
        return off_win_exp.reshape(-1, 1)
