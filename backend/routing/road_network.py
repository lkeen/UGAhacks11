"""Road network manager using NetworkX for graph operations."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import networkx as nx

from backend.agents.base_agent import AgentReport, EventType, Location


@dataclass
class EdgeStatus:
    """Status information for a road segment."""
    weight_multiplier: float = 1.0
    status: str = "open"  # open, damaged, closed
    confidence: float = 1.0
    last_update: datetime | None = None
    reports: list[str] = None  # List of report IDs

    def __post_init__(self):
        if self.reports is None:
            self.reports = []


class RoadNetworkManager:
    """
    Manages the road network graph with dynamic edge weights.

    Uses NetworkX for graph operations. Edges can be updated based
    on agent reports about road conditions.
    """

    # How event types affect road weights
    EVENT_WEIGHT_IMPACT = {
        EventType.ROAD_CLOSURE: float("inf"),
        EventType.BRIDGE_COLLAPSE: float("inf"),
        EventType.ROAD_DAMAGE: 3.0,
        EventType.FLOODING: 5.0,
        EventType.ROAD_CLEAR: 1.0,
    }

    def __init__(self):
        """Initialize empty road network."""
        self.graph: nx.DiGraph = nx.DiGraph()
        self.edge_status: dict[tuple, EdgeStatus] = {}
        self._osm_data_loaded = False

    def load_from_geojson(self, filepath: str | Path) -> None:
        """
        Load road network from GeoJSON file.

        Expected format from OSMnx export.

        Args:
            filepath: Path to GeoJSON file
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"GeoJSON file not found: {filepath}")

        with open(filepath) as f:
            data = json.load(f)

        # Parse features into graph
        for feature in data.get("features", []):
            if feature["geometry"]["type"] == "LineString":
                props = feature["properties"]
                coords = feature["geometry"]["coordinates"]

                # Use first and last coordinate as nodes
                start = tuple(coords[0][:2])  # (lon, lat)
                end = tuple(coords[-1][:2])

                # Add nodes
                self.graph.add_node(start, lon=start[0], lat=start[1])
                self.graph.add_node(end, lon=end[0], lat=end[1])

                # Calculate length from coordinates if not provided
                length = props.get("length", self._calculate_length(coords))

                # Add edge
                self.graph.add_edge(
                    start,
                    end,
                    osm_id=props.get("osmid"),
                    name=props.get("name"),
                    highway=props.get("highway"),
                    length=length,
                    geometry=coords,
                    base_weight=length,
                    weight=length,  # Dynamic weight
                )

                # Initialize edge status
                self.edge_status[(start, end)] = EdgeStatus()

        self._osm_data_loaded = True

    def load_from_osmnx(self, graph: nx.MultiDiGraph) -> None:
        """
        Load road network directly from OSMnx graph.

        Args:
            graph: NetworkX graph from osmnx.graph_from_place() or similar
        """
        # Convert OSMnx MultiDiGraph to simple DiGraph
        for u, v, data in graph.edges(data=True):
            # Get node coordinates
            start = (graph.nodes[u].get("x", 0), graph.nodes[u].get("y", 0))
            end = (graph.nodes[v].get("x", 0), graph.nodes[v].get("y", 0))

            # Add nodes with coordinates
            self.graph.add_node(
                start,
                lon=start[0],
                lat=start[1],
                osm_id=u,
            )
            self.graph.add_node(
                end,
                lon=end[0],
                lat=end[1],
                osm_id=v,
            )

            # Get edge length
            length = data.get("length", 100)

            # Add edge
            self.graph.add_edge(
                start,
                end,
                osm_id=data.get("osmid"),
                name=data.get("name"),
                highway=data.get("highway"),
                length=length,
                base_weight=length,
                weight=length,
            )

            # Initialize edge status
            self.edge_status[(start, end)] = EdgeStatus()

        self._osm_data_loaded = True

    def update_edge_weight(
        self,
        start: tuple,
        end: tuple,
        multiplier: float,
        confidence: float = 1.0,
        report_id: str | None = None,
    ) -> bool:
        """
        Update the weight of an edge based on conditions.

        Args:
            start: Start node (lon, lat)
            end: End node (lon, lat)
            multiplier: Weight multiplier (1.0 = normal, inf = blocked)
            confidence: Confidence in this update
            report_id: Optional report ID for tracking

        Returns:
            True if edge was updated, False if edge not found
        """
        if not self.graph.has_edge(start, end):
            return False

        edge_data = self.graph.edges[start, end]
        base_weight = edge_data.get("base_weight", edge_data.get("length", 100))

        # Calculate new weight
        if multiplier == float("inf"):
            new_weight = float("inf")
            status = "closed"
        elif multiplier > 1.0:
            new_weight = base_weight * multiplier
            status = "damaged"
        else:
            new_weight = base_weight
            status = "open"

        # Update edge
        edge_data["weight"] = new_weight

        # Update status tracking
        edge_status = self.edge_status.get((start, end), EdgeStatus())
        edge_status.weight_multiplier = multiplier
        edge_status.status = status
        edge_status.confidence = confidence
        edge_status.last_update = datetime.utcnow()
        if report_id:
            edge_status.reports.append(report_id)
        self.edge_status[(start, end)] = edge_status

        return True

    def update_edge_weight_by_location(
        self,
        location: Location,
        multiplier: float,
        confidence: float = 1.0,
        radius_deg: float = 0.001,  # ~100m
    ) -> int:
        """
        Update edges near a location.

        Args:
            location: Location to search near
            multiplier: Weight multiplier
            confidence: Confidence in this update
            radius_deg: Search radius in degrees

        Returns:
            Number of edges updated
        """
        updated = 0

        for start, end in self.graph.edges():
            # Check if edge is near location
            mid_lon = (start[0] + end[0]) / 2
            mid_lat = (start[1] + end[1]) / 2

            if (
                abs(mid_lon - location.lon) <= radius_deg
                and abs(mid_lat - location.lat) <= radius_deg
            ):
                if self.update_edge_weight(start, end, multiplier, confidence):
                    updated += 1

        return updated

    def apply_agent_report(self, report: AgentReport) -> int:
        """
        Apply an agent report to update road network.

        Args:
            report: AgentReport from any agent

        Returns:
            Number of edges updated
        """
        if report.event_type not in self.EVENT_WEIGHT_IMPACT:
            return 0

        multiplier = self.EVENT_WEIGHT_IMPACT[report.event_type]
        return self.update_edge_weight_by_location(
            report.location,
            multiplier,
            report.confidence,
        )

    def apply_agent_reports(self, reports: list[AgentReport]) -> int:
        """Apply multiple agent reports."""
        total_updated = 0
        for report in reports:
            total_updated += self.apply_agent_report(report)
        return total_updated

    def get_nearest_node(self, location: Location) -> tuple | None:
        """
        Find the nearest node to a location.

        Args:
            location: Target location

        Returns:
            Node tuple (lon, lat) or None if graph is empty
        """
        if not self.graph.nodes():
            return None

        min_dist = float("inf")
        nearest = None

        for node in self.graph.nodes():
            dist = (
                (node[0] - location.lon) ** 2 + (node[1] - location.lat) ** 2
            ) ** 0.5
            if dist < min_dist:
                min_dist = dist
                nearest = node

        return nearest

    def find_route(
        self,
        start: Location,
        end: Location,
        avoid_risk_level: float = 0.5,
    ) -> tuple[list[tuple], float] | None:
        """
        Find optimal route between two locations.

        Args:
            start: Start location
            end: End location
            avoid_risk_level: Avoid edges with confidence below this (0-1)

        Returns:
            Tuple of (path as list of nodes, total weight) or None if no path
        """
        start_node = self.get_nearest_node(start)
        end_node = self.get_nearest_node(end)

        if start_node is None or end_node is None:
            return None

        try:
            # Use Dijkstra's algorithm with current weights
            path = nx.dijkstra_path(self.graph, start_node, end_node, weight="weight")
            total_weight = nx.dijkstra_path_length(
                self.graph, start_node, end_node, weight="weight"
            )

            return path, total_weight
        except nx.NetworkXNoPath:
            return None

    def get_blocked_edges(self) -> list[dict]:
        """Get all edges currently marked as blocked."""
        blocked = []
        for (start, end), status in self.edge_status.items():
            if status.status == "closed":
                edge_data = self.graph.edges.get((start, end), {})
                blocked.append({
                    "start": {"lon": start[0], "lat": start[1]},
                    "end": {"lon": end[0], "lat": end[1]},
                    "name": edge_data.get("name"),
                    "highway": edge_data.get("highway"),
                    "confidence": status.confidence,
                    "last_update": status.last_update.isoformat() if status.last_update else None,
                })
        return blocked

    def get_damaged_edges(self) -> list[dict]:
        """Get all edges with damage (slow but passable)."""
        damaged = []
        for (start, end), status in self.edge_status.items():
            if status.status == "damaged":
                edge_data = self.graph.edges.get((start, end), {})
                damaged.append({
                    "start": {"lon": start[0], "lat": start[1]},
                    "end": {"lon": end[0], "lat": end[1]},
                    "name": edge_data.get("name"),
                    "highway": edge_data.get("highway"),
                    "weight_multiplier": status.weight_multiplier,
                    "confidence": status.confidence,
                })
        return damaged

    def get_network_stats(self) -> dict:
        """Get statistics about the road network."""
        blocked = sum(1 for s in self.edge_status.values() if s.status == "closed")
        damaged = sum(1 for s in self.edge_status.values() if s.status == "damaged")

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "blocked_edges": blocked,
            "damaged_edges": damaged,
            "open_edges": self.graph.number_of_edges() - blocked - damaged,
            "osm_loaded": self._osm_data_loaded,
        }

    def reset_all_weights(self) -> None:
        """Reset all edge weights to base values."""
        for start, end, data in self.graph.edges(data=True):
            data["weight"] = data.get("base_weight", data.get("length", 100))
            if (start, end) in self.edge_status:
                self.edge_status[(start, end)] = EdgeStatus()

    def _calculate_length(self, coords: list) -> float:
        """Calculate approximate length of a coordinate path in meters."""
        total = 0.0
        for i in range(len(coords) - 1):
            # Simple Euclidean distance in degrees, convert to approximate meters
            dx = coords[i + 1][0] - coords[i][0]
            dy = coords[i + 1][1] - coords[i][1]
            # Approximate conversion at ~35° latitude
            meters_per_deg_lon = 90000
            meters_per_deg_lat = 111000
            total += ((dx * meters_per_deg_lon) ** 2 + (dy * meters_per_deg_lat) ** 2) ** 0.5
        return total
