"""Pipeline definitions for FIFA World Cup Poisson regression models."""

from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import Pipeline

from sklearn.preprocessing import StandardScaler

from model.transformers import FullFeatureTransformer, WinExpTransformer


def build_baseline_pipeline(shape=0.625, alpha=0.000253, max_iter=711):
    """Original single-feature baseline pipeline."""
    return Pipeline([
        ("win_exp", WinExpTransformer(shape=shape)),
        ("poisson", PoissonRegressor(alpha=alpha, max_iter=max_iter)),
    ])


def build_full_pipeline(shape=0.625, host_discount=0.0, confed_discount=0.0, 
                        alpha=0.000253, max_iter=711,
                        include_off_def=True, include_stage_weight=True):
    """Full multi-feature pipeline with configurable feature groups."""
    return Pipeline([
        ("features", FullFeatureTransformer(
            shape=shape,
            host_discount=host_discount,
            confed_discount=confed_discount,
            include_off_def=include_off_def,
            include_stage_weight=include_stage_weight,
        )),
        ("scaler", StandardScaler()),
        ("poisson", PoissonRegressor(alpha=alpha, max_iter=max_iter)),
    ])
