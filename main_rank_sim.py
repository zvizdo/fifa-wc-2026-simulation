"""
Run N simulations per country, randomizing that country's FIFA rank (1-80) each time.

For every country in the tournament, this creates N simulation runs where the
target country's rank is sampled uniformly from 1 to 80 while all other teams
keep their original ranks.
"""

import argparse
import copy
import json
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

from tqdm import tqdm

from engine import Competition
from engine.match import ModeledMatch

CHUNK_SIZE = 75


def _run_chunk(args):
    """Worker: simulate a chunk for one country with randomized ranks."""
    base_data, country, start, count = args
    all_match = []
    all_stand = []
    all_third = []
    for i in range(start, start + count):
        data = copy.deepcopy(base_data)
        rank = random.randint(1, 80)
        for group_teams in data["groups"].values():
            for team in group_teams:
                if team["name"] == country:
                    team["fifa_rank"] = rank

        comp = Competition(teams_data=data, match_class=ModeledMatch)
        comp.simulate()
        m, s, t = comp.extract_rows(f"rank_{country}_{i}_{rank}")
        all_match.extend(m)
        all_stand.extend(s)
        all_third.extend(t)
    return all_match, all_stand, all_third


def main():
    parser = argparse.ArgumentParser(
        description="Run N simulations per country with randomized rank (1-80)"
    )
    parser.add_argument(
        "-n", type=int, default=50_000, help="Simulations per country (default: 50_000)"
    )
    parser.add_argument(
        "--db", type=str, default="wc2026_rank.duckdb", help="DuckDB output path"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, cpu_count() - 1),
        help="Number of worker processes (default: cpu_count - 1)",
    )
    args = parser.parse_args()

    with open("data/wc_2026_teams.json") as f:
        base_data = json.load(f)

    countries = [
        team["name"]
        for group_teams in base_data["groups"].values()
        for team in group_teams
    ]

    # Build work chunks: each chunk is one country × CHUNK_SIZE sims
    chunks = []
    for country in countries:
        for start in range(0, args.n, CHUNK_SIZE):
            count = min(CHUNK_SIZE, args.n - start)
            chunks.append((base_data, country, start, count))

    total = len(countries) * args.n
    con = Competition.init_db(args.db)

    print(
        f"Running {total} simulations ({args.n} per country, {len(countries)} countries) "
        f"across {args.workers} workers ({len(chunks)} chunks of ~{CHUNK_SIZE})..."
    )

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_chunk, chunk): chunk for chunk in chunks}
        with tqdm(total=total, desc="Simulating", unit="sim") as pbar:
            for future in as_completed(futures):
                match_rows, stand_rows, third_rows = future.result()
                Competition.insert_rows(con, match_rows, stand_rows, third_rows)
                chunk_size = len(match_rows) // 104
                pbar.update(chunk_size)

    print("Creating indexes...")
    Competition.create_db_indexes(con)
    con.close()
    print(f"Done. {total} simulations ({args.n} per country) saved to {args.db}")


if __name__ == "__main__":
    main()
