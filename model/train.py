#!/usr/bin/env python
"""Training script for the expanded Poisson regression model.

Trains a multi-feature Poisson regression model with Optuna hyperparameter
tuning and leave-one-tournament-out cross-validation. Compares against the
single-feature baseline model.

Usage:
    python -m model.train
    python -m model.train --n-trials 200
    python -m model.train --data ./data/dataset.json --seed 0
"""

import argparse
import json
import pickle
import sys

import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import mean_poisson_deviance

from model.cv import leave_one_tournament_out_cv, train_one_evaluate_rest_cv
from model.pipelines import build_baseline_pipeline, build_full_pipeline
from model.preprocessing import process_tournament_history

# Columns fed into FullFeatureTransformer (order must match transformer indices)
FEATURE_COLUMNS = [
    "rank", "opp_rank",
    "cur_rank", "opp_cur_rank",
    "rank_shift", "opp_rank_shift",
    "off_rank", "opp_off_rank",
    "def_rank", "opp_def_rank",
    "host", "opp_host",
    "is_strong_confed", "opp_is_strong_confed",
    "stage_weight",
]


def prepare_data(df_raw, preprocess_shape, k_mul, k_off_mul, k_def_mul, goal_cap):
    """Run preprocessing and extract feature matrix + targets."""
    df = process_tournament_history(
        df_raw,
        shape=preprocess_shape,
        k_mul=k_mul,
        k_off_mul=k_off_mul,
        k_def_mul=k_def_mul,
        goal_cap=goal_cap,
    )
    X = df[FEATURE_COLUMNS].values
    y = df["score"].values
    tournament_ids = df["tournament_id"].reset_index(drop=True)
    return X, y, tournament_ids


def objective(trial, df_raw):
    """Optuna objective: minimise mean Poisson deviance across CV folds."""
    # Preprocessing hyperparameters
    preprocess_shape = trial.suggest_float("preprocess_shape", 0.5, 3.0)
    k_mul = trial.suggest_float("k_mul", 1.0, 15.0)
    k_off_mul = trial.suggest_float("k_off_mul", 1.0, 15.0)
    k_def_mul = trial.suggest_float("k_def_mul", 1.0, 15.0)
    goal_cap = trial.suggest_float("goal_cap", 2.0, 6.0)

    # Feature transformer hyperparameters
    feature_shape = trial.suggest_float("feature_shape", 0.1, 3.0)
    host_discount = trial.suggest_float("host_discount", 0.0, 0.4)
    confed_discount = trial.suggest_float("confed_discount", 0.0, 0.3)

    # Regressor hyperparameters
    alpha = trial.suggest_float("alpha", 1e-6, 10.0, log=True)
    max_iter = trial.suggest_int("max_iter", 100, 1000)

    # Prepare data with current preprocessing params
    X, y, tournament_ids = prepare_data(
        df_raw, preprocess_shape, k_mul, k_off_mul, k_def_mul, goal_cap
    )

    # Build and evaluate pipeline
    pipeline = build_full_pipeline(
        shape=feature_shape,
        host_discount=host_discount,
        confed_discount=confed_discount,
        alpha=alpha,
        max_iter=max_iter,
    )

    return train_one_evaluate_rest_cv(pipeline, X, y, tournament_ids)


def run_baseline(df_raw):
    """Run baseline model and return its CV score."""
    X_base = df_raw[["rank", "opp_rank"]].values
    y_base = df_raw["score"].values
    t_ids = df_raw["tournament_id"]

    # Use known best baseline params from win_exp_model_notes.md
    pipeline = build_baseline_pipeline(shape=1.4223, alpha=0.000253, max_iter=711)
    score = train_one_evaluate_rest_cv(pipeline, X_base, y_base, t_ids)
    return score


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Train expanded Poisson regression model with Optuna."
    )
    parser.add_argument(
        "--data", default="./data/dataset.json",
        help="Path to the dataset JSON file",
    )
    parser.add_argument(
        "--n-trials", type=int, default=200,
        help="Number of Optuna trials (default: 200)",
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
        "--model-output", default="model/expanded_model.pkl",
        help="Path to save the trained model",
    )
    args = parser.parse_args(argv)

    # --- Load data ---
    df_raw = pd.read_json(args.data)
    print(f"Loaded {len(df_raw)} rows, {df_raw['tournament_id'].nunique()} tournaments")
    print(f"Tournaments: {sorted(df_raw['tournament_id'].unique())}")

    # --- Baseline ---
    print("\n" + "=" * 70)
    print("BASELINE MODEL (single win_exp feature)")
    print("=" * 70)
    baseline_score = run_baseline(df_raw)
    print(f"Baseline mean Poisson deviance: {baseline_score:.6f}")

    # --- Optuna study ---
    print("\n" + "=" * 70)
    print("EXPANDED MODEL (Optuna hyperparameter tuning)")
    print("=" * 70)
    study = optuna.create_study(
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=args.seed),
    )
    study.optimize(
        lambda trial: objective(trial, df_raw),
        n_trials=args.n_trials,
    )

    # --- Report results ---
    best = study.best_params
    print(f"\nBest mean Poisson deviance: {study.best_value:.6f}")
    print(f"Improvement over baseline:  {baseline_score - study.best_value:.6f}")
    print(f"Relative improvement:       {(baseline_score - study.best_value) / baseline_score * 100:.2f}%")
    print(f"\nBest parameters:")
    for k, v in sorted(best.items()):
        if isinstance(v, float):
            print(f"  {k:20s} = {v:.6f}")
        else:
            print(f"  {k:20s} = {v}")

    # --- Per-fold breakdown ---
    X, y, tournament_ids = prepare_data(
        df_raw, best["preprocess_shape"], best["k_mul"],
        best["k_off_mul"], best["k_def_mul"], best["goal_cap"],
    )
    pipeline = build_full_pipeline(
        shape=best["feature_shape"],
        host_discount=best["host_discount"],
        confed_discount=best["confed_discount"],
        alpha=best["alpha"],
        max_iter=best["max_iter"],
    )

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
            "baseline_score": baseline_score,
            "improvement": baseline_score - study.best_value,
            "best_params": best,
            "metric": "mean_poisson_deviance",
        }
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")

    # --- Train final model on all data ---
    final_pipeline = build_full_pipeline(
        shape=best["feature_shape"],
        host_discount=best["host_discount"],
        confed_discount=best["confed_discount"],
        alpha=best["alpha"],
        max_iter=best["max_iter"],
    )
    final_pipeline.fit(X, y)

    model_artifact = {
        "pipeline": final_pipeline,
        "preprocess_params": {
            "shape": best["preprocess_shape"],
            "k_mul": best["k_mul"],
            "k_off_mul": best["k_off_mul"],
            "k_def_mul": best["k_def_mul"],
            "goal_cap": best["goal_cap"],
        },
        "feature_params": {
            "shape": best["feature_shape"],
            "host_discount": best["host_discount"],
            "confed_discount": best["confed_discount"],
        },
        "feature_columns": FEATURE_COLUMNS,
        "best_score": study.best_value,
        "baseline_score": baseline_score,
    }
    with open(args.model_output, "wb") as f:
        pickle.dump(model_artifact, f)
    print(f"\nFinal model trained on all {len(X)} samples and saved to {args.model_output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
