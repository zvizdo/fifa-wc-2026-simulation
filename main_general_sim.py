"""Run N general simulations in parallel and dump results to DuckDB."""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

from tqdm import tqdm

from engine import Competition
from engine.match import WinExpMatch

CHUNK_SIZE = 50


def _run_chunk(args):
    """Worker: simulate a chunk of tournaments, return raw rows."""
    teams_data, start, count = args
    all_match = []
    all_stand = []
    all_third = []
    for i in range(start, start + count):
        comp = Competition(teams_data=teams_data, match_class=WinExpMatch)
        comp.simulate()
        m, s, t = comp.extract_rows(f"general_{i}")
        all_match.extend(m)
        all_stand.extend(s)
        all_third.extend(t)
    return all_match, all_stand, all_third


def main():
    parser = argparse.ArgumentParser(description="Run N FIFA WC 2026 simulations")
    parser.add_argument(
        "-n", type=int, default=100_000, help="Number of simulations (default: 100_000)"
    )
    parser.add_argument(
        "--db", type=str, default="wc2026_general.duckdb", help="DuckDB output path"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, cpu_count() - 1),
        help="Number of worker processes (default: cpu_count - 1)",
    )
    args = parser.parse_args()

    with open("data/wc_2026_teams.json") as f:
        teams_data = json.load(f)

    # Build work chunks
    chunks = []
    for start in range(0, args.n, CHUNK_SIZE):
        count = min(CHUNK_SIZE, args.n - start)
        chunks.append((teams_data, start, count))

    con = Competition.init_db(args.db)

    print(f"Running {args.n} simulations across {args.workers} workers "
          f"({len(chunks)} chunks of ~{CHUNK_SIZE})...")

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_chunk, chunk): chunk for chunk in chunks}
        with tqdm(total=args.n, desc="Simulating", unit="sim") as pbar:
            for future in as_completed(futures):
                match_rows, stand_rows, third_rows = future.result()
                Competition.insert_rows(con, match_rows, stand_rows, third_rows)
                chunk_size = len(match_rows) // 104  # 104 matches per sim
                pbar.update(chunk_size)

    print("Creating indexes...")
    Competition.create_db_indexes(con)
    con.close()
    print(f"Done. {args.n} simulations saved to {args.db}")


if __name__ == "__main__":
    main()
