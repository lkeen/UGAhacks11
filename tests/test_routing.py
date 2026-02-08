"""Tests for routing module."""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.routing import RoadNetworkManager, Router
from backend.agents.base_agent import Location, AgentReport, EventType


class TestRoadNetworkManager:
    """Tests for RoadNetworkManager."""

    @pytest.fixture
    def network(self):
        """Create a simple test network."""
        manager = RoadNetworkManager()

        # Add some nodes and edges manually
        manager.graph.add_node((-82.5, 35.5), lon=-82.5, lat=35.5)
        manager.graph.add_node((-82.4, 35.5), lon=-82.4, lat=35.5)
        manager.graph.add_node((-82.3, 35.5), lon=-82.3, lat=35.5)
        manager.graph.add_node((-82.4, 35.4), lon=-82.4, lat=35.4)

        manager.graph.add_edge(
            (-82.5, 35.5),
            (-82.4, 35.5),
            length=1000,
            base_weight=1000,
            weight=1000,
            name="Test Road 1",
        )
        manager.graph.add_edge(
            (-82.4, 35.5),
            (-82.3, 35.5),
            length=1000,
            base_weight=1000,
            weight=1000,
            name="Test Road 2",
        )
        manager.graph.add_edge(
            (-82.4, 35.5),
            (-82.4, 35.4),
            length=1500,
            base_weight=1500,
            weight=1500,
            name="Test Road 3",
        )

        return manager

    def test_get_nearest_node(self, network):
        """Test finding nearest node to location."""
        location = Location(lat=35.5, lon=-82.45)
        nearest = network.get_nearest_node(location)

        assert nearest is not None
        assert nearest == (-82.4, 35.5) or nearest == (-82.5, 35.5)

    def test_update_edge_weight(self, network):
        """Test updating edge weight."""
        success = network.update_edge_weight(
            (-82.5, 35.5),
            (-82.4, 35.5),
            multiplier=3.0,
            confidence=0.9,
        )

        assert success
        edge_data = network.graph.edges[(-82.5, 35.5), (-82.4, 35.5)]
        assert edge_data["weight"] == 3000  # 1000 * 3.0

    def test_update_edge_weight_blocked(self, network):
        """Test blocking an edge."""
        network.update_edge_weight(
            (-82.5, 35.5),
            (-82.4, 35.5),
            multiplier=float("inf"),
            confidence=0.95,
        )

        edge_data = network.graph.edges[(-82.5, 35.5), (-82.4, 35.5)]
        assert edge_data["weight"] == float("inf")

        blocked = network.get_blocked_edges()
        assert len(blocked) == 1

    def test_apply_agent_report(self, network):
        """Test applying agent report to network."""
        report = AgentReport(
            event_type=EventType.ROAD_CLOSURE,
            location=Location(lat=35.5, lon=-82.45),
            confidence=0.9,
        )

        updated = network.apply_agent_report(report)
        assert updated >= 0

    def test_find_route(self, network):
        """Test finding route between locations."""
        start = Location(lat=35.5, lon=-82.5)
        end = Location(lat=35.5, lon=-82.3)

        result = network.find_route(start, end)

        assert result is not None
        node_path, weight, detailed_path = result
        assert len(node_path) == 3
        assert weight == 2000  # Two edges of 1000 each
        assert len(detailed_path) >= len(node_path)  # Detailed has at least as many points

    def test_find_route_avoids_blocked(self, network):
        """Test that routing avoids blocked edges."""
        # Block the direct route
        network.update_edge_weight(
            (-82.4, 35.5),
            (-82.3, 35.5),
            multiplier=float("inf"),
        )

        start = Location(lat=35.5, lon=-82.5)
        end = Location(lat=35.5, lon=-82.3)

        result = network.find_route(start, end)

        # Should fail since no alternate route exists
        assert result is None

    def test_network_stats(self, network):
        """Test getting network statistics."""
        stats = network.get_network_stats()

        assert stats["total_nodes"] == 4
        assert stats["total_edges"] == 3
        assert stats["blocked_edges"] == 0

    def test_reset_weights(self, network):
        """Test resetting all weights."""
        # First damage some edges
        network.update_edge_weight(
            (-82.5, 35.5),
            (-82.4, 35.5),
            multiplier=5.0,
        )

        # Reset
        network.reset_all_weights()

        edge_data = network.graph.edges[(-82.5, 35.5), (-82.4, 35.5)]
        assert edge_data["weight"] == 1000  # Back to base


class TestRouter:
    """Tests for Router."""

    @pytest.fixture
    def router(self):
        """Create router with test network."""
        network = RoadNetworkManager()

        # Add a simple grid
        for i in range(3):
            for j in range(3):
                lon = -82.5 + i * 0.1
                lat = 35.5 + j * 0.1
                network.graph.add_node((lon, lat), lon=lon, lat=lat)

        # Add horizontal edges
        for i in range(2):
            for j in range(3):
                start = (-82.5 + i * 0.1, 35.5 + j * 0.1)
                end = (-82.5 + (i + 1) * 0.1, 35.5 + j * 0.1)
                network.graph.add_edge(
                    start, end,
                    length=1000,
                    base_weight=1000,
                    weight=1000,
                )

        # Add vertical edges
        for i in range(3):
            for j in range(2):
                start = (-82.5 + i * 0.1, 35.5 + j * 0.1)
                end = (-82.5 + i * 0.1, 35.5 + (j + 1) * 0.1)
                network.graph.add_edge(
                    start, end,
                    length=1000,
                    base_weight=1000,
                    weight=1000,
                )

        return Router(network)

    def test_plan_route(self, router):
        """Test basic route planning."""
        origin = Location(lat=35.5, lon=-82.5)
        dest = Location(lat=35.7, lon=-82.3)

        route = router.plan_route(origin, dest)

        assert route is not None
        assert route.distance_m > 0
        assert route.estimated_duration_min > 0

    def test_route_has_waypoints(self, router):
        """Test that route includes waypoints."""
        origin = Location(lat=35.5, lon=-82.5)
        dest = Location(lat=35.7, lon=-82.3)

        route = router.plan_route(origin, dest)

        assert len(route.waypoints) >= 2

    def test_route_confidence(self, router):
        """Test route confidence calculation."""
        origin = Location(lat=35.5, lon=-82.5)
        dest = Location(lat=35.6, lon=-82.4)

        route = router.plan_route(origin, dest)

        assert 0 <= route.confidence <= 1
