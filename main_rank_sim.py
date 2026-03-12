"""
Run N simulations with fully randomized FIFA ranks.

Before each simulation, all 48 teams receive a random permutation of ranks 1–48.
This gives every team equal coverage across the full rank spectrum, which is
needed for building accurate win-rate curves for the implied Polymarket rank
optimizer.
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

CHUNK_SIZE = 50


def randomize_ranks(base_data: dict, sim_id: str) -> tuple[dict, list]:
    """
    Fully randomize all team FIFA ranks.

    Each team independently receives a random rank drawn uniformly from 1–80,
    covering the realistic spectrum of World Cup-caliber nations. Collisions
    are resolved by pushing duplicates to the next free slot.
    """
    data = copy.deepcopy(base_data)

    teams = []
    for group_teams in data["groups"].values():
        teams.extend(group_teams)

    # Draw independent random targets
    targets = [(team, random.randint(1, 80)) for team in teams]

    # Sort by target rank, shuffle ties randomly
    random.shuffle(targets)
    targets.sort(key=lambda x: x[1])

    # Assign unique ranks, pushing collisions to the next free slot
    rank_rows = []
    occupied = set()
    for team, target in targets:
        rank = target
        while rank in occupied:
            rank += 1
        occupied.add(rank)
        team["fifa_rank"] = rank
        rank_rows.append((sim_id, team["name"], rank))

    return data, rank_rows


def _run_chunk(args):
    """Worker: simulate a chunk of tournaments with randomized ranks."""
    base_data, start, count = args
    all_match = []
    all_stand = []
    all_third = []
    all_ranks = []
    
    for i in range(start, start + count):
        sim_id = f"rank_sim_{i}"
        sim_data, rank_rows = randomize_ranks(base_data, sim_id)
        
        comp = Competition(teams_data=sim_data, match_class=ModeledMatch)
        comp.simulate()
        m, s, t = comp.extract_rows(sim_id)
        all_match.extend(m)
        all_stand.extend(s)
        all_third.extend(t)
        all_ranks.extend(rank_rows)
    return all_match, all_stand, all_third, all_ranks


def main():
    parser = argparse.ArgumentParser(
        description="Run N simulations with randomized ranks across all teams"
    )
    parser.add_argument(
        "-n", type=int, default=100_000, help="Total simulations to run (default: 100_000)"
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

    # Build work chunks
    chunks = []
    for start in range(0, args.n, CHUNK_SIZE):
        count = min(CHUNK_SIZE, args.n - start)
        chunks.append((base_data, start, count))

    con = Competition.init_db(args.db)
    
    # We must add our sim_team_ranks table definition
    con.execute("""
        CREATE TABLE IF NOT EXISTS sim_team_ranks (
            sim_id       VARCHAR NOT NULL,
            team         VARCHAR NOT NULL,
            fifa_rank    INTEGER NOT NULL,
            PRIMARY KEY (sim_id, team)
        )
    """)

    print(
        f"Running {args.n} overall simulations "
        f"across {args.workers} workers ({len(chunks)} chunks of ~{CHUNK_SIZE})..."
    )

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_chunk, chunk): chunk for chunk in chunks}
        with tqdm(total=args.n, desc="Simulating", unit="sim") as pbar:
            for future in as_completed(futures):
                match_rows, stand_rows, third_rows, rank_rows = future.result()
                Competition.insert_rows(con, match_rows, stand_rows, third_rows)
                
                # Insert dynamic team ranks
                con.executemany(
                    "INSERT INTO sim_team_ranks VALUES (?,?,?)",
                    rank_rows,
                )
                
                chunk_size = len(match_rows) // 104
                pbar.update(chunk_size)

    print("Creating indexes...")
    Competition.create_db_indexes(con)
    con.execute("CREATE INDEX IF NOT EXISTS idx_sim_team_ranks_sim ON sim_team_ranks (sim_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_sim_team_ranks_team ON sim_team_ranks (team)")
    con.close()
    print(f"Done. {args.n} simulations saved to {args.db}")


if __name__ == "__main__":
    main()
