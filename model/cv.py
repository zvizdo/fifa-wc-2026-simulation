"""Leave-one-tournament-out cross-validation for Poisson regression."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_poisson_deviance
from sklearn.pipeline import Pipeline


def leave_one_tournament_out_cv(
    pipeline: Pipeline,
    X: np.ndarray,
    y: np.ndarray,
    tournament_ids: pd.Series,
) -> float:
    """Evaluate pipeline using leave-one-tournament-out CV.

    Each fold holds out one tournament as the validation set and trains on
    the remaining tournaments. Returns the mean Poisson deviance averaged
    across all folds.

    Note: X should already be preprocessed (process_tournament_history applied).
    Since rank evolution is intra-tournament only, there is no data leakage
    when preprocessing the full dataset before splitting.
    """
    unique_tournaments = tournament_ids.unique()
    fold_scores = []

    for t_id in unique_tournaments:
        train_mask = tournament_ids != t_id
        val_mask = tournament_ids == t_id

        X_train, X_val = X[train_mask], X[val_mask]
        y_train, y_val = y[train_mask], y[val_mask]

        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_val)
        y_pred = np.clip(y_pred, 1e-6, None)

        fold_scores.append(mean_poisson_deviance(y_val, y_pred))

    return np.mean(fold_scores)
