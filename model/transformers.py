"""Sklearn-compatible transformers for FIFA World Cup model features."""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class WinExpTransformer(BaseEstimator, TransformerMixin):
    """Baseline transformer: (rank, opp_rank) -> win_exp.

    Input:  X[:, 0] = rank, X[:, 1] = opp_rank
    Output: single column win_exp = 1 / (1 + (rank / opp_rank) ** shape)
    """

    def __init__(self, shape=0.625):
        self.shape = shape

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        rank = X[:, 0]
        opp_rank = X[:, 1]
        win_exp = 1.0 / (1.0 + (rank / opp_rank) ** self.shape)
        return win_exp.reshape(-1, 1)


class FullFeatureTransformer(BaseEstimator, TransformerMixin):
    """Transform preprocessed feature matrix into model-ready features.

    Computes win-expectation variants from rank pairs and passes through
    auxiliary features. Feature flags allow incremental testing.

    Input columns (indices into X):
        0: rank               4: rank_shift        8: def_rank
        1: opp_rank           5: opp_rank_shift    9: opp_def_rank
        2: cur_rank           6: off_rank         10: host
        3: opp_cur_rank       7: opp_off_rank     11: is_strong_confed
                                                   12: opp_is_strong_confed
                                                   13: rest_diff
                                                   14: matches_played

    Output columns (depends on flags):
        - win_exp:            1/(1+(rank/opp_rank)^shape)
        - cur_win_exp:        1/(1+(cur_rank/opp_cur_rank)^shape)
        - rank_shift:         passthrough
        - opp_rank_shift:     passthrough
        - off_win_exp:        1/(1+(off_rank/opp_def_rank)^shape)  [if include_off_def]
        - def_win_exp:        1/(1+(def_rank/opp_off_rank)^shape)  [if include_off_def]
        - host:               passthrough
        - is_strong_confed:   passthrough [if include_confed]
        - opp_is_strong_confed: passthrough [if include_confed]
        - rest_diff:          passthrough [if include_rest]
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
    IS_STRONG_CONFED = 11
    OPP_IS_STRONG_CONFED = 12
    REST_DIFF = 13
    STAGE_WEIGHT = 14

    def __init__(self, shape=0.625, include_off_def=True,
                 include_confed=True, include_rest=True,
                 include_stage_weight=True):
        self.shape = shape
        self.include_off_def = include_off_def
        self.include_confed = include_confed
        self.include_rest = include_rest
        self.include_stage_weight = include_stage_weight

    def fit(self, X, y=None):
        return self

    def _win_exp(self, rank, opp_rank):
        return 1.0 / (1.0 + (rank / opp_rank) ** self.shape)

    def transform(self, X):
        features = []

        # Core win expectation features (base rank and current rank)
        features.append(self._win_exp(X[:, self.RANK], X[:, self.OPP_RANK]))
        features.append(self._win_exp(X[:, self.CUR_RANK], X[:, self.OPP_CUR_RANK]))

        # Form features
        features.append(X[:, self.RANK_SHIFT])
        features.append(X[:, self.OPP_RANK_SHIFT])

        # Offensive/defensive win expectation
        if self.include_off_def:
            # Team attack vs opponent defense
            features.append(self._win_exp(X[:, self.OFF_RANK], X[:, self.OPP_DEF_RANK]))
            # Team defense vs opponent attack
            features.append(self._win_exp(X[:, self.DEF_RANK], X[:, self.OPP_OFF_RANK]))

        # Host advantage
        features.append(X[:, self.HOST])

        # Confederation strength
        if self.include_confed:
            features.append(X[:, self.IS_STRONG_CONFED])
            features.append(X[:, self.OPP_IS_STRONG_CONFED])

        # Rest advantage
        if self.include_rest:
            features.append(X[:, self.REST_DIFF])

        # Competition stage weight (0=group, 1=R16/QF/3rd, 2=SF/final)
        if self.include_stage_weight:
            features.append(X[:, self.STAGE_WEIGHT])

        return np.column_stack(features)
