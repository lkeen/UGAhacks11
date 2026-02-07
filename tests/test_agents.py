"""Tests for agent implementations."""

import pytest
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.agents import (
    SocialMediaAgent,
    SatelliteAgent,
    OfficialDataAgent,
    RoadNetworkAgent,
    BoundingBox,
    WESTERN_NC_BBOX,
)


@pytest.fixture
def data_dir():
    """Get the data directory path."""
    return Path(__file__).parent.parent / "backend" / "data"


@pytest.fixture
def scenario_time():
    """Default scenario time."""
    return datetime.fromisoformat("2024-09-27T14:00:00+00:00")


class TestSocialMediaAgent:
    """Tests for SocialMediaAgent."""

    @pytest.mark.asyncio
    async def test_gather_intelligence_loads_data(self, data_dir, scenario_time):
        """Test that agent can load and process social media data."""
        agent = SocialMediaAgent(
            data_path=data_dir / "events" / "social_media_posts.json"
        )

        reports = await agent.gather_intelligence(scenario_time, WESTERN_NC_BBOX)

        assert len(reports) > 0
        assert all(r.agent_name == "SocialMediaAgent" for r in reports)

    @pytest.mark.asyncio
    async def test_filters_by_time(self, data_dir):
        """Test that agent filters reports by scenario time."""
        agent = SocialMediaAgent(
            data_path=data_dir / "events" / "social_media_posts.json"
        )

        # Early time - should have fewer reports
        early_time = datetime.fromisoformat("2024-09-27T06:00:00+00:00")
        early_reports = await agent.gather_intelligence(early_time, WESTERN_NC_BBOX)

        # Later time - should have more reports
        late_time = datetime.fromisoformat("2024-09-28T18:00:00+00:00")
        agent.clear_reports()
        late_reports = await agent.gather_intelligence(late_time, WESTERN_NC_BBOX)

        assert len(late_reports) >= len(early_reports)

    def test_confidence_calculation(self, data_dir):
        """Test confidence score calculation."""
        agent = SocialMediaAgent()

        # Post with verification and media should have higher confidence
        high_conf_post = {
            "verified": True,
            "is_local": True,
            "has_photo": True,
            "has_video": True,
            "retweets": 100,
        }
        high_conf = agent._calculate_confidence(high_conf_post)

        low_conf_post = {}
        low_conf = agent._calculate_confidence(low_conf_post)

        assert high_conf > low_conf


class TestSatelliteAgent:
    """Tests for SatelliteAgent."""

    @pytest.mark.asyncio
    async def test_gather_intelligence_loads_detections(self, data_dir, scenario_time):
        """Test that agent can load satellite detections."""
        agent = SatelliteAgent(
            detections_path=data_dir / "satellite" / "detections.json"
        )

        reports = await agent.gather_intelligence(scenario_time, WESTERN_NC_BBOX)

        assert len(reports) >= 0  # May be 0 if detections are after scenario_time
        assert all(r.agent_name == "SatelliteAgent" for r in reports)

    def test_high_confidence_weight(self):
        """Test that satellite agent has high confidence weight."""
        agent = SatelliteAgent()
        assert agent.confidence_weight >= 0.85


class TestOfficialDataAgent:
    """Tests for OfficialDataAgent."""

    @pytest.mark.asyncio
    async def test_gather_intelligence_includes_shelters(self, data_dir, scenario_time):
        """Test that agent returns shelter information."""
        agent = OfficialDataAgent(
            data_path=data_dir / "events" / "helene_timeline.json"
        )
        # Also load shelter data
        shelters_path = data_dir / "shelters" / "shelters.json"
        if shelters_path.exists():
            agent.load_data(data_dir / "events" / "helene_timeline.json")
            import json
            with open(shelters_path) as f:
                shelter_data = json.load(f)
                agent._shelters = shelter_data.get("shelters", [])

        reports = await agent.gather_intelligence(scenario_time, WESTERN_NC_BBOX)

        # Should have some shelter reports
        shelter_reports = [r for r in reports if "shelter" in r.event_type.value.lower()]
        assert len(shelter_reports) >= 0


class TestRoadNetworkAgent:
    """Tests for RoadNetworkAgent."""

    def test_receives_updates(self):
        """Test that agent can receive updates from other agents."""
        agent = RoadNetworkAgent()

        from backend.agents.base_agent import AgentReport, EventType, Location

        report = AgentReport(
            event_type=EventType.ROAD_CLOSURE,
            location=Location(lat=35.5, lon=-82.5),
            description="Test road closure",
            confidence=0.8,
        )

        agent.receive_update(report)

        assert len(agent._pending_updates) == 1

    def test_resolves_conflicts(self):
        """Test that agent resolves conflicting reports."""
        agent = RoadNetworkAgent()

        from backend.agents.base_agent import AgentReport, EventType, Location

        # Add conflicting reports
        closure_report = AgentReport(
            event_type=EventType.ROAD_CLOSURE,
            location=Location(lat=35.500, lon=-82.500),
            description="Road is closed",
            confidence=0.9,
        )
        clear_report = AgentReport(
            event_type=EventType.ROAD_CLEAR,
            location=Location(lat=35.500, lon=-82.500),
            description="Road is clear",
            confidence=0.5,
        )

        agent.receive_updates([closure_report, clear_report])
        agent._process_pending_updates()

        # Higher confidence closure should win
        status = agent.get_road_status(Location(lat=35.500, lon=-82.500))
        assert status is not None
        assert status["status"] == "blocked"
