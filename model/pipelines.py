"""Pipeline definitions for FIFA World Cup Poisson regression models."""

from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import Pipeline

from model.transformers import FullFeatureTransformer, WinExpTransformer


def build_baseline_pipeline(shape=0.625, alpha=0.000253, max_iter=711):
    """Original single-feature baseline pipeline."""
    return Pipeline([
        ("win_exp", WinExpTransformer(shape=shape)),
        ("poisson", PoissonRegressor(alpha=alpha, max_iter=max_iter)),
    ])


def build_full_pipeline(shape=0.625, alpha=0.000253, max_iter=711,
                        include_off_def=True, include_confed=True,
                        include_rest=True, include_matches_played=True):
    """Full multi-feature pipeline with configurable feature groups."""
    return Pipeline([
        ("features", FullFeatureTransformer(
            shape=shape,
            include_off_def=include_off_def,
            include_confed=include_confed,
            include_rest=include_rest,
            include_matches_played=include_matches_played,
        )),
        ("poisson", PoissonRegressor(alpha=alpha, max_iter=max_iter)),
    ])
