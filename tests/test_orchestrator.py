"""Tests for the orchestrator with Claude API integration."""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.agents.base_agent import (
    AgentReport,
    BoundingBox,
    DataSource,
    EventType,
    Location,
    WESTERN_NC_BBOX,
)
from backend.orchestrator import Orchestrator
from backend.utils.report_aggregator import (
    calculate_consensus_confidence,
    group_reports_by_location,
    identify_conflicting_reports,
)


@pytest.fixture
def data_dir():
    return Path(__file__).parent.parent / "backend" / "data"


@pytest.fixture
def scenario_time():
    return datetime.fromisoformat("2024-09-27T14:00:00+00:00")


@pytest.fixture
def orchestrator(data_dir):
    """Create an orchestrator without Claude client for deterministic tests."""
    orch = Orchestrator(anthropic_api_key="", data_dir=data_dir)
    orch.client = None  # Ensure fallback paths are used
    return orch


# ------------------------------------------------------------------
# Intelligence gathering tests
# ------------------------------------------------------------------


class TestIntelligenceGathering:
    @pytest.mark.asyncio
    async def test_gather_all_intelligence(self, orchestrator, scenario_time):
        """Gathering intelligence returns reports from all agents."""
        orchestrator.set_scenario_time(scenario_time)
        intelligence = await orchestrator.gather_all_intelligence()

        assert "satellite" in intelligence
        assert "social_media" in intelligence
        assert "official" in intelligence
        assert "road_network" in intelligence

    @pytest.mark.asyncio
    async def test_apply_intelligence_to_network(self, orchestrator, scenario_time):
        """Applying intelligence should update road network edges."""
        orchestrator.set_scenario_time(scenario_time)
        await orchestrator.gather_all_intelligence()
        updated = orchestrator.apply_intelligence_to_network()
        # updated may be 0 if no reports match road edges, that's fine
        assert isinstance(updated, int)
        assert updated >= 0


# ------------------------------------------------------------------
# Query parsing tests
# ------------------------------------------------------------------


class TestQueryParsing:
    def test_fallback_parse_water(self, orchestrator):
        """Fallback parser extracts water supply quantities."""
        result = orchestrator._parse_query("I have 200 water cases at Asheville airport")
        assert result["supplies"].get("water_cases") == 200
        assert result["parsed_by"] == "keyword"

    def test_fallback_parse_blankets(self, orchestrator):
        """Fallback parser extracts blanket quantities."""
        result = orchestrator._parse_query("We have 50 blankets in Hendersonville")
        assert result["supplies"].get("blankets") == 50

    def test_fallback_parse_origin_asheville(self, orchestrator):
        """Fallback parser recognizes Asheville as origin."""
        result = orchestrator._parse_query("200 water at Asheville")
        assert result["origin"].address == "Asheville, NC"

    def test_fallback_parse_origin_airport(self, orchestrator):
        """Fallback parser recognizes Asheville airport."""
        result = orchestrator._parse_query("200 water at Asheville airport")
        assert "Airport" in result["origin"].address

    def test_fallback_parse_urgency(self, orchestrator):
        """Fallback parser detects urgency keywords."""
        result = orchestrator._parse_query("urgent: 100 water at Asheville")
        assert result["urgency"] == "critical"

    def test_fallback_default_origin(self, orchestrator):
        """Fallback parser provides default origin when none specified."""
        result = orchestrator._parse_query("I have 100 water cases")
        assert result["origin"] is not None

    def test_claude_parse_mocked(self, orchestrator):
        """Claude parsing returns structured result when API is mocked."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "intent": "route_supplies",
                        "supplies": {"water_cases": 200},
                        "origin_description": "Asheville Regional Airport",
                        "origin_lat": 35.4363,
                        "origin_lon": -82.5418,
                        "urgency": "high",
                        "constraints": [],
                    }
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        orchestrator.client = mock_client

        result = orchestrator._parse_query(
            "I have 200 water cases at Asheville airport, need to deliver fast"
        )
        assert result["supplies"]["water_cases"] == 200
        assert result["parsed_by"] == "claude"
        assert result["urgency"] == "high"

    def test_claude_parse_falls_back_on_error(self, orchestrator):
        """If Claude API raises, parsing falls back to keyword."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API down")
        orchestrator.client = mock_client

        result = orchestrator._parse_query("I have 100 water at Asheville")
        assert result["parsed_by"] == "keyword"
        assert result["supplies"]["water_cases"] == 100


# ------------------------------------------------------------------
# Conflict resolution tests
# ------------------------------------------------------------------


class TestConflictResolution:
    def _make_report(self, event_type, confidence, agent_name="test", lat=35.5, lon=-82.5):
        return AgentReport(
            event_type=event_type,
            location=Location(lat=lat, lon=lon),
            description=f"{event_type.value} report",
            confidence=confidence,
            agent_name=agent_name,
            source=DataSource.CITIZEN_REPORT,
        )

    def test_fallback_picks_highest_confidence(self, orchestrator):
        """Fallback resolver picks the highest-confidence report."""
        reports = [
            self._make_report(EventType.ROAD_CLOSURE, 0.9, "satellite"),
            self._make_report(EventType.ROAD_CLEAR, 0.5, "social_media"),
        ]
        result = orchestrator.resolve_conflicting_reports(reports, "I-40 at exit 55")
        assert result["resolved_status"] == "blocked"
        assert result["confidence"] == 0.9
        assert result["resolved_by"] == "fallback"

    def test_fallback_clear_wins_when_higher_confidence(self, orchestrator):
        """If ROAD_CLEAR has higher confidence, it wins."""
        reports = [
            self._make_report(EventType.ROAD_CLOSURE, 0.3),
            self._make_report(EventType.ROAD_CLEAR, 0.95),
        ]
        result = orchestrator.resolve_conflicting_reports(reports, "US-25")
        assert result["resolved_status"] == "clear"

    def test_fallback_empty_reports(self, orchestrator):
        """Empty reports returns unknown."""
        result = orchestrator.resolve_conflicting_reports([], "nowhere")
        assert result["resolved_status"] == "unknown"

    def test_claude_resolution_mocked(self, orchestrator):
        """Claude conflict resolution returns structured result when mocked."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "resolved_status": "blocked",
                        "confidence": 0.85,
                        "reasoning": "Satellite data is more reliable than a single social media post.",
                    }
                )
            )
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        orchestrator.client = mock_client

        reports = [
            self._make_report(EventType.ROAD_CLOSURE, 0.8, "satellite"),
            self._make_report(EventType.ROAD_CLEAR, 0.6, "social_media"),
        ]
        result = orchestrator.resolve_conflicting_reports(reports, "I-26")
        assert result["resolved_status"] == "blocked"
        assert result["resolved_by"] == "claude"
        assert result["road_id"] == "I-26"


# ------------------------------------------------------------------
# Report aggregation tests
# ------------------------------------------------------------------


class TestReportAggregation:
    def _make_report(self, lat, lon, event_type=EventType.ROAD_CLOSURE, confidence=0.8):
        return AgentReport(
            event_type=event_type,
            location=Location(lat=lat, lon=lon),
            confidence=confidence,
            source=DataSource.SATELLITE,
        )

    def test_group_reports_nearby(self):
        """Reports within proximity are grouped together."""
        reports = [
            self._make_report(35.500, -82.500),
            self._make_report(35.501, -82.501),  # ~0.15 km away
            self._make_report(36.000, -83.000),  # far away
        ]
        clusters = group_reports_by_location(reports, proximity_km=0.5)
        assert len(clusters) == 2
        assert len(clusters[0]) == 2
        assert len(clusters[1]) == 1

    def test_consensus_confidence_single(self):
        """Single report returns its own confidence."""
        reports = [self._make_report(35.5, -82.5, confidence=0.7)]
        assert calculate_consensus_confidence(reports) == 0.7

    def test_consensus_confidence_multiple(self):
        """Multiple reports increase confidence."""
        reports = [
            self._make_report(35.5, -82.5, confidence=0.7),
            self._make_report(35.5, -82.5, confidence=0.8),
        ]
        conf = calculate_consensus_confidence(reports)
        assert conf > 0.75  # Should be higher than average due to bonuses

    def test_consensus_confidence_empty(self):
        """No reports returns 0."""
        assert calculate_consensus_confidence([]) == 0.0

    def test_identify_conflicts(self):
        """Conflicting event types at same location are detected."""
        reports = [
            self._make_report(35.5, -82.5, EventType.ROAD_CLOSURE, 0.9),
            self._make_report(35.5, -82.5, EventType.ROAD_CLEAR, 0.5),
        ]
        conflicts = identify_conflicting_reports(reports, proximity_km=1.0)
        assert len(conflicts) == 1
        assert EventType.ROAD_CLOSURE in conflicts[0]["types"]
        assert EventType.ROAD_CLEAR in conflicts[0]["types"]

    def test_no_conflicts_when_consistent(self):
        """Non-contradicting reports have no conflicts."""
        reports = [
            self._make_report(35.5, -82.5, EventType.ROAD_CLOSURE, 0.9),
            self._make_report(35.5, -82.5, EventType.ROAD_CLOSURE, 0.7),
        ]
        conflicts = identify_conflicting_reports(reports, proximity_km=1.0)
        assert len(conflicts) == 0


# ------------------------------------------------------------------
# End-to-end process_query test
# ------------------------------------------------------------------


class TestProcessQuery:
    @pytest.mark.asyncio
    async def test_process_query_returns_response(self, orchestrator, scenario_time):
        """process_query returns a dict with expected keys."""
        orchestrator.set_scenario_time(scenario_time)
        response = await orchestrator.process_query(
            "I have 200 water cases at Asheville airport"
        )

        assert "query" in response
        assert "scenario_time" in response
        assert "situational_awareness" in response
        assert "delivery_plan" in response
        assert "reasoning" in response
        assert "conflicts_resolved" in response
        assert response["parsed_by"] == "keyword"

    @pytest.mark.asyncio
    async def test_process_query_with_mock_claude(self, orchestrator, scenario_time):
        """process_query works end-to-end with mocked Claude."""
        # Mock parse
        parse_response = MagicMock()
        parse_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "intent": "route_supplies",
                        "supplies": {"water_cases": 200},
                        "origin_description": "Asheville Regional Airport",
                        "origin_lat": 35.4363,
                        "origin_lon": -82.5418,
                        "urgency": "high",
                        "constraints": [],
                    }
                )
            )
        ]

        # Mock reasoning
        reasoning_response = MagicMock()
        reasoning_response.content = [
            MagicMock(text="## Field Briefing\n- Route 200 water cases to priority shelters.")
        ]

        mock_client = MagicMock()
        # First call = parse, subsequent calls = reasoning (and possibly conflict resolution)
        mock_client.messages.create.side_effect = [parse_response, reasoning_response]
        orchestrator.client = mock_client
        orchestrator.set_scenario_time(scenario_time)

        response = await orchestrator.process_query(
            "I have 200 water cases at Asheville airport"
        )

        assert response["parsed_by"] == "claude"
        assert "reasoning" in response
