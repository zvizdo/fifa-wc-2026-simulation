"""
Worker module for parallel simulations.
Moving these out of the Streamlit page script allows them to be properly pickled
by the multiprocessing framework (ProcessPoolExecutor).
"""

from engine.sim import Competition
from engine.match import ModeledMatch
from config import SIMULATOR_BASE_SEED


def run_single_sim(args):
    """Run a single simulation."""
    teams_data, seed_index = args
    seed = SIMULATOR_BASE_SEED + seed_index
    comp = Competition(teams_data=teams_data, random_seed=seed,
                       match_class=ModeledMatch)
    comp.simulate()
    return comp.extract_rows(f"u{seed_index}")
