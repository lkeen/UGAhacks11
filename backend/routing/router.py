"""Route planning and optimization."""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime

from backend.agents.base_agent import Location
from .road_network import RoadNetworkManager
from .ors_client import get_road_route
from .hazard_polygons import collect_hazard_polygons

logger = logging.getLogger(__name__)


@dataclass
class Route:
    """A planned delivery route."""
    id: str
    origin: Location
    destination: Location
    waypoints: list[tuple] = field(default_factory=list)
    distance_m: float = 0.0
    estimated_duration_min: float = 0.0
    hazards_avoided: list[dict] = field(default_factory=list)
    confidence: float = 1.0
    reasoning: str = ""
    directions: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert route to dictionary."""
        import math

        def sanitize_float(val: float) -> float | None:
            """Replace inf/nan with None for JSON compatibility."""
            if isinstance(val, float) and (math.isinf(val) or math.isnan(val)):
                return None
            return val

        return {
            "id": self.id,
            "origin": self.origin.to_dict(),
            "destination": self.destination.to_dict(),
            "waypoints": [{"lon": w[0], "lat": w[1]} for w in self.waypoints],
            "distance_m": sanitize_float(self.distance_m),
            "estimated_duration_min": sanitize_float(self.estimated_duration_min),
            "hazards_avoided": self.hazards_avoided,
            "confidence": sanitize_float(self.confidence),
            "reasoning": self.reasoning,
            "directions": self.directions,
            "created_at": self.created_at.isoformat(),
        }


class Router:
    """
    Route planner that uses the road network to find optimal paths.

    Considers current road conditions and hazards when planning routes.
    """

    # Average speeds for different conditions (km/h)
    SPEED_NORMAL = 50.0
    SPEED_DAMAGED = 20.0
    SPEED_URBAN = 30.0

    def __init__(self, network: RoadNetworkManager, events_data: list[dict] | None = None):
        """
        Initialize router with road network.

        Args:
            network: RoadNetworkManager instance with loaded road data
            events_data: Raw event dicts (from helene_timeline.json) for hazard polygon extraction
        """
        self.network = network
        self._route_counter = 0
        self._events_data = events_data or []

    def set_events_data(self, events_data: list[dict]) -> None:
        """Update the raw events data used for hazard polygon collection."""
        self._events_data = events_data

    def plan_route(
        self,
        origin: Location,
        destination: Location,
        avoid_hazards: bool = True,
    ) -> Route | None:
        """
        Plan optimal route from origin to destination.

        Args:
            origin: Starting location
            destination: End location
            avoid_hazards: Whether to avoid known hazards

        Returns:
            Route object or None if no path exists
        """
        # Find route using network
        result = self.network.find_route(origin, destination)

        if result is None:
            return self._plan_direct_route(origin, destination)

        node_path, total_weight, detailed_geometry = result

        # Generate route ID
        self._route_counter += 1
        route_id = f"route-{self._route_counter:04d}"

        # Use node_path for edge-level analysis (hazards, confidence)
        hazards_avoided = self._get_avoided_hazards(node_path)
        reasoning = self._build_reasoning(node_path, hazards_avoided)

        # Try ORS for real road geometry with hazard avoidance
        # Only pass origin + destination — ORS finds its own road path,
        # and avoid_polygons ensures it routes around hazard zones.
        endpoints = [(origin.lon, origin.lat), (destination.lon, destination.lat)]
        avoid_polygons = collect_hazard_polygons(
            self._events_data, route_endpoints=endpoints,
        ) if self._events_data else None
        ors_result = get_road_route(endpoints, avoid_polygons=avoid_polygons)

        if ors_result:
            waypoints = ors_result["coordinates"]
            distance_m = ors_result["distance_m"]
            duration_min = ors_result["duration_s"] / 60.0
            directions = ors_result["steps"]
            logger.info("ORS route: %.1f km, %.0f min, %d waypoints",
                        distance_m / 1000, duration_min, len(waypoints))
        else:
            # Fallback to graph geometry
            waypoints = detailed_geometry
            distance_m = self._calculate_path_distance(node_path)
            duration_min = self._estimate_duration(node_path, distance_m)
            directions = []

        return Route(
            id=route_id,
            origin=origin,
            destination=destination,
            waypoints=waypoints,
            distance_m=distance_m,
            estimated_duration_min=duration_min,
            hazards_avoided=hazards_avoided,
            confidence=self._calculate_route_confidence(node_path),
            reasoning=reasoning,
            directions=directions,
        )

    def plan_multi_stop_route(
        self,
        origin: Location,
        destinations: list[Location],
        optimize_order: bool = True,
    ) -> list[Route] | None:
        """
        Plan routes to multiple destinations.

        Args:
            origin: Starting location
            destinations: List of destinations to visit
            optimize_order: Whether to optimize visit order

        Returns:
            List of Route objects for each leg, or None if any leg fails
        """
        if optimize_order:
            destinations = self._optimize_destination_order(origin, destinations)

        routes = []
        current = origin

        for dest in destinations:
            route = self.plan_route(current, dest)
            if route is None:
                return None  # Can't reach this destination
            routes.append(route)
            current = dest

        return routes

    def find_alternative_routes(
        self,
        origin: Location,
        destination: Location,
        num_alternatives: int = 3,
    ) -> list[Route]:
        """
        Find multiple alternative routes.

        Uses k-shortest paths algorithm to find alternatives.

        Args:
            origin: Starting location
            destination: End location
            num_alternatives: Number of alternatives to find

        Returns:
            List of Route objects, ordered by preference
        """
        # For now, just return the single best route
        # TODO: Implement k-shortest paths
        primary = self.plan_route(origin, destination)
        if primary:
            return [primary]
        return []

    def _calculate_path_distance(self, path: list[tuple]) -> float:
        """Calculate total distance of a path in meters."""
        total = 0.0
        for i in range(len(path) - 1):
            if self.network.graph.has_edge(path[i], path[i + 1]):
                edge_data = self.network.graph.edges[path[i], path[i + 1]]
                total += edge_data.get("length", 100)
        return total

    def _estimate_duration(self, path: list[tuple], distance_m: float) -> float:
        """Estimate travel duration in minutes."""
        # Base estimate using average speed
        avg_speed_mps = self.SPEED_NORMAL * 1000 / 60  # Convert km/h to m/min

        # Adjust for damaged segments
        damaged_segments = 0
        for i in range(len(path) - 1):
            edge = (path[i], path[i + 1])
            if edge in self.network.edge_status:
                if self.network.edge_status[edge].status == "damaged":
                    damaged_segments += 1

        # Reduce average speed based on damaged segments
        damage_ratio = damaged_segments / max(1, len(path) - 1)
        adjusted_speed = avg_speed_mps * (1 - 0.5 * damage_ratio)

        return distance_m / adjusted_speed if adjusted_speed > 0 else float("inf")

    def _get_avoided_hazards(self, path: list[tuple]) -> list[dict]:
        """Get list of hazards that the route avoids."""
        avoided = []

        # Check for nearby blocked edges that aren't in the path
        path_edges = set(zip(path[:-1], path[1:]))

        for edge, status in self.network.edge_status.items():
            if status.status == "closed" and edge not in path_edges:
                # Check if this edge is near the path
                edge_data = self.network.graph.edges.get(edge, {})
                avoided.append({
                    "type": "road_closure",
                    "location": {
                        "lon": (edge[0][0] + edge[1][0]) / 2,
                        "lat": (edge[0][1] + edge[1][1]) / 2,
                    },
                    "name": edge_data.get("name", "Unknown road"),
                    "confidence": status.confidence,
                })

        return avoided[:5]  # Limit to top 5 hazards

    def _calculate_route_confidence(self, path: list[tuple]) -> float:
        """Calculate overall confidence in the route."""
        if not path:
            return 0.0

        # Start with high confidence
        confidence = 1.0

        # Reduce based on damaged segments
        for i in range(len(path) - 1):
            edge = (path[i], path[i + 1])
            if edge in self.network.edge_status:
                status = self.network.edge_status[edge]
                if status.status == "damaged":
                    # Reduce confidence based on damage
                    confidence *= 0.9
                elif status.status == "closed":
                    # Should not happen if routing works correctly
                    confidence = 0.0

        return max(0.0, min(1.0, confidence))

    def _build_reasoning(self, path: list[tuple], hazards: list[dict]) -> str:
        """Build human-readable reasoning for route choice."""
        parts = []

        if hazards:
            hazard_names = [h.get("name", "hazard") for h in hazards[:3]]
            parts.append(f"Avoiding {len(hazards)} hazards including: {', '.join(hazard_names)}")

        # Check for damaged segments on route
        damaged = 0
        for i in range(len(path) - 1):
            edge = (path[i], path[i + 1])
            if edge in self.network.edge_status:
                if self.network.edge_status[edge].status == "damaged":
                    damaged += 1

        if damaged > 0:
            parts.append(f"Route includes {damaged} damaged but passable road segment(s)")
        else:
            parts.append("All segments on route are clear")

        return ". ".join(parts) + "."

    def _plan_direct_route(
        self,
        origin: Location,
        destination: Location,
    ) -> Route:
        """
        Create a fallback route when graph routing fails.

        Tries OSRM for real road geometry first, falls back to
        haversine straight-line with lower confidence.
        """
        self._route_counter += 1
        route_id = f"route-{self._route_counter:04d}"

        # Try ORS for real road geometry even without graph path
        endpoints = [(origin.lon, origin.lat), (destination.lon, destination.lat)]
        avoid_polygons = collect_hazard_polygons(
            self._events_data, route_endpoints=endpoints,
        ) if self._events_data else None
        ors_result = get_road_route(endpoints, avoid_polygons=avoid_polygons)

        if ors_result:
            return Route(
                id=route_id,
                origin=origin,
                destination=destination,
                waypoints=ors_result["coordinates"],
                distance_m=ors_result["distance_m"],
                estimated_duration_min=ors_result["duration_s"] / 60.0,
                hazards_avoided=[],
                confidence=0.7,
                reasoning="Route via ORS (road conditions not verified in hazard graph). Use caution.",
                directions=ors_result["steps"],
            )

        # Final fallback: straight-line haversine
        distance_m = self._haversine_distance(
            origin.lat, origin.lon, destination.lat, destination.lon
        )
        duration_min = (distance_m / 1000) / self.SPEED_URBAN * 60

        return Route(
            id=route_id,
            origin=origin,
            destination=destination,
            waypoints=[(origin.lon, origin.lat), (destination.lon, destination.lat)],
            distance_m=distance_m,
            estimated_duration_min=duration_min,
            hazards_avoided=[],
            confidence=0.5,
            reasoning="Direct-distance estimate (no road data available). Actual route may differ.",
        )

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate haversine distance between two points in meters."""
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _optimize_destination_order(
        self,
        origin: Location,
        destinations: list[Location],
    ) -> list[Location]:
        """
        Optimize order of destinations using nearest neighbor heuristic.

        Simple greedy algorithm - visit nearest unvisited destination.
        For production, would use proper TSP solver.
        """
        if len(destinations) <= 1:
            return destinations

        remaining = list(destinations)
        ordered = []
        current = origin

        while remaining:
            # Find nearest remaining destination
            nearest = min(
                remaining,
                key=lambda d: (
                    (d.lat - current.lat) ** 2 + (d.lon - current.lon) ** 2
                ) ** 0.5,
            )
            ordered.append(nearest)
            remaining.remove(nearest)
            current = nearest

        return ordered
