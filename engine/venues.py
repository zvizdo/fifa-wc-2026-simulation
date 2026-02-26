"""
Host cities and venues for FIFA World Cup 2026.
16 venues across USA (11), Mexico (3), and Canada (2).
"""


class HostCity:
    """Represents a host city venue for World Cup matches."""
    
    def __init__(self, name: str, stadium: str, country: str, capacity: int):
        self.name = name
        self.stadium = stadium
        self.country = country
        self.capacity = capacity
    
    def __repr__(self):
        return f"HostCity({self.name}, {self.stadium})"
    
    def __eq__(self, other):
        if not isinstance(other, HostCity):
            return False
        return self.name == other.name and self.stadium == other.stadium


# 16 Host Cities for FIFA World Cup 2026
HOST_CITIES = [
    # Mexico (3 venues)
    HostCity("Mexico City", "Estadio Azteca", "Mexico", 87523),
    HostCity("Guadalajara", "Estadio Akron", "Mexico", 49850),
    HostCity("Monterrey", "Estadio BBVA", "Mexico", 53500),
    
    # Canada (2 venues)
    HostCity("Toronto", "BMO Field", "Canada", 45500),
    HostCity("Vancouver", "BC Place", "Canada", 54500),
    
    # USA (11 venues)
    HostCity("Atlanta", "Mercedes-Benz Stadium", "USA", 71000),
    HostCity("Boston", "Gillette Stadium", "USA", 65878),
    HostCity("Dallas", "AT&T Stadium", "USA", 80000),
    HostCity("Houston", "NRG Stadium", "USA", 72220),
    HostCity("Kansas City", "Arrowhead Stadium", "USA", 76416),
    HostCity("Los Angeles", "SoFi Stadium", "USA", 70240),
    HostCity("Miami", "Hard Rock Stadium", "USA", 65326),
    HostCity("New York/New Jersey", "MetLife Stadium", "USA", 82500),
    HostCity("Philadelphia", "Lincoln Financial Field", "USA", 69176),
    HostCity("San Francisco", "Levi's Stadium", "USA", 68500),
    HostCity("Seattle", "Lumen Field", "USA", 69000),
]


def get_city_by_name(name: str) -> HostCity:
    """Get a host city by name."""
    for city in HOST_CITIES:
        if city.name == name:
            return city
    raise ValueError(f"Host city '{name}' not found")


def get_cities_by_country(country: str) -> list:
    """Get all host cities in a specific country."""
    return [city for city in HOST_CITIES if city.country == country]
