"""
Engine package for FIFA World Cup 2026 Simulation Engine.
"""
from .core import STAGE, Team, Match, Group
from .sim import Competition
from .venues import HostCity, HOST_CITIES, get_city_by_name
from .schedule import (
    GROUP_STAGE_SCHEDULE,
    ROUND_OF_32_BRACKET,
    ROUND_OF_16_BRACKET,
    QUARTER_FINALS_BRACKET,
    SEMI_FINALS_BRACKET,
    THIRD_PLACE_MATCH,
    FINAL_MATCH,
    get_venue_for_match,
)

__all__ = [
    'STAGE',
    'Team',
    'Match',
    'Group',
    'Competition',
    'HostCity',
    'HOST_CITIES',
    'get_city_by_name',
    'GROUP_STAGE_SCHEDULE',
    'ROUND_OF_32_BRACKET',
    'ROUND_OF_16_BRACKET',
    'QUARTER_FINALS_BRACKET',
    'SEMI_FINALS_BRACKET',
    'THIRD_PLACE_MATCH',
    'FINAL_MATCH',
    'get_venue_for_match',
]
