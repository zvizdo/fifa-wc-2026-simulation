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

### Single Feature, Many Things Rolled In

The production model uses a **single feature** — offensive win expectation — which compresses a rich set of information into one number:

```
off_win_exp = 1 / (1 + (eff_off_rank / eff_opp_def_rank) ^ shape)
```

Where `eff_rank = rank × (1 - host_discount × is_host)`.

This one formula captures five distinct signals:

| Signal | How it's encoded |
|---|---|
| **Pre-tournament quality** | Base FIFA ranking, initialized from the pre-tournament standings |
| **In-tournament form** | Dynamic offensive rank evolves after each match via Elo-style updates — teams that score more than expected improve |
| **Matchup specificity** | Offensive rank is compared against the *opponent's defensive rank*, not their overall rank — a clinical attack against a leaky defense reads differently than the same attack against a solid one |
| **Host advantage** | Host nations receive a percentage discount on their effective rank, making the win-exp nonlinearly larger for evenly-matched games — where crowd effect matters most |
| **Rank curvature** | The power `shape` controls how sharply win probability falls off with rank distance — tuned jointly with everything else via Optuna |

The simplicity is deliberate. Feature ablation testing showed that adding win expectation from base rankings, current rankings, and defensive decomposition all introduced correlated signals that diluted rather than added predictive power. A single well-constructed feature generalizes better under the train-one-evaluate-rest CV protocol — the harshest test for simulation extrapolation.

### Dynamic Ranks

Three Elo-style ranks are tracked per team throughout the tournament, all starting at the team's pre-tournament FIFA ranking:

- **General rank** — Updated after each match based on result vs opponent quality.
- **Offensive rank** — Updated based on goals scored relative to the opponent's general quality. Feeds directly into the `off_win_exp` feature.
- **Defensive rank** — Updated based on goals conceded. Used as the opponent's defensive component in `off_win_exp`.

Update magnitude scales with `log(1 + |rank_diff|)` — upsets produce larger adjustments. All update parameters (shape, k-factors, goal cap) are tuned jointly with the model.

**Mean reversion.** After each rank update, the dynamic rank is pulled partway back toward the team's base FIFA ranking:

```
new_rank = (1 - reversion_rate) × dynamic_rank + reversion_rate × base_rank
```

This matters because World Cup groups play only 3 matches before knockout. Without reversion, a single fluky result — a top side conceding an early own goal — can swing the offensive or defensive rank far enough to distort all subsequent predictions. Mean reversion anchors each dynamic rank to our best prior (the pre-tournament FIFA ranking) and controls how aggressively one match can revise it. The `reversion_rate` is tuned by Optuna alongside the other preprocessing parameters.

### Training

```bash
python -m model.train --n-trials 200 --seed 42
```

Optuna TPE search over 9 hyperparameters: 6 controlling dynamic rank preprocessing (shape, k-factors, goal cap, reversion rate) and 3 controlling the feature transformer and regressor (feature shape, host discount, alpha). Each trial is evaluated with **train-one-evaluate-rest CV** — training on a single tournament (~128 rows) and validating on the remaining 6 (~720 rows). This harsher protocol favors models that extrapolate cleanly rather than ones that memorize training patterns.

The final model is trained on all data and saved to `model/expanded_model.pkl`.

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
