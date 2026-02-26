# FIFA World Cup 2026 Simulation Explorer

An interactive Streamlit dashboard that visualizes the results of 100,000 FIFA World Cup 2026 tournament simulations. Explore tournament outcomes through multiple lenses: overall competition, individual teams, and host cities.

## Features

- **Landing Page** — Projected podium (champion, runner-up, 3rd place) with probabilities
- **Competition Explorer** — Stage-by-stage matchup probabilities, group scenarios, head-to-head analyzer
- **Team Explorer** — Per-team tournament path, outcome distribution, and likely opponents by stage
- **City Explorer** — Host city matchup projections across 16 venues in the USA, Mexico, and Canada

## Tech Stack

- **Python 3.12+**
- **Streamlit** — Web dashboard
- **DuckDB** — Columnar database for efficient querying of 10M+ match rows
- **scikit-learn / scipy** — Poisson regression match prediction model
- **Plotly** — Interactive charts
- **Pandas / NumPy** — Data processing

## Project Structure

```
├── app/                    # Streamlit application
│   ├── main.py             # App entry point
│   ├── config.py           # Constants & configuration
│   ├── pages/              # Landing, Competition, Team, City pages
│   ├── db/                 # DuckDB query layer
│   ├── ui/                 # Theme, cards, charts, brackets, flags
│   └── data/               # DuckDB database (generated)
├── engine/                 # Simulation engine
│   ├── sim.py              # Competition orchestrator
│   ├── core.py             # Team, Match, Group classes
│   ├── match.py            # Match prediction strategies
│   ├── schedule.py         # Tournament bracket & venue assignments
│   └── venues.py           # Host cities & stadiums
├── model/                  # ML model & notebooks
│   ├── win_exp_model.pkl   # Trained prediction model
│   ├── nb_dataset.ipynb    # Dataset preparation notebook
│   └── nb_eda.ipynb        # Exploratory data analysis
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

### 3. Generate the core dataset

Once the CSV files are in `data/db/`, run the dataset preparation notebook to produce the processed match dataset used for model training:

```bash
jupyter lab model/nb_dataset.ipynb
```

Run all cells in `nb_dataset.ipynb`. This will:
- Load historical match data from `data/db/` (World Cup matches 1998–2022)
- Join team metadata (FIFA rankings, confederations, host status)
- Compute per-match features (goals, win/draw flags, opponent stats)
- Export the processed dataset to `data/dataset.json`

### 4. Run the simulations

Generate the DuckDB database by running 100,000 tournament simulations:

```bash
python main_general_sim.py -n 100000 --db app/data/wc2026_general.duckdb --workers 8
```

Options:
- `-n` — Number of simulations (default: 100,000)
- `--db` — Output DuckDB file path
- `--workers` — Number of parallel worker processes (default: CPU count - 1)

This uses multiprocessing to simulate tournaments in chunks of 50, with each simulation running 104 matches (72 group stage + 32 knockout). The resulting database is ~1.3 GB.

### 5. Run the app

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
- **FIFA rankings & team rosters**: Manually curated in `data/wc_2026_teams.json` and `data/wc_teams.csv`
