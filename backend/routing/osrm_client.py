"""OSRM client for real road-following route geometry."""

import logging
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

logger = logging.getLogger(__name__)

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
REQUEST_TIMEOUT = 10  # seconds


def get_road_route(
    coordinates: list[tuple[float, float]],
) -> dict | None:
    """
    Get a real road-following route from OSRM.

    Args:
        coordinates: List of (lon, lat) tuples defining waypoints.
                     Must have at least 2 points (origin and destination).

    Returns:
        Dictionary with keys:
          - coordinates: list of (lon, lat) tuples forming the road geometry
          - distance_m: total distance in meters
          - duration_s: total duration in seconds
          - steps: list of turn-by-turn direction dicts
        Returns None if request fails.
    """
    if len(coordinates) < 2:
        return None

    # Build coordinate string: "lon,lat;lon,lat;..."
    coord_str = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
    url = f"{OSRM_BASE_URL}/{coord_str}?overview=full&geometries=geojson&steps=true"

    try:
        req = Request(url, headers={"User-Agent": "DisasterReliefRouter/1.0"})
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())

        if data.get("code") != "Ok" or not data.get("routes"):
            logger.warning("OSRM returned no routes: %s", data.get("code"))
            return None

        route = data["routes"][0]
        geometry = route["geometry"]["coordinates"]

        # Extract turn-by-turn steps from the first leg
        steps = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                if step.get("maneuver", {}).get("type") == "depart" and not steps:
                    # Include depart step
                    pass
                name = step.get("name", "")
                maneuver = step.get("maneuver", {})
                steps.append({
                    "instruction": _build_instruction(maneuver, name),
                    "name": name,
                    "distance_m": step.get("distance", 0),
                    "duration_s": step.get("duration", 0),
                    "maneuver_type": maneuver.get("type", ""),
                    "maneuver_modifier": maneuver.get("modifier", ""),
                })

        return {
            "coordinates": [(c[0], c[1]) for c in geometry],
            "distance_m": route.get("distance", 0),
            "duration_s": route.get("duration", 0),
            "steps": steps,
        }

    except (URLError, TimeoutError, json.JSONDecodeError, KeyError) as e:
        logger.warning("OSRM request failed: %s", e)
        return None


def _build_instruction(maneuver: dict, road_name: str) -> str:
    """Build a human-readable instruction from OSRM maneuver data."""
    mtype = maneuver.get("type", "")
    modifier = maneuver.get("modifier", "")

    road = f" onto {road_name}" if road_name else ""

    if mtype == "depart":
        return f"Depart{road}"
    elif mtype == "arrive":
        return "Arrive at destination"
    elif mtype == "turn":
        return f"Turn {modifier}{road}"
    elif mtype == "fork":
        return f"Take the {modifier} fork{road}"
    elif mtype == "merge":
        return f"Merge {modifier}{road}"
    elif mtype == "on ramp":
        return f"Take the ramp{road}"
    elif mtype == "off ramp":
        return f"Exit{road}"
    elif mtype == "roundabout":
        return f"Enter roundabout, exit{road}"
    elif mtype == "continue":
        return f"Continue{road}"
    elif mtype == "new name":
        return f"Continue onto {road_name}" if road_name else "Continue"
    elif mtype == "end of road":
        return f"Turn {modifier}{road}"
    else:
        if modifier:
            return f"{modifier.capitalize()}{road}"
        return f"Continue{road}"
