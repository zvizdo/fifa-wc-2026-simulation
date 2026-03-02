from engine import Competition, STAGE
from engine.match import ModeledMatch

comp = Competition.from_json_file(
    "data/wc_2026_teams.json", match_class=ModeledMatch #, random_seed=42
)
champion = comp.simulate()
comp.print_results()
# Access specific matches
final = comp.matches_by_number[104]
print(f"Final at: {final.city.stadium}")  # MetLife Stadium
