"""Geography only: no routing or claims about pedestrian accessibility."""
from math import asin, cos, radians, sin, sqrt


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6_371_008.8 * 2 * asin(min(1.0, sqrt(a)))
