"""Sklearn-compatible transformers for FIFA World Cup model features."""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class WinExpTransformer(BaseEstimator, TransformerMixin):
    """Baseline transformer: (rank, opp_rank) -> win_exp.

    Input:  X[:, 0] = rank, X[:, 1] = opp_rank
    Output: single column win_exp = 1 / (1 + (rank / opp_rank) ** shape)
    """

    def __init__(self, shape=0.625, host_discount=0.0, confed_discount=0.0):
        self.shape = shape
        self.host_discount = host_discount
        self.confed_discount = confed_discount

    def fit(self, X, y=None):
        return self

    def _effective_rank(self, rank, is_host, is_strong_confed):
        discount = (1.0 - self.host_discount * is_host) * (1.0 - self.confed_discount * is_strong_confed)
        return rank * discount

    def transform(self, X):
        rank = X[:, 0]
        opp_rank = X[:, 1]
        
        # If we only have 2 columns, it's the baseline. Assume no host/confed advantages.
        if X.shape[1] > 2:
            host = X[:, 2]
            opp_host = X[:, 3]
            confed = X[:, 4]
            opp_confed = X[:, 5]
            rank = self._effective_rank(rank, host, confed)
            opp_rank = self._effective_rank(opp_rank, opp_host, opp_confed)
            
        win_exp = 1.0 / (1.0 + (rank / opp_rank) ** self.shape)
        return win_exp.reshape(-1, 1)


class FullFeatureTransformer(BaseEstimator, TransformerMixin):
    """Transform preprocessed feature matrix into model-ready features.

    Computes win-expectation variants from rank pairs and passes through
    auxiliary features. Feature flags allow incremental testing.

    Input columns (indices into X):
        0: rank               4: rank_shift        8: def_rank             12: is_strong_confed
        1: opp_rank           5: opp_rank_shift    9: opp_def_rank         13: opp_is_strong_confed
        2: cur_rank           6: off_rank         10: host                 14: stage_weight
        3: opp_cur_rank       7: opp_off_rank     11: opp_host

    Output columns:
        - win_exp:            1/(1+(eff_rank/eff_opp_rank)^shape)
        - cur_win_exp:        1/(1+(eff_cur_rank/eff_opp_cur_rank)^shape)
        - rank_shift:         passthrough
        - opp_rank_shift:     passthrough
        - off_win_exp:        1/(1+(eff_off_rank/eff_opp_def_rank)^shape)  [if include_off_def]
        - def_win_exp:        1/(1+(eff_def_rank/eff_opp_off_rank)^shape)  [if include_off_def]
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

    def __init__(self, shape=0.625, host_discount=0.0, confed_discount=0.0,
                 include_off_def=True, include_stage_weight=True):
        self.shape = shape
        self.host_discount = host_discount
        self.confed_discount = confed_discount
        self.include_off_def = include_off_def
        self.include_stage_weight = include_stage_weight

    def fit(self, X, y=None):
        return self

    def _effective_rank(self, rank, is_host, is_strong_confed):
        discount = (1.0 - self.host_discount * is_host) * (1.0 - self.confed_discount * is_strong_confed)
        return rank * discount

    def _win_exp(self, rank, opp_rank, host, opp_host, confed, opp_confed):
        eff_rank = self._effective_rank(rank, host, confed)
        eff_opp_rank = self._effective_rank(opp_rank, opp_host, opp_confed)
        return 1.0 / (1.0 + (eff_rank / eff_opp_rank) ** self.shape)

    def transform(self, X):
        features = []
        
        host = X[:, self.HOST]
        opp_host = X[:, self.OPP_HOST]
        confed = X[:, self.IS_STRONG_CONFED]
        opp_confed = X[:, self.OPP_IS_STRONG_CONFED]

        # Core win expectation features (base rank and current rank)
        features.append(self._win_exp(X[:, self.RANK], X[:, self.OPP_RANK], host, opp_host, confed, opp_confed))
        features.append(self._win_exp(X[:, self.CUR_RANK], X[:, self.OPP_CUR_RANK], host, opp_host, confed, opp_confed))

        # Form features
        features.append(X[:, self.RANK_SHIFT])
        features.append(X[:, self.OPP_RANK_SHIFT])

        # Offensive/defensive win expectation
        if self.include_off_def:
            # Team attack vs opponent defense
            features.append(self._win_exp(X[:, self.OFF_RANK], X[:, self.OPP_DEF_RANK], host, opp_host, confed, opp_confed))
            # Team defense vs opponent attack
            features.append(self._win_exp(X[:, self.DEF_RANK], X[:, self.OPP_OFF_RANK], host, opp_host, confed, opp_confed))

        # Competition stage weight (0=group, 1=R16/QF/3rd, 2=SF/final)
        if self.include_stage_weight:
            features.append(X[:, self.STAGE_WEIGHT])

        return np.column_stack(features)
