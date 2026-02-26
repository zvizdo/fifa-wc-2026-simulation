"""
Country flag emoji mapping for all 48 FIFA World Cup 2026 teams.
"""

FLAG_EMOJI = {
    "Algeria": "\U0001f1e9\U0001f1ff",
    "Argentina": "\U0001f1e6\U0001f1f7",
    "Australia": "\U0001f1e6\U0001f1fa",
    "Austria": "\U0001f1e6\U0001f1f9",
    "Belgium": "\U0001f1e7\U0001f1ea",
    "Brazil": "\U0001f1e7\U0001f1f7",
    "Canada": "\U0001f1e8\U0001f1e6",
    "Cape Verde": "\U0001f1e8\U0001f1fb",
    "Colombia": "\U0001f1e8\U0001f1f4",
    "Croatia": "\U0001f1ed\U0001f1f7",
    "Cura\u00e7ao": "\U0001f1e8\U0001f1fc",
    "Ecuador": "\U0001f1ea\U0001f1e8",
    "Egypt": "\U0001f1ea\U0001f1ec",
    "England": "\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f",
    "France": "\U0001f1eb\U0001f1f7",
    "Germany": "\U0001f1e9\U0001f1ea",
    "Ghana": "\U0001f1ec\U0001f1ed",
    "Haiti": "\U0001f1ed\U0001f1f9",
    "Iran": "\U0001f1ee\U0001f1f7",
    "Ivory Coast": "\U0001f1e8\U0001f1ee",
    "Japan": "\U0001f1ef\U0001f1f5",
    "Jordan": "\U0001f1ef\U0001f1f4",
    "Mexico": "\U0001f1f2\U0001f1fd",
    "Morocco": "\U0001f1f2\U0001f1e6",
    "Netherlands": "\U0001f1f3\U0001f1f1",
    "New Zealand": "\U0001f1f3\U0001f1ff",
    "Norway": "\U0001f1f3\U0001f1f4",
    "Panama": "\U0001f1f5\U0001f1e6",
    "Paraguay": "\U0001f1f5\U0001f1fe",
    "Portugal": "\U0001f1f5\U0001f1f9",
    "Qatar": "\U0001f1f6\U0001f1e6",
    "Saudi Arabia": "\U0001f1f8\U0001f1e6",
    "Scotland": "\U0001f3f4\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f",
    "Senegal": "\U0001f1f8\U0001f1f3",
    "South Africa": "\U0001f1ff\U0001f1e6",
    "South Korea": "\U0001f1f0\U0001f1f7",
    "Spain": "\U0001f1ea\U0001f1f8",
    "Switzerland": "\U0001f1e8\U0001f1ed",
    "Tunisia": "\U0001f1f9\U0001f1f3",
    "USA": "\U0001f1fa\U0001f1f8",
    "Uruguay": "\U0001f1fa\U0001f1fe",
    "Uzbekistan": "\U0001f1fa\U0001f1ff",
    "TBD (UEFA Path A)": "\U0001f3f3\ufe0f",
    "TBD (UEFA Path B)": "\U0001f3f3\ufe0f",
    "TBD (UEFA Path C)": "\U0001f3f3\ufe0f",
    "TBD (UEFA Path D)": "\U0001f3f3\ufe0f",
    "TBD (IC Path 1)": "\U0001f3f3\ufe0f",
    "TBD (IC Path 2)": "\U0001f3f3\ufe0f",
}


def team_with_flag(team_name: str) -> str:
    """Return 'FLAG TeamName' string for display."""
    flag = FLAG_EMOJI.get(team_name, "\U0001f3f3\ufe0f")
    return f"{flag} {team_name}"


def get_flag(team_name: str) -> str:
    """Return just the flag emoji for a team."""
    return FLAG_EMOJI.get(team_name, "\U0001f3f3\ufe0f")
