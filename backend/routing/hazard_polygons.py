"""Utility for collecting and merging hazard polygons for ORS avoidance."""

import math
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Event types that should generate avoidance polygons
ROUTING_HAZARD_TYPES = {"road_closure", "bridge_collapse", "flooding", "road_damage"}

# Default radius (meters) when generating a polygon from a point
DEFAULT_RADIUS_BY_TYPE = {
    "flooding": 500,
    "road_closure": 200,
    "bridge_collapse": 150,
    "road_damage": 100,
}


def generate_circle_polygon(
    center_lon: float,
    center_lat: float,
    radius_m: float,
    num_points: int = 8,
) -> dict:
    """
    Generate a GeoJSON Polygon approximating a circle.

    Args:
        center_lon: Longitude of center.
        center_lat: Latitude of center.
        radius_m: Radius in meters.
        num_points: Number of vertices (default 8 for octagon).

    Returns:
        GeoJSON Polygon dict with [lon, lat] coordinates and a closed ring.
    """
    coords = []
    meters_per_deg_lat = 111320
    meters_per_deg_lon = 111320 * math.cos(math.radians(center_lat))

    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        d_lat = (radius_m * math.cos(angle)) / meters_per_deg_lat
        d_lon = (radius_m * math.sin(angle)) / meters_per_deg_lon
        coords.append([
            round(center_lon + d_lon, 6),
            round(center_lat + d_lat, 6),
        ])

    # Close the ring
    coords.append(coords[0])

    return {
        "type": "Polygon",
        "coordinates": [coords],
    }


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Ray-casting test for point inside a polygon ring."""
    n = len(ring)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def collect_hazard_polygons(
    events: list[dict],
    scenario_time: datetime | None = None,
    route_endpoints: list[tuple[float, float]] | None = None,
) -> dict | None:
    """
    Collect hazard polygons from event data and merge into a MultiPolygon.

    Args:
        events: List of event dicts (from helene_timeline.json).
        scenario_time: If provided, only include events up to this time.
        route_endpoints: Optional list of (lon, lat) tuples for origin/destination.
                         Polygons containing these points are excluded so ORS
                         can still reach the start/end of the route.

    Returns:
        GeoJSON Polygon or MultiPolygon dict, or None if no hazard polygons.
    """
    polygons = []

    for event in events:
        event_type = event.get("type", "")
        if event_type not in ROUTING_HAZARD_TYPES:
            continue

        # Filter by scenario time
        if scenario_time:
            ts = event.get("timestamp", "")
            if ts:
                try:
                    event_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if event_time > scenario_time:
                        continue
                except ValueError:
                    pass

        # Resolve polygon coordinates
        poly = event.get("affected_polygon")
        if poly and poly.get("type") == "Polygon" and poly.get("coordinates"):
            ring_coords = poly["coordinates"]
        else:
            # Fallback: generate a circle polygon from the point location
            location = event.get("location", {})
            lat = location.get("lat")
            lon = location.get("lon")
            if lat is None or lon is None:
                continue
            radius = DEFAULT_RADIUS_BY_TYPE.get(event_type, 200)
            circle = generate_circle_polygon(lon, lat, radius)
            ring_coords = circle["coordinates"]

        # Skip polygons that contain a route endpoint — ORS cannot
        # route to/from a point inside an avoidance polygon.
        if route_endpoints and ring_coords:
            outer_ring = ring_coords[0]
            contains_endpoint = False
            for ep_lon, ep_lat in route_endpoints:
                if _point_in_ring(ep_lon, ep_lat, outer_ring):
                    contains_endpoint = True
                    break
            if contains_endpoint:
                continue

        polygons.append(ring_coords)

    if not polygons:
        return None

    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}

    return {"type": "MultiPolygon", "coordinates": polygons}
