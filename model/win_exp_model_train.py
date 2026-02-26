#!/usr/bin/env python
"""
CLI for training a win-expectation Poisson regression model with Optuna
hyperparameter tuning and leave-one-tournament-out cross-validation.

Usage:
    python model/win_exp_model_train.py
    python model/win_exp_model_train.py --n-trials 200 --output model/best_params.json
    python model/win_exp_model_train.py --data ./data/dataset.json --seed 0
    python model/win_exp_model_train.py --model-output model/custom_model.pkl
"""

import argparse
import json
import pickle
import sys

import numpy as np
import optuna
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import mean_poisson_deviance
from sklearn.pipeline import Pipeline


class WinExpTransformer(BaseEstimator, TransformerMixin):
    """Transform (rank, opp_rank) into a single win-expectation feature.

    win_exp = 1 / (1 + (rank / opp_rank) ** shape)
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


def leave_one_tournament_out_cv(pipeline, X, y, tournament_ids):
    """Evaluate the pipeline using leave-one-tournament-out cross-validation.

    Each fold holds out one tournament as the validation set and trains on
    the remaining tournaments. Returns the mean Poisson deviance averaged
    across all folds.
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

        # Poisson deviance requires strictly positive predictions
        y_pred = np.clip(y_pred, 1e-6, None)

        fold_scores.append(mean_poisson_deviance(y_val, y_pred))

    return np.mean(fold_scores)


def objective(trial, X, y, tournament_ids):
    """Optuna objective: minimise mean Poisson deviance across CV folds."""
    shape = trial.suggest_float("shape", 0.1, 3.0)
    alpha = trial.suggest_float("alpha", 1e-6, 10.0, log=True)
    max_iter = trial.suggest_int("max_iter", 100, 1000)

    pipeline = Pipeline([
        ("win_exp", WinExpTransformer(shape=shape)),
        ("poisson", PoissonRegressor(alpha=alpha, max_iter=max_iter)),
    ])

    return leave_one_tournament_out_cv(pipeline, X, y, tournament_ids)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Train a win-expectation Poisson regression model "
                    "with Optuna hyperparameter tuning."
    )
    parser.add_argument(
        "--data", default="./data/dataset.json",
        help="Path to the dataset JSON file (default: ./data/dataset.json)",
    )
    parser.add_argument(
        "--n-trials", type=int, default=100,
        help="Number of Optuna trials (default: 100)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for the Optuna sampler (default: 42)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Path to save best parameters as JSON",
    )
    parser.add_argument(
        "--model-output", default="model/win_exp_model.pkl",
        help="Path to save the trained model (default: model/win_exp_model.pkl)",
    )
    args = parser.parse_args(argv)

    # --- Load data ---
    df = pd.read_json(args.data)
    X = df[["rank", "opp_rank"]].values
    y = df["score"].values
    tournament_ids = df["tournament_id"]

    print(f"Loaded {len(df)} rows, {tournament_ids.nunique()} tournaments")
    print(f"Tournaments: {sorted(tournament_ids.unique())}")

    # --- Optuna study ---
    study = optuna.create_study(
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=args.seed),
    )
    study.optimize(
        lambda trial: objective(trial, X, y, tournament_ids),
        n_trials=args.n_trials,
    )

    # --- Report results ---
    best = study.best_params
    print(f"\nBest mean Poisson deviance: {study.best_value:.6f}")
    print(f"Best parameters:")
    print(f"  shape    = {best['shape']:.4f}")
    print(f"  alpha    = {best['alpha']:.6f}")
    print(f"  max_iter = {best['max_iter']}")

    # --- Per-fold breakdown with best params ---
    pipeline = Pipeline([
        ("win_exp", WinExpTransformer(shape=best["shape"])),
        ("poisson", PoissonRegressor(alpha=best["alpha"], max_iter=best["max_iter"])),
    ])

    print("\nPer-tournament fold scores (mean Poisson deviance):")
    for t_id in sorted(tournament_ids.unique()):
        train_mask = tournament_ids != t_id
        val_mask = tournament_ids == t_id
        pipeline.fit(X[train_mask], y[train_mask])
        y_pred = np.clip(pipeline.predict(X[val_mask]), 1e-6, None)
        score = mean_poisson_deviance(y[val_mask], y_pred)
        print(f"  {t_id}: {score:.4f}  (n={val_mask.sum()})")

    # --- Save results ---
    if args.output:
        results = {
            "best_score": study.best_value,
            "best_params": best,
            "metric": "mean_poisson_deviance",
        }
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")

    # --- Train final model on all data and pickle it ---
    final_pipeline = Pipeline([
        ("win_exp", WinExpTransformer(shape=best["shape"])),
        ("poisson", PoissonRegressor(alpha=best["alpha"], max_iter=best["max_iter"])),
    ])
    final_pipeline.fit(X, y)

    with open(args.model_output, "wb") as f:
        pickle.dump(final_pipeline, f)
    print(f"\nFinal model trained on all {len(X)} samples and saved to {args.model_output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
