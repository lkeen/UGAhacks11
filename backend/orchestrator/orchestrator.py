"""Orchestrator for multi-agent disaster relief coordination."""

import json
import os
from datetime import datetime
from pathlib import Path

from backend.agents import (
    BaseAgent,
    SatelliteAgent,
    SocialMediaAgent,
    OfficialDataAgent,
    RoadNetworkAgent,
    AgentReport,
    BoundingBox,
    WESTERN_NC_BBOX,
)
from backend.routing import RoadNetworkManager, Router, Route
from backend.agents.base_agent import Location


class Orchestrator:
    """
    Main orchestrator that coordinates multiple agents for disaster relief.

    Uses Claude API (when integrated) to:
    1. Parse user queries about supply routing
    2. Query appropriate agents for situational awareness
    3. Plan optimal delivery routes
    4. Generate human-readable delivery plans with reasoning
    """

    def __init__(
        self,
        anthropic_api_key: str | None = None,
        data_dir: str | Path | None = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            anthropic_api_key: API key for Claude (optional for skeleton)
            data_dir: Directory containing mock data files
        """
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "data"

        # Initialize agents
        self.satellite_agent = SatelliteAgent(
            detections_path=self.data_dir / "satellite" / "detections.json"
        )
        self.social_media_agent = SocialMediaAgent(
            data_path=self.data_dir / "events" / "social_media_posts.json"
        )
        self.official_data_agent = OfficialDataAgent(
            data_path=self.data_dir / "events" / "helene_timeline.json"
        )
        # Also load shelter data into official agent
        shelters_path = self.data_dir / "shelters" / "shelters.json"
        if shelters_path.exists():
            import json
            with open(shelters_path) as f:
                shelter_data = json.load(f)
                self.official_data_agent._shelters = shelter_data.get("shelters", [])

        # Initialize road network
        self.road_network = RoadNetworkManager()
        self.road_network_agent = RoadNetworkAgent(
            road_network_manager=self.road_network
        )

        # Initialize router
        self.router = Router(self.road_network)

        # Scenario state
        self.scenario_time: datetime = datetime.fromisoformat("2024-09-27T12:00:00+00:00")
        self.bbox: BoundingBox = WESTERN_NC_BBOX

        # Agent outputs cache
        self._last_intelligence: dict[str, list[AgentReport]] = {}

    async def gather_all_intelligence(self) -> dict[str, list[AgentReport]]:
        """
        Query all agents to build situational awareness.

        Returns:
            Dict mapping agent names to their reports
        """
        intelligence = {}

        # Gather from each agent
        intelligence["satellite"] = await self.satellite_agent.gather_intelligence(
            self.scenario_time, self.bbox
        )
        intelligence["social_media"] = await self.social_media_agent.gather_intelligence(
            self.scenario_time, self.bbox
        )
        intelligence["official"] = await self.official_data_agent.gather_intelligence(
            self.scenario_time, self.bbox
        )

        # Apply reports to road network
        all_reports = []
        for reports in intelligence.values():
            all_reports.extend(reports)

        # Update road network agent with all reports
        self.road_network_agent.receive_updates(all_reports)

        # Gather road network's aggregated view
        intelligence["road_network"] = await self.road_network_agent.gather_intelligence(
            self.scenario_time, self.bbox
        )

        self._last_intelligence = intelligence
        return intelligence

    def apply_intelligence_to_network(self) -> int:
        """
        Apply gathered intelligence to update road network weights.

        Returns:
            Number of edges updated
        """
        total_updated = 0

        for agent_name, reports in self._last_intelligence.items():
            for report in reports:
                updated = self.road_network.apply_agent_report(report)
                total_updated += updated

        return total_updated

    async def process_query(self, query: str) -> dict:
        """
        Process a natural language query about supply routing.

        This is the main entry point for user queries.

        Args:
            query: User query like "I have 200 water cases at Asheville depot, where should they go?"

        Returns:
            Dict with delivery plan and reasoning
        """
        # Step 1: Gather intelligence
        intelligence = await self.gather_all_intelligence()

        # Step 2: Apply to road network
        edges_updated = self.apply_intelligence_to_network()

        # Step 3: Parse query (placeholder for Claude integration)
        parsed = self._parse_query(query)

        # Step 4: Get shelter needs
        shelters = self._get_priority_shelters()

        # Step 5: Plan routes
        routes = self._plan_delivery_routes(parsed, shelters)

        # Step 6: Generate response
        response = self._generate_response(parsed, routes, intelligence)

        return response

    def _parse_query(self, query: str) -> dict:
        """
        Parse user query to extract intent and parameters.

        TODO: Replace with Claude API call for intelligent parsing.
        """
        # Simple keyword-based parsing for skeleton
        parsed = {
            "intent": "route_supplies",
            "supplies": {},
            "origin": None,
            "raw_query": query,
        }

        query_lower = query.lower()

        # Extract supply types and quantities
        if "water" in query_lower:
            # Look for number before "water"
            import re
            match = re.search(r"(\d+)\s*(?:cases?\s+of\s+)?water", query_lower)
            if match:
                parsed["supplies"]["water_cases"] = int(match.group(1))

        if "blanket" in query_lower:
            import re
            match = re.search(r"(\d+)\s*blanket", query_lower)
            if match:
                parsed["supplies"]["blankets"] = int(match.group(1))

        # Extract origin
        if "asheville" in query_lower:
            parsed["origin"] = Location(lat=35.5951, lon=-82.5515, address="Asheville, NC")
        elif "hendersonville" in query_lower:
            parsed["origin"] = Location(lat=35.4368, lon=-82.4573, address="Hendersonville, NC")
        elif "airport" in query_lower:
            parsed["origin"] = Location(lat=35.4363, lon=-82.5418, address="Asheville Regional Airport")

        # Default origin if not found
        if parsed["origin"] is None:
            parsed["origin"] = Location(lat=35.4363, lon=-82.5418, address="Asheville Regional Airport")

        return parsed

    def _get_priority_shelters(self) -> list[dict]:
        """Get shelters prioritized by urgency of needs."""
        # Load shelters from data
        shelters_path = self.data_dir / "shelters" / "shelters.json"
        if not shelters_path.exists():
            return []

        with open(shelters_path) as f:
            data = json.load(f)

        shelters = data.get("shelters", [])

        # Filter to open shelters with needs
        active = [
            s for s in shelters
            if s.get("opened_at") and s.get("needs")
        ]

        # Sort by occupancy ratio (fuller = more urgent)
        active.sort(
            key=lambda s: s.get("current_occupancy", 0) / max(s.get("capacity", 1), 1),
            reverse=True,
        )

        return active

    def _plan_delivery_routes(
        self,
        parsed_query: dict,
        shelters: list[dict],
    ) -> list[Route]:
        """
        Plan delivery routes to shelters based on parsed query.

        Args:
            parsed_query: Parsed user query
            shelters: List of shelters to consider

        Returns:
            List of planned routes
        """
        routes = []
        origin = parsed_query.get("origin")

        if origin is None:
            return routes

        # Match supplies to shelter needs
        supplies = parsed_query.get("supplies", {})

        for shelter in shelters[:3]:  # Top 3 priority shelters
            shelter_needs = set(shelter.get("needs", []))
            supply_types = set(supplies.keys())

            # Check if we have anything this shelter needs
            # Simple matching: water_cases -> water, blankets -> blankets
            supply_to_need = {
                "water_cases": "water",
                "blankets": "blankets",
                "medical_kits": "medical_supplies",
                "food_cases": "food",
            }

            matched_needs = []
            for supply, need in supply_to_need.items():
                if supply in supply_types and need in shelter_needs:
                    matched_needs.append(need)

            if not matched_needs:
                continue

            # Plan route to this shelter
            dest = Location(
                lat=shelter["location"]["lat"],
                lon=shelter["location"]["lon"],
                address=shelter.get("address"),
            )

            route = self.router.plan_route(origin, dest)
            if route:
                route.reasoning = (
                    f"Delivering to {shelter['name']} - "
                    f"needs: {', '.join(matched_needs)}. "
                    f"Occupancy: {shelter.get('current_occupancy', 0)}/{shelter.get('capacity', 0)}. "
                    + route.reasoning
                )
                routes.append(route)

        return routes

    def _generate_response(
        self,
        parsed_query: dict,
        routes: list[Route],
        intelligence: dict[str, list[AgentReport]],
    ) -> dict:
        """
        Generate final response with delivery plan and reasoning.

        TODO: Use Claude API for natural language generation.
        """
        # Summarize intelligence
        total_reports = sum(len(r) for r in intelligence.values())
        blocked_roads = len(self.road_network.get_blocked_edges())
        damaged_roads = len(self.road_network.get_damaged_edges())

        # Build response
        response = {
            "query": parsed_query.get("raw_query"),
            "scenario_time": self.scenario_time.isoformat(),
            "situational_awareness": {
                "total_reports": total_reports,
                "blocked_roads": blocked_roads,
                "damaged_roads": damaged_roads,
                "reports_by_source": {
                    name: len(reports) for name, reports in intelligence.items()
                },
            },
            "delivery_plan": {
                "origin": parsed_query.get("origin").to_dict() if parsed_query.get("origin") else None,
                "supplies": parsed_query.get("supplies", {}),
                "routes": [r.to_dict() for r in routes],
            },
            "reasoning": self._build_reasoning(routes, intelligence),
        }

        return response

    def _build_reasoning(
        self,
        routes: list[Route],
        intelligence: dict[str, list[AgentReport]],
    ) -> str:
        """Build human-readable reasoning for the delivery plan."""
        parts = []

        # Report on data sources
        parts.append("## Situational Awareness")
        for source, reports in intelligence.items():
            if reports:
                parts.append(f"- {source}: {len(reports)} reports")

        # Report on hazards
        blocked = self.road_network.get_blocked_edges()
        if blocked:
            parts.append(f"\n### Blocked Roads ({len(blocked)})")
            for edge in blocked[:5]:
                parts.append(f"- {edge.get('name', 'Unknown')} (confidence: {edge.get('confidence', 0):.0%})")

        # Report on routes
        if routes:
            parts.append("\n## Recommended Deliveries")
            for i, route in enumerate(routes, 1):
                parts.append(f"\n### Route {i}")
                parts.append(f"- Distance: {route.distance_m/1000:.1f} km")
                parts.append(f"- Estimated time: {route.estimated_duration_min:.0f} minutes")
                parts.append(f"- {route.reasoning}")
        else:
            parts.append("\n## No viable routes found")
            parts.append("All potential routes are blocked or no matching shelter needs.")

        return "\n".join(parts)

    def set_scenario_time(self, time: datetime) -> None:
        """Set the current scenario time."""
        self.scenario_time = time
        # Clear cached intelligence
        self._last_intelligence = {}

    def advance_scenario_time(self, hours: float) -> None:
        """Advance scenario time by specified hours."""
        from datetime import timedelta
        self.scenario_time += timedelta(hours=hours)
        self._last_intelligence = {}

    def load_road_network(self, geojson_path: str | Path) -> None:
        """Load road network from GeoJSON file."""
        self.road_network.load_from_geojson(geojson_path)

    def get_tool_definitions(self) -> list[dict]:
        """
        Get Claude tool definitions for agent queries.

        These would be used with Claude's tool use feature for
        structured agent interactions.
        """
        return [
            {
                "name": "query_satellite_agent",
                "description": "Query the satellite intelligence agent for flood and road damage detections from satellite imagery.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "area_description": {
                            "type": "string",
                            "description": "Description of area to query (e.g., 'Asheville downtown', 'I-40 corridor')",
                        },
                    },
                    "required": ["area_description"],
                },
            },
            {
                "name": "query_social_media_agent",
                "description": "Query the social media agent for real-time reports from Twitter and Reddit about road conditions and needs.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Topic to search for (e.g., 'road closures', 'shelter needs', 'flooding')",
                        },
                    },
                    "required": ["topic"],
                },
            },
            {
                "name": "query_official_agent",
                "description": "Query the official data agent for verified information from FEMA, NCDOT, and emergency management.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "data_type": {
                            "type": "string",
                            "enum": ["road_closures", "shelters", "all"],
                            "description": "Type of official data to retrieve",
                        },
                    },
                    "required": ["data_type"],
                },
            },
            {
                "name": "plan_route",
                "description": "Plan an optimal delivery route from origin to destination, avoiding known hazards.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "origin_lat": {"type": "number"},
                        "origin_lon": {"type": "number"},
                        "destination_lat": {"type": "number"},
                        "destination_lon": {"type": "number"},
                    },
                    "required": ["origin_lat", "origin_lon", "destination_lat", "destination_lon"],
                },
            },
            {
                "name": "get_shelter_needs",
                "description": "Get current supply needs for all active emergency shelters.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def get_system_prompt(self) -> str:
        """
        Get system prompt for Claude orchestrator.

        This would be used when integrating with Claude API.
        """
        return """You are a disaster relief logistics coordinator AI assistant. Your role is to help relief organizations efficiently route supplies to people in need during Hurricane Helene's aftermath in Western North Carolina.

You have access to multiple intelligence agents:
1. **Satellite Agent**: Provides high-confidence flood and damage detection from satellite imagery
2. **Social Media Agent**: Provides real-time but lower-confidence reports from Twitter/Reddit
3. **Official Agent**: Provides verified but potentially delayed information from FEMA and NCDOT
4. **Road Network Agent**: Maintains current road passability status

When a user asks about routing supplies:
1. First query relevant agents to understand current conditions
2. Identify priority shelters based on their needs
3. Plan routes that avoid blocked roads and minimize travel time
4. Explain your reasoning, citing which sources informed your decisions

Always prioritize safety. If a route seems risky, recommend alternatives or waiting for more information.

Current scenario: Hurricane Helene aftermath, September 27-28, 2024
Region: Western North Carolina (Asheville and surrounding areas)"""
