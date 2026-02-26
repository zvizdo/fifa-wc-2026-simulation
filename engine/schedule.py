"""
Complete match schedule for FIFA World Cup 2026.
Based on official FIFA schedule with exact venue assignments.
"""

from typing import Dict, List, Tuple
from .venues import HostCity, HOST_CITIES, get_city_by_name


# ============================================================================
# VENUE MAPPING (city names to HostCity objects)
# ============================================================================
VENUE_MAP = {
    "Mexico City": get_city_by_name("Mexico City"),
    "Guadalajara": get_city_by_name("Guadalajara"),
    "Monterrey": get_city_by_name("Monterrey"),
    "Toronto": get_city_by_name("Toronto"),
    "Vancouver": get_city_by_name("Vancouver"),
    "Atlanta": get_city_by_name("Atlanta"),
    "Boston": get_city_by_name("Boston"),  # Foxborough
    "Dallas": get_city_by_name("Dallas"),  # Arlington
    "Houston": get_city_by_name("Houston"),
    "Kansas City": get_city_by_name("Kansas City"),
    "Los Angeles": get_city_by_name("Los Angeles"),  # Inglewood
    "Miami": get_city_by_name("Miami"),
    "New York/New Jersey": get_city_by_name("New York/New Jersey"),  # East Rutherford
    "Philadelphia": get_city_by_name("Philadelphia"),
    "San Francisco": get_city_by_name("San Francisco"),  # Santa Clara
    "Seattle": get_city_by_name("Seattle"),
}


# ============================================================================
# GROUP STAGE SCHEDULE (Matches 1-72)
# Format: match_number: (group, match_day, city_name, home_seed, away_seed)
# Positions: 1=Pot1(top seed), 2=Pot2, 3=Pot3, 4=Pot4 (Based on JSON order)
# ============================================================================
GROUP_STAGE_SCHEDULE: Dict[int, Tuple[str, int, str, int, int]] = {
    # Match Day 1
    1: ("A", 1, "Mexico City", 1, 2),          # Mexico vs South Africa
    2: ("A", 1, "Guadalajara", 3, 4),          # South Korea vs TBD
    3: ("B", 1, "Toronto", 1, 2),              # Canada vs TBD
    4: ("D", 1, "Los Angeles", 1, 2),          # USA vs Paraguay
    5: ("C", 1, "Boston", 3, 4),               # Haiti vs Scotland
    6: ("D", 1, "Vancouver", 3, 4),            # Australia vs TBD
    7: ("C", 1, "New York/New Jersey", 1, 2),  # Brazil vs Morocco
    8: ("B", 1, "San Francisco", 3, 4),        # Qatar vs Switzerland
    9: ("E", 1, "Philadelphia", 3, 4),         # Ivory Coast vs Ecuador
    10: ("E", 1, "Houston", 1, 2),             # Germany vs Curaçao
    11: ("F", 1, "Dallas", 1, 2),              # Netherlands vs Japan
    12: ("F", 1, "Monterrey", 3, 4),           # TBD vs Tunisia
    13: ("H", 1, "Miami", 3, 4),               # Saudi Arabia vs Uruguay
    14: ("H", 1, "Atlanta", 1, 2),             # Spain vs Cape Verde
    15: ("G", 1, "Los Angeles", 3, 4),         # Iran vs New Zealand
    16: ("G", 1, "Seattle", 1, 2),             # Belgium vs Egypt
    17: ("I", 1, "New York/New Jersey", 1, 2), # France vs Senegal
    18: ("I", 1, "Boston", 3, 4),              # TBD vs Norway
    19: ("J", 1, "Kansas City", 1, 2),         # Argentina vs Algeria
    20: ("J", 1, "San Francisco", 3, 4),       # Austria vs Jordan
    21: ("L", 1, "Toronto", 3, 4),             # Ghana vs Panama
    22: ("L", 1, "Dallas", 1, 2),              # England vs Croatia
    23: ("K", 1, "Houston", 1, 2),             # Portugal vs TBD
    24: ("K", 1, "Mexico City", 3, 4),         # Uzbekistan vs Colombia

    # Match Day 2
    25: ("A", 2, "Atlanta", 4, 2),             # TBD vs South Africa
    26: ("B", 2, "San Francisco", 4, 2),       # Switzerland vs TBD
    27: ("B", 2, "Vancouver", 1, 3),           # Canada vs Qatar
    28: ("A", 2, "Guadalajara", 1, 3),         # Mexico vs South Korea
    29: ("C", 2, "Philadelphia", 1, 3),        # Brazil vs Haiti
    30: ("C", 2, "Boston", 4, 2),              # Scotland vs Morocco
    31: ("D", 2, "San Francisco", 4, 2),       # TBD vs Paraguay
    32: ("D", 2, "Seattle", 1, 3),             # USA vs Australia
    33: ("E", 2, "Toronto", 1, 3),             # Germany vs Ivory Coast
    34: ("E", 2, "Kansas City", 4, 2),         # Ecuador vs Curaçao
    35: ("F", 2, "Houston", 1, 3),             # Netherlands vs TBD
    36: ("F", 2, "Monterrey", 4, 2),           # Tunisia vs Japan
    37: ("H", 2, "Miami", 4, 2),               # Uruguay vs Cape Verde
    38: ("H", 2, "Atlanta", 1, 3),             # Spain vs Saudi Arabia
    39: ("G", 2, "Los Angeles", 1, 3),         # Belgium vs Iran
    40: ("G", 2, "Vancouver", 4, 2),           # New Zealand vs Egypt
    41: ("I", 2, "Philadelphia", 4, 2),        # Norway vs Senegal
    42: ("I", 2, "Boston", 1, 3),              # France vs TBD
    43: ("J", 2, "Dallas", 1, 3),              # Argentina vs Austria
    44: ("J", 2, "San Francisco", 4, 2),       # Jordan vs Algeria
    45: ("L", 2, "Boston", 1, 3),              # England vs Ghana
    46: ("L", 2, "Toronto", 4, 2),             # Panama vs Croatia
    47: ("K", 2, "Houston", 1, 3),             # Portugal vs Uzbekistan
    48: ("K", 2, "Guadalajara", 4, 2),         # Colombia vs TBD

    # Match Day 3
    49: ("C", 3, "Miami", 4, 1),               # Scotland vs Brazil
    50: ("C", 3, "Atlanta", 2, 3),             # Morocco vs Haiti
    51: ("B", 3, "Vancouver", 4, 1),           # Switzerland vs Canada
    52: ("B", 3, "Seattle", 2, 3),             # TBD vs Qatar
    53: ("A", 3, "Mexico City", 4, 1),         # TBD vs Mexico
    54: ("A", 3, "Monterrey", 2, 3),           # South Africa vs South Korea
    55: ("E", 3, "Kansas City", 2, 3),         # Curaçao vs Ivory Coast
    56: ("E", 3, "Philadelphia", 4, 1),        # Ecuador vs Germany
    57: ("F", 3, "Dallas", 2, 3),              # Japan vs TBD
    58: ("F", 3, "Kansas City", 4, 1),         # Tunisia vs Netherlands
    59: ("D", 3, "Los Angeles", 4, 1),         # TBD vs USA
    60: ("D", 3, "San Francisco", 2, 3),       # Paraguay vs Australia
    61: ("I", 3, "New York/New Jersey", 4, 1), # Norway vs France
    62: ("I", 3, "Toronto", 2, 3),             # Senegal vs TBD
    63: ("G", 3, "Seattle", 2, 3),             # Egypt vs Iran
    64: ("G", 3, "Vancouver", 4, 1),           # New Zealand vs Belgium
    65: ("H", 3, "Houston", 2, 3),             # Cape Verde vs Saudi Arabia
    66: ("H", 3, "Guadalajara", 4, 1),         # Uruguay vs Spain
    67: ("L", 3, "New York/New Jersey", 4, 1), # Panama vs England
    68: ("L", 3, "Philadelphia", 2, 3),        # Croatia vs Ghana
    69: ("J", 3, "Kansas City", 2, 3),         # Algeria vs Austria
    70: ("J", 3, "Dallas", 4, 1),              # Jordan vs Argentina
    71: ("K", 3, "Miami", 4, 1),               # Colombia vs Portugal
    72: ("K", 3, "Atlanta", 2, 3),             # TBD vs Uzbekistan
}


# ============================================================================
# ROUND OF 32 BRACKET STRUCTURE (Matches 73-88)
# This defines the EXACT bracket per FIFA rules
# Format: match_number: (city, pairing_type, team1_source, team2_source)
# pairing_type: "1v2" (winner vs runner-up), "2v2" (runner-up vs runner-up), "1v3" (winner vs 3rd)
# ============================================================================
ROUND_OF_32_BRACKET: Dict[int, Tuple[str, str, str, str]] = {
    # Left side of bracket (leads to SF1)
    73: ("Los Angeles", "2v2", "2A", "2B"),  # Runner-up A vs Runner-up B
    74: ("Boston", "1v3", "1E", "3ABCDF"),  # Winner E vs 3rd from A/B/C/D/F
    75: ("Monterrey", "1v2", "1F", "2C"),  # Winner F vs Runner-up C
    76: ("Houston", "1v2", "1C", "2F"),  # Winner C vs Runner-up F
    77: (
        "New York/New Jersey",
        "1v3",
        "1I",
        "3CDFGH",
    ),  # Winner I vs 3rd from C/D/F/G/H
    78: ("Dallas", "2v2", "2E", "2I"),  # Runner-up E vs Runner-up I
    79: ("Mexico City", "1v3", "1A", "3CEFHI"),  # Winner A vs 3rd from C/E/F/H/I
    80: ("Atlanta", "1v3", "1L", "3EHIJK"),  # Winner L vs 3rd from E/H/I/J/K
    # Right side of bracket (leads to SF2)
    81: ("San Francisco", "1v3", "1D", "3BEFIJ"),  # Winner D vs 3rd from B/E/F/I/J
    82: ("Seattle", "1v3", "1G", "3AEHIJ"),  # Winner G vs 3rd from A/E/H/I/J
    83: ("Toronto", "2v2", "2K", "2L"),  # Runner-up K vs Runner-up L
    84: ("Los Angeles", "1v2", "1H", "2J"),  # Winner H vs Runner-up J
    85: ("Vancouver", "1v3", "1B", "3EFGIJ"),  # Winner B vs 3rd from E/F/G/I/J
    86: ("Miami", "1v2", "1J", "2H"),  # Winner J vs Runner-up H
    87: ("Kansas City", "1v3", "1K", "3DEIJL"),  # Winner K vs 3rd from D/E/I/J/L
    88: ("Dallas", "2v2", "2D", "2G"),  # Runner-up D vs Runner-up G
}


# ============================================================================
# KNOCKOUT STAGE BRACKET PATH
# Format: match_number: (city, match1_source, match2_source)
# ============================================================================
ROUND_OF_16_BRACKET: Dict[int, Tuple[str, int, int]] = {
    89: ("Philadelphia", 74, 77),  # Winner M74 vs Winner M77
    90: ("Houston", 73, 75),  # Winner M73 vs Winner M75
    91: ("New York/New Jersey", 76, 78),  # Winner M76 vs Winner M78
    92: ("Mexico City", 79, 80),  # Winner M79 vs Winner M80
    93: ("Dallas", 83, 84),  # Winner M83 vs Winner M84
    94: ("Seattle", 81, 82),  # Winner M81 vs Winner M82
    95: ("Atlanta", 86, 88),  # Winner M86 vs Winner M88
    96: ("Vancouver", 85, 87),  # Winner M85 vs Winner M87
}

QUARTER_FINALS_BRACKET: Dict[int, Tuple[str, int, int]] = {
    97: ("Boston", 89, 90),  # Winner M89 vs Winner M90
    98: ("Los Angeles", 93, 94),  # Winner M93 vs Winner M94
    99: ("Miami", 91, 92),  # Winner M91 vs Winner M92
    100: ("Kansas City", 95, 96),  # Winner M95 vs Winner M96
}

SEMI_FINALS_BRACKET: Dict[int, Tuple[str, int, int]] = {
    101: ("Dallas", 97, 98),  # Winner M97 vs Winner M98
    102: ("Atlanta", 99, 100),  # Winner M99 vs Winner M100
}

# Third place playoff and Final
THIRD_PLACE_MATCH = (103, "Miami")  # Loser SF1 vs Loser SF2
FINAL_MATCH = (104, "New York/New Jersey")  # Winner SF1 vs Winner SF2


# ============================================================================
# THIRD-PLACE TEAM ASSIGNMENT TABLE
# Maps combination of 8 qualifying groups to opponent for each group winner
# Key: frozenset of 8 group letters that qualified their 3rd-place teams
# Value: dict mapping winner slot (1A, 1B, 1D, 1E, 1G, 1I, 1K, 1L) to 3rd place group
# ============================================================================
# Full table has 495 combinations; here are the key patterns simplified
# The logic: based on which 8 groups send their 3rd place, determine matchups


def get_third_place_assignments(qualifying_groups: set) -> Dict[str, str]:
    """
    Determine which third-place team plays which group winner.

    Args:
        qualifying_groups: Set of 8 group letters (A-L) whose 3rd place teams advance

    Returns:
        Dict mapping winner codes (1A, 1B, etc.) to third-place group letters
    """
    qg = frozenset(qualifying_groups)

    # Simplified assignment logic based on FIFA rules
    # The actual table has 495 rows, but follows patterns
    # Group winners playing 3rd: 1A, 1B, 1D, 1E, 1G, 1I, 1K, 1L (8 winners)

    # Default fallback - assign in order of group letter
    third_groups = sorted(qg)

    # Standard assignment patterns (simplified)
    # This follows the FIFA constraint: a group winner cannot play their own group's 3rd
    assignments = {}
    available = list(third_groups)

    winners_needing_3rd = ["1A", "1B", "1D", "1E", "1G", "1I", "1K", "1L"]

    for winner in winners_needing_3rd:
        winner_group = winner[1]  # Extract group letter

        # Find a valid opponent (not from same group)
        for g in available:
            if g != winner_group:
                assignments[winner] = f"3{g}"
                available.remove(g)
                break

    return assignments


# Build lookup table for the most common combinations
# Key brackets in the R32 that need 3rd place teams:
# Match 74: 1E vs 3rd from (A/B/C/D/F)
# Match 77: 1I vs 3rd from (C/D/F/G/H)
# Match 79: 1A vs 3rd from (C/E/F/H/I)
# Match 80: 1L vs 3rd from (E/H/I/J/K)
# Match 81: 1D vs 3rd from (B/E/F/I/J)
# Match 82: 1G vs 3rd from (A/E/H/I/J)
# Match 85: 1B vs 3rd from (E/F/G/I/J)
# Match 87: 1K vs 3rd from (D/E/I/J/L)

THIRD_PLACE_POOLS = {
    74: set("ABCDF"),
    77: set("CDFGH"),
    79: set("CEFHI"),
    80: set("EHIJK"),
    81: set("BEFIJ"),
    82: set("AEHIJ"),
    85: set("EFGIJ"),
    87: set("DEIJL"),
}


def get_third_place_for_match(match_number: int, advancing_third_groups: set) -> str:
    """
    Get which third-place team plays in a specific R32 match.

    Args:
        match_number: Match number (74, 77, 79, 80, 81, 82, 85, or 87)
        advancing_third_groups: Set of 8 group letters whose 3rd teams advance

    Returns:
        Group letter of the third-place team for this match
    """
    if match_number not in THIRD_PLACE_POOLS:
        raise ValueError(f"Match {match_number} does not involve a 3rd place team")

    pool = THIRD_PLACE_POOLS[match_number]
    candidates = pool & advancing_third_groups

    if not candidates:
        raise ValueError(f"No valid 3rd place team for match {match_number}")

    # Use defined priority (based on FIFA rules - prefer certain groups)
    priority_order = list("ABCDEFGHIJKL")
    for group in priority_order:
        if group in candidates:
            return group

    return sorted(candidates)[0]


def get_venue_for_match(match_number: int) -> HostCity:
    """Get the host city for a specific match number."""
    if match_number <= 72:
        # Group stage
        if match_number in GROUP_STAGE_SCHEDULE:
            _, _, city_name, _, _ = GROUP_STAGE_SCHEDULE[match_number]
            return VENUE_MAP[city_name]
    elif match_number <= 88:
        # Round of 32
        if match_number in ROUND_OF_32_BRACKET:
            city_name, _, _, _ = ROUND_OF_32_BRACKET[match_number]
            return VENUE_MAP[city_name]
    elif match_number <= 96:
        # Round of 16
        if match_number in ROUND_OF_16_BRACKET:
            city_name, _, _ = ROUND_OF_16_BRACKET[match_number]
            return VENUE_MAP[city_name]
    elif match_number <= 100:
        # Quarter-finals
        if match_number in QUARTER_FINALS_BRACKET:
            city_name, _, _ = QUARTER_FINALS_BRACKET[match_number]
            return VENUE_MAP[city_name]
    elif match_number <= 102:
        # Semi-finals
        if match_number in SEMI_FINALS_BRACKET:
            city_name, _, _ = SEMI_FINALS_BRACKET[match_number]
            return VENUE_MAP[city_name]
    elif match_number == 103:
        return VENUE_MAP[THIRD_PLACE_MATCH[1]]
    elif match_number == 104:
        return VENUE_MAP[FINAL_MATCH[1]]

    raise ValueError(f"Unknown match number: {match_number}")
