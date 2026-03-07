# FIFA World Cup 2026 Simulation Explorer (WIP)

An interactive Streamlit dashboard that visualizes the results of 100,000 FIFA World Cup 2026 tournament simulations. Explore tournament outcomes through multiple lenses: overall competition, individual teams, and host cities.

## Features

- **Landing Page** — Projected podium (champion, runner-up, 3rd place) with probabilities
- **Competition Explorer** — Stage-by-stage matchup probabilities, group scenarios, head-to-head analyzer
- **Team Explorer** — Per-team tournament path, outcome distribution, and likely opponents by stage
- **City Explorer** — Host city matchup projections across 16 venues in the USA, Mexico, and Canada
- **Simulator** — Adjust team ranks with sliders to run custom simulations and compare results against the baseline

## Match Prediction Model

Each match is simulated by predicting the expected goals for both teams using a **Poisson regression model**, then sampling a scoreline from a bivariate Poisson distribution with a Dixon-Coles correction for low-scoring outcomes.

### Baseline vs Expanded Model

The **baseline model** uses a single feature — win expectation derived from the two teams' FIFA rankings:

```
win_exp = 1 / (1 + (rank / opp_rank) ^ shape)
```

The **expanded model** computes **7 transformed features** from 15 raw input columns, incorporating dynamic in-tournament ranks, offensive/defensive splits, and effective rank discounts for host advantage and confederation strength. Host and confederation effects are not modeled as separate binary features — instead, they are baked into every win-expectation calculation via effective rank discounts:

```
eff_rank = rank × (1 - host_discount × is_host) × (1 - confed_discount × is_strong_confed)
```

### Features

| Feature | Description |
|---|---|
| **Win expectation** | `1/(1+(eff_rank/eff_opp_rank)^shape)` using pre-tournament FIFA rankings, adjusted by host and confederation discounts |
| **Current win expectation** | Same formula but using dynamic in-tournament ranks that evolve after each match via Elo-style updates |
| **Rank shift** | Difference between current dynamic rank and base FIFA rank — captures momentum and form within the tournament |
| **Opponent rank shift** | Same as above, for the opponent |
| **Offensive win expectation** | Team's effective offensive rank vs opponent's effective defensive rank — measures attacking strength against the specific defensive quality faced |
| **Defensive win expectation** | Team's effective defensive rank vs opponent's effective offensive rank — measures defensive resilience against the specific attacking threat |
| **Stage weight** | Ordinal encoding of the competition round: 0 = group stage, 1 = round of 16 / quarter-finals / third-place, 2 = semi-finals / final |

### Dynamic Ranks

Three types of Elo-style ranks are tracked per team throughout the tournament, all initialized to the team's FIFA ranking at kickoff:

- **General rank** — Updated based on match result (win/draw/loss). Beating a stronger opponent improves the rank more than beating a weaker one.
- **Offensive rank** — Updated based on goals scored relative to the opponent's general quality. Scoring more than expected lowers (improves) the rank.
- **Defensive rank** — Updated based on goals conceded relative to the opponent's general quality. Conceding fewer than expected lowers (improves) the rank.

The shift magnitude is controlled by a k-factor scaled by `log(1 + |rank_diff|)`, so upsets against much stronger/weaker opponents produce larger adjustments. All rank update parameters (shape, k-factors, goal cap) are tuned jointly with the model via Optuna.

### Training

```bash
python -m model.train --n-trials 200 --seed 42
```

This runs Optuna TPE hyperparameter search over 10 parameters (5 preprocessing + 3 feature transformer + 2 regressor), evaluating each trial with train-one-evaluate-rest CV — training on a single tournament and validating on all others, a harsher test to prevent overfitting. The final model is trained on all data and saved to `model/expanded_model.pkl`.

## Tech Stack

- **Python 3.12+**
- **Streamlit** — Web dashboard
- **DuckDB** — Columnar database for efficient querying of 10M+ match rows
- **scikit-learn / scipy** — Poisson regression match prediction model
- **Optuna** — Hyperparameter tuning
- **Plotly** — Interactive charts
- **Pandas / NumPy** — Data processing

## Project Structure

```
├── app/                    # Streamlit application
│   ├── main.py             # App entry point
│   ├── config.py           # Constants & configuration
│   ├── sim_worker.py       # Worker for parallel simulation runs
│   ├── pages/              # Landing, Competition, Team, City, Simulator pages
│   ├── db/                 # DuckDB query layer (incl. simulator queries)
│   ├── ui/                 # Theme, cards, charts, brackets, flags, simulator components
│   └── data/               # DuckDB database (generated)
├── engine/                 # Simulation engine
│   ├── sim.py              # Competition orchestrator
│   ├── core.py             # Team, Match, Group classes
│   ├── match.py            # Match prediction strategies (WinExpMatch, ModeledMatch)
│   ├── schedule.py         # Tournament bracket & venue assignments
│   └── venues.py           # Host cities & stadiums
├── model/                  # ML model training & analysis
│   ├── train.py            # Expanded model training with Optuna
│   ├── preprocessing.py    # Dynamic rank computation & feature engineering
│   ├── transformers.py     # sklearn-compatible feature transformers
│   ├── pipelines.py        # Pipeline builders (baseline & full)
│   ├── cv.py               # Leave-one-tournament-out cross-validation
│   ├── expanded_model.pkl  # Trained expanded model artifact
│   ├── win_exp_model.pkl   # Trained baseline model artifact
│   ├── win_exp_model_train.py   # Legacy baseline model training
│   ├── win_exp_model_notes.md   # Baseline model notes
│   ├── nb_eda_v2.ipynb     # Expanded model EDA & feature analysis
│   ├── nb_eda.ipynb        # Baseline model EDA
│   └── nb_dataset.ipynb    # Dataset preparation notebook
├── data/                   # Raw data & team rosters
│   ├── db/                 # Historical World Cup CSVs (see below)
│   ├── wc_2026_teams.json  # 48 teams with group assignments, FIFA ranks, confederations
│   ├── wc_teams.csv/json   # Historical FIFA rankings before each World Cup
│   └── dataset.json        # Processed historical match data (pre-generated)
├── main_general_sim.py     # Run 100K simulations (parallel)
├── main_rank_sim.py        # Alternative rank-based simulation
└── requirements.txt        # Python dependencies
```

## Setup

### 1. Install dependencies

```bash
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

### 2. Add historical World Cup data

The project requires historical World Cup CSV data from the [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup/tree/master/data-csv) repository. Download all CSV files and place them in `data/db/`:

```bash
# Clone the source repo and copy the CSVs
git clone https://github.com/jfjelstul/worldcup.git /tmp/worldcup
cp /tmp/worldcup/data-csv/*.csv data/db/
```

The key files used by the project include `matches.csv`, `tournaments.csv`, and others from that dataset.

### 3. Prepare team data

The simulation requires `data/wc_2026_teams.json` — a manually curated file containing all 48 qualified teams organized by group (A–L). Each team entry includes:
- Team name
- FIFA ranking
- Confederation (UEFA, CONMEBOL, AFC, CAF, CONCACAF, OFC)
- Host flag (whether the team is a host nation)

This file must be placed in the `data/` directory before running simulations.

### 4. Core dataset

The processed historical match dataset is already included at `data/dataset.json`. It contains FIFA rankings for each team before their respective World Cup edition (1998–2022).

If you need to regenerate it (e.g. after updating the source CSVs), run the `model/nb_dataset.ipynb` notebook, which reads from `data/db/` and exports to `data/dataset.json`.

### 5. Run the simulations

Generate the DuckDB database by running 100,000 tournament simulations:

```bash
python main_general_sim.py -n 100000 --db app/data/wc2026_general.duckdb --workers 8
```

Options:
- `-n` — Number of simulations (default: 100,000)
- `--db` — Output DuckDB file path
- `--workers` — Number of parallel worker processes (default: CPU count - 1)

This uses multiprocessing to simulate tournaments in chunks of 50, with each simulation running 104 matches (72 group stage + 32 knockout). The resulting database is ~1.3 GB.

### 6. Run the app

```bash
cd app
streamlit run main.py
```

The app will be available at `http://localhost:8501`.

## Deployment

A Dockerfile is included for deploying to Google Cloud Run:

```bash
gcloud run deploy fifa-wc-2026-simulation --source . --region=us-central1 \
  --platform=managed --min-instances=1 --allow-unauthenticated
```

## Data Sources

- **Historical match data**: [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup) — World Cup match results, standings, and metadata (1930–2022)
- **2026 team roster**: Manually curated in `data/wc_2026_teams.json` — 48 teams with group assignments, FIFA rankings, and confederations
- **Historical FIFA rankings**: `data/wc_teams.csv` / `data/wc_teams.json` — FIFA rankings for each team before their respective World Cup edition (1998–2022)
