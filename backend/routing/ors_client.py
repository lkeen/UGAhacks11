"""OpenRouteService (ORS) client for road-following route geometry with polygon avoidance."""

import json
import logging
from urllib.request import urlopen, Request
from urllib.error import URLError

from backend.config import ORS_API_KEY

logger = logging.getLogger(__name__)

ORS_BASE_URL = "https://api.openrouteservice.org/v2/directions"
ORS_PROFILE = "driving-car"
REQUEST_TIMEOUT = 10  # seconds


def get_road_route(
    coordinates: list[tuple[float, float]],
    avoid_polygons: dict | None = None,
) -> dict | None:
    """
    Get a real road-following route from OpenRouteService.

    Uses the ORS Directions v2 POST endpoint with optional polygon avoidance.

    Args:
        coordinates: List of (lon, lat) tuples defining waypoints.
                     Must have at least 2 points (origin and destination).
        avoid_polygons: Optional GeoJSON Polygon or MultiPolygon to avoid.
                        Must have [lon, lat] coordinate order and closed rings.

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

    if not ORS_API_KEY:
        logger.warning("ORS_API_KEY not set, cannot call OpenRouteService")
        return None

    # Build request body
    body: dict = {
        "coordinates": [[lon, lat] for lon, lat in coordinates],
    }

    if avoid_polygons:
        body["options"] = {"avoid_polygons": avoid_polygons}

    url = f"{ORS_BASE_URL}/{ORS_PROFILE}/geojson"

    try:
        data_bytes = json.dumps(body).encode("utf-8")
        req = Request(
            url,
            data=data_bytes,
            headers={
                "Authorization": ORS_API_KEY,
                "Content-Type": "application/json",
                "User-Agent": "DisasterReliefRouter/1.0",
            },
            method="POST",
        )

        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())

        # ORS /geojson returns a GeoJSON FeatureCollection
        features = data.get("features", [])
        if not features:
            logger.warning("ORS returned no features")
            return None

        feature = features[0]
        geometry = feature["geometry"]["coordinates"]
        properties = feature["properties"]
        summary = properties.get("summary", {})

        # Extract turn-by-turn steps from segments
        steps = []
        for segment in properties.get("segments", []):
            for step in segment.get("steps", []):
                steps.append({
                    "instruction": step.get("instruction", ""),
                    "name": step.get("name", ""),
                    "distance_m": step.get("distance", 0),
                    "duration_s": step.get("duration", 0),
                    "maneuver_type": str(step.get("type", "")),
                    "maneuver_modifier": "",
                })

        return {
            "coordinates": [(c[0], c[1]) for c in geometry],
            "distance_m": summary.get("distance", 0),
            "duration_s": summary.get("duration", 0),
            "steps": steps,
        }

    except URLError as e:
        # Extract detailed error message from ORS response body
        detail = ""
        if hasattr(e, "read"):
            try:
                body = json.loads(e.read().decode())
                detail = f" - {body.get('error', {}).get('message', '')}"
            except Exception:
                pass
        logger.warning("ORS request failed: %s%s", e, detail)
        return None
    except (TimeoutError, json.JSONDecodeError, KeyError) as e:
        logger.warning("ORS request failed: %s", e)
        return None
