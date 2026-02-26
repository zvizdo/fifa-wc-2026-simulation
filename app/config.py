"""
Global constants for the FIFA World Cup 2026 Simulation Explorer app.
"""

TOTAL_SIMS = 100_000

# --- FIFA 2026 Color Palette ---
PRIMARY_TURQUOISE = "#00B4D8"
MAGENTA = "#E63E6D"
GOLD = "#FFB703"
DARK_BG = "#0A1628"
LIGHT_TEXT = "#F0F4F8"
CARD_BG = "#FFFFFF"
SECONDARY_TEXT = "#6B7280"
LIGHT_BG = "#F0F4F8"

# --- Stage ordering and display names ---
STAGE_ORDER = [
    "GROUP_STAGE",
    "ROUND_OF_32",
    "ROUND_OF_16",
    "QUARTER_FINALS",
    "SEMI_FINALS",
    "THIRD_PLACE",
    "FINAL",
]

STAGE_DISPLAY_NAMES = {
    "GROUP_STAGE": "Group Stage",
    "ROUND_OF_32": "Round of 32",
    "ROUND_OF_16": "Round of 16",
    "QUARTER_FINALS": "Quarter-Finals",
    "SEMI_FINALS": "Semi-Finals",
    "THIRD_PLACE": "3rd Place Match",
    "FINAL": "Final",
}

# Knockout stages shown in the Competition Explorer selector (reverse order for UI)
KNOCKOUT_STAGES_UI = [
    "FINAL",
    "SEMI_FINALS",
    "QUARTER_FINALS",
    "ROUND_OF_16",
    "ROUND_OF_32",
    "GROUP_STAGE",
    "HEAD_TO_HEAD",
]

KNOCKOUT_STAGE_LABELS = {
    "FINAL": "Final",
    "SEMI_FINALS": "Semi-Finals",
    "QUARTER_FINALS": "Quarter-Finals",
    "ROUND_OF_16": "Round of 16",
    "ROUND_OF_32": "Round of 32",
    "GROUP_STAGE": "Group Stage",
    "HEAD_TO_HEAD": "Head-to-Head",
}

# --- City coordinates for the map ---
CITY_COORDS = {
    "Mexico City": {"lat": 19.4326, "lon": -99.1332, "country": "Mexico"},
    "Guadalajara": {"lat": 20.6597, "lon": -103.3496, "country": "Mexico"},
    "Monterrey": {"lat": 25.6866, "lon": -100.3161, "country": "Mexico"},
    "Toronto": {"lat": 43.6426, "lon": -79.3871, "country": "Canada"},
    "Vancouver": {"lat": 49.2765, "lon": -123.1118, "country": "Canada"},
    "Atlanta": {"lat": 33.7573, "lon": -84.4009, "country": "USA"},
    "Boston": {"lat": 42.0909, "lon": -71.2643, "country": "USA"},
    "Dallas": {"lat": 32.7473, "lon": -97.0945, "country": "USA"},
    "Houston": {"lat": 29.6847, "lon": -95.4107, "country": "USA"},
    "Kansas City": {"lat": 39.0489, "lon": -94.4839, "country": "USA"},
    "Los Angeles": {"lat": 33.9535, "lon": -118.3392, "country": "USA"},
    "Miami": {"lat": 25.9580, "lon": -80.2389, "country": "USA"},
    "New York/New Jersey": {"lat": 40.8135, "lon": -74.0745, "country": "USA"},
    "Philadelphia": {"lat": 39.9012, "lon": -75.1676, "country": "USA"},
    "San Francisco": {"lat": 37.4033, "lon": -121.9694, "country": "USA"},
    "Seattle": {"lat": 47.5952, "lon": -122.3316, "country": "USA"},
}

CITY_STADIUMS = {
    "Mexico City": ("Estadio Azteca", 87523),
    "Guadalajara": ("Estadio Akron", 49850),
    "Monterrey": ("Estadio BBVA", 53500),
    "Toronto": ("BMO Field", 45500),
    "Vancouver": ("BC Place", 54500),
    "Atlanta": ("Mercedes-Benz Stadium", 71000),
    "Boston": ("Gillette Stadium", 65878),
    "Dallas": ("AT&T Stadium", 80000),
    "Houston": ("NRG Stadium", 72220),
    "Kansas City": ("Arrowhead Stadium", 76416),
    "Los Angeles": ("SoFi Stadium", 70240),
    "Miami": ("Hard Rock Stadium", 65326),
    "New York/New Jersey": ("MetLife Stadium", 82500),
    "Philadelphia": ("Lincoln Financial Field", 69176),
    "San Francisco": ("Levi's Stadium", 68500),
    "Seattle": ("Lumen Field", 69000),
}

COUNTRY_COLORS = {
    "USA": "#3B82F6",
    "Mexico": "#22C55E",
    "Canada": "#EF4444",
}

# --- Outcome ordering for team explorer ---
OUTCOME_ORDER = [
    "Champion",
    "Runner-up",
    "3rd Place",
    "4th Place",
    "Semi-Finals Exit",
    "Quarter-Finals Exit",
    "Round of 16 Exit",
    "Round of 32 Exit",
    "Group Stage Exit",
]

GROUP_NAMES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
