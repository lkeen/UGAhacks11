"""Orchestrator for multi-agent disaster relief coordination."""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import anthropic

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
from backend.agents.base_agent import EventType, Location
from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS
from backend.routing import RoadNetworkManager, Router, Route
from backend.utils.report_aggregator import identify_conflicting_reports

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator that coordinates multiple agents for disaster relief.

    Uses Claude API to:
    1. Parse user queries about supply routing
    2. Resolve conflicting agent reports
    3. Generate human-readable delivery plans with reasoning
    """

    def __init__(
        self,
        anthropic_api_key: str | None = None,
        data_dir: str | Path | None = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            anthropic_api_key: API key for Claude (falls back to env/config)
            data_dir: Directory containing mock data files
        """
        self.api_key = anthropic_api_key or ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "data"

        # Initialize Claude client
        self.client: anthropic.Anthropic | None = None
        if self.api_key:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("Claude API client initialized successfully")
            except Exception as e:
                logger.warning("Failed to initialize Claude client: %s", e)

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
            with open(shelters_path) as f:
                shelter_data = json.load(f)
                self.official_data_agent._shelters = shelter_data.get("shelters", [])

        # Initialize road network
        self.road_network = RoadNetworkManager()
        geojson_path = self.data_dir / "osm" / "western_nc_roads.geojson"
        if geojson_path.exists():
            self.road_network.load_from_geojson(geojson_path)
            logger.info("Loaded road network from %s", geojson_path)
        self.road_network_agent = RoadNetworkAgent(
            road_network_manager=self.road_network
        )

        # Initialize router with event data for hazard polygon avoidance
        events_data = self._load_timeline_events()
        self.router = Router(self.road_network, events_data=events_data)

        # Scenario state
        self.scenario_time: datetime = datetime.fromisoformat("2024-09-27T03:00:00+00:00")
        self._previous_scenario_time: datetime | None = None
        self.bbox: BoundingBox = WESTERN_NC_BBOX

        # Agent outputs cache
        self._last_intelligence: dict[str, list[AgentReport]] = {}

    # ------------------------------------------------------------------
    # Intelligence gathering
    # ------------------------------------------------------------------

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

        # Refresh router's event data for polygon avoidance
        self.router.set_events_data(self._load_timeline_events())

        return total_updated

    # ------------------------------------------------------------------
    # Main query pipeline
    # ------------------------------------------------------------------

    async def process_query(self, query: str) -> dict:
        """
        Process a natural language query about supply routing.

        Pipeline: parse -> gather intel -> resolve conflicts -> plan routes -> explain.

        Args:
            query: User query like "I have 200 water cases at Asheville depot"

        Returns:
            Dict with delivery plan and reasoning
        """
        # Step 1: Parse query via Claude (or fallback)
        parsed = self._parse_query(query)

        # Step 2: Gather intelligence
        intelligence = await self.gather_all_intelligence()

        # Step 3: Apply to road network
        edges_updated = self.apply_intelligence_to_network()

        # Step 4: Resolve conflicts
        all_reports = [r for reports in intelligence.values() for r in reports]
        conflicts = identify_conflicting_reports(all_reports)
        resolved_conflicts = []
        for conflict in conflicts:
            resolution = self.resolve_conflicting_reports(
                conflict["reports"], conflict["road_id"]
            )
            resolved_conflicts.append(resolution)

        # Step 5: Check we have an origin
        if parsed.get("origin") is None:
            response = self._generate_response(parsed, [], intelligence, resolved_conflicts)
            response["error"] = "Could not determine your starting location. Please include a place name, address, or landmark in your message."
            return response

        # Step 6: Get shelter needs
        shelters = self._get_priority_shelters()

        # Step 7: Plan routes
        routes = self._plan_delivery_routes(parsed, shelters)

        # Step 8: Generate response with Claude reasoning
        response = self._generate_response(parsed, routes, intelligence, resolved_conflicts)

        return response

    # ------------------------------------------------------------------
    # Claude-powered query parsing
    # ------------------------------------------------------------------

    def _parse_query(self, query: str) -> dict:
        """
        Parse user query using Claude to extract structured parameters.

        Falls back to keyword-based parsing if Claude API is unavailable.
        """
        parsed = None
        if self.client:
            try:
                parsed = self._parse_query_with_claude(query)
            except Exception as e:
                logger.warning("Claude query parsing failed, using fallback: %s", e)

        if parsed is None:
            parsed = self._parse_query_fallback(query)

        # Last resort: if still no origin, try keyword matching
        if parsed.get("origin") is None:
            parsed["origin"] = self._match_origin_from_text(query)

        return parsed

    def _parse_query_with_claude(self, query: str) -> dict:
        """Call Claude to extract structured info from a natural language query."""
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=(
                "You are a geocoding and logistics parser. "
                "Your job is to read a user's message, figure out WHERE they are, "
                "and WHAT supplies they have. "
                "Respond ONLY with valid JSON, no markdown fences."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Read this disaster relief message and extract:\n\n"
                        "- origin_description: the place the user says they ARE or where their supplies are\n"
                        "- origin_lat: the latitude of that place (float). Use your geographic knowledge "
                        "to look up / estimate the coordinates of whatever location is mentioned. "
                        "This could be a city, a store, a staging area, a warehouse, a road, an "
                        "intersection, an address — anything. Estimate as accurately as you can. "
                        "The disaster area is Western North Carolina.\n"
                        "- origin_lon: the longitude of that place (float)\n"
                        "- supplies: dict of supply_type -> quantity (int). Types: "
                        "water_cases, blankets, medical_kits, food_cases, generators, fuel, "
                        "diapers, baby_formula, pet_supplies, hygiene_kits, cots, medications, "
                        "charging_stations. If a supply is mentioned without a number, use 1.\n"
                        "- urgency: one of 'low', 'medium', 'high', 'critical'\n"
                        "- constraints: list of strings (e.g. 'avoid flooding')\n"
                        "- intent: one of 'route_supplies', 'check_status', 'find_shelter'\n\n"
                        "RULES:\n"
                        "- Do NOT default to any location. Only set origin_lat/origin_lon if "
                        "the user actually mentions a place.\n"
                        "- If the user does not mention any location, set origin_lat and "
                        "origin_lon to null.\n"
                        "- Do NOT assume the airport or any other default.\n\n"
                        f"Message: {query}\n\n"
                        "JSON:"
                    ),
                }
            ],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)

        origin = None
        if data.get("origin_lat") is not None and data.get("origin_lon") is not None:
            origin = Location(
                lat=float(data["origin_lat"]),
                lon=float(data["origin_lon"]),
                address=data.get("origin_description", ""),
            )

        parsed = {
            "intent": data.get("intent", "route_supplies"),
            "supplies": data.get("supplies", {}),
            "origin": origin,
            "raw_query": query,
            "urgency": data.get("urgency", "medium"),
            "constraints": data.get("constraints", []),
            "parsed_by": "claude",
        }

        if parsed["origin"]:
            logger.info("Parsed origin: %s (%.4f, %.4f) [claude]",
                         parsed["origin"].address, parsed["origin"].lat,
                         parsed["origin"].lon)
        else:
            logger.warning("Claude could not determine origin from query: %s", query)

        return parsed

    def _match_origin_from_text(self, text: str) -> Location | None:
        """
        Try to match a starting location from free text.

        Only matches against landmarks, depots, and town names — NOT shelters,
        because shelters are destinations, not origins.
        """
        text_lower = text.lower()

        # Only use landmarks and depots for origin matching (not shelters)
        origin_locations = self._get_origin_locations()

        # Build search entries sorted longest-keyword-first
        search_entries = []
        for loc in origin_locations:
            name = loc["name"]
            keywords = [name.lower()]
            for word in name.lower().split():
                if len(word) >= 4:
                    keywords.append(word)
            search_entries.append((keywords, loc))

        search_entries.sort(key=lambda e: max(len(k) for k in e[0]), reverse=True)

        for keywords, loc in search_entries:
            for kw in keywords:
                if kw in text_lower:
                    return Location(
                        lat=loc["lat"], lon=loc["lon"], address=loc["name"],
                    )

        return None

    def _get_origin_locations(self) -> list[dict]:
        """Get locations suitable as route origins (depots + landmarks, NOT shelters)."""
        locations = []

        # Add supply depots
        shelters_path = self.data_dir / "shelters" / "shelters.json"
        if shelters_path.exists():
            with open(shelters_path) as f:
                data = json.load(f)
            for d in data.get("supply_depots", []):
                loc = d.get("location", {})
                locations.append({
                    "name": d.get("name", ""),
                    "lat": loc.get("lat"),
                    "lon": loc.get("lon"),
                })

        # Town/city/landmark names only
        locations.extend([
            {"name": "Asheville Regional Airport", "lat": 35.4363, "lon": -82.5418},
            {"name": "Asheville Downtown", "lat": 35.5951, "lon": -82.5515},
            {"name": "Hendersonville", "lat": 35.4368, "lon": -82.4573},
            {"name": "Black Mountain", "lat": 35.6178, "lon": -82.3215},
            {"name": "Brevard", "lat": 35.2334, "lon": -82.7343},
            {"name": "Boone", "lat": 36.2168, "lon": -81.6746},
            {"name": "Cherokee", "lat": 35.4743, "lon": -83.3146},
            {"name": "Mars Hill", "lat": 35.7965, "lon": -82.5493},
            {"name": "Waynesville", "lat": 35.4887, "lon": -82.9887},
            {"name": "Weaverville", "lat": 35.6973, "lon": -82.5607},
            {"name": "Swannanoa", "lat": 35.5982, "lon": -82.3990},
            {"name": "Canton", "lat": 35.5329, "lon": -82.8373},
            {"name": "Marion", "lat": 35.6840, "lon": -82.0093},
            {"name": "Burnsville", "lat": 35.9174, "lon": -82.2929},
            {"name": "Spruce Pine", "lat": 35.9154, "lon": -82.0646},
            {"name": "Sylva", "lat": 35.3734, "lon": -83.2257},
            {"name": "Bryson City", "lat": 35.4312, "lon": -83.4496},
            {"name": "Old Fort", "lat": 35.6276, "lon": -82.1735},
            {"name": "Linville Falls", "lat": 35.9503, "lon": -81.9285},
            {"name": "Fletcher", "lat": 35.4307, "lon": -82.5010},
            {"name": "Arden", "lat": 35.4698, "lon": -82.5151},
            {"name": "Enka", "lat": 35.5373, "lon": -82.6413},
            {"name": "West Asheville", "lat": 35.5780, "lon": -82.5860},
            {"name": "Biltmore Village", "lat": 35.5707, "lon": -82.5430},
            {"name": "River Arts District", "lat": 35.5750, "lon": -82.5680},
        ])

        return [loc for loc in locations if loc.get("lat") and loc.get("lon")]

    def _parse_query_fallback(self, query: str) -> dict:
        """Keyword-based query parsing fallback."""
        parsed = {
            "intent": "route_supplies",
            "supplies": {},
            "origin": None,
            "raw_query": query,
            "urgency": "medium",
            "constraints": [],
            "parsed_by": "keyword",
        }

        query_lower = query.lower()

        # Extract supply types and quantities
        supply_patterns = {
            "water_cases": r"(\d+)\s*(?:cases?\s+of\s+)?water",
            "blankets": r"(\d+)\s*blanket",
            "medical_kits": r"(\d+)\s*(?:medical\s+)?(?:kit|med)",
            "food_cases": r"(\d+)\s*(?:cases?\s+of\s+)?food",
            "generators": r"(\d+)\s*generator",
            "cots": r"(\d+)\s*cot",
            "diapers": r"(\d+)\s*(?:packs?\s+of\s+)?diaper",
            "medications": r"(\d+)\s*(?:medication|medicine)",
        }
        for supply_key, pattern in supply_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                parsed["supplies"][supply_key] = int(match.group(1))

        # If no specific quantities found, try to detect supply types mentioned
        if not parsed["supplies"]:
            type_keywords = {
                "water_cases": ["water"],
                "food_cases": ["food", "mre"],
                "blankets": ["blanket"],
                "medical_kits": ["medical", "medicine", "med kit", "first aid"],
                "generators": ["generator"],
                "cots": ["cot", "bed"],
                "diapers": ["diaper"],
                "medications": ["medication", "medicine", "prescription"],
            }
            for supply_key, keywords in type_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    parsed["supplies"][supply_key] = 1  # unknown qty

        # Extract origin from the query text (keyword fallback — no defaults)
        parsed["origin"] = self._match_origin_from_text(query)

        if parsed["origin"]:
            logger.info("Parsed origin: %s (%.4f, %.4f) [keyword]",
                         parsed["origin"].address, parsed["origin"].lat,
                         parsed["origin"].lon)
        else:
            logger.warning("Keyword parser could not determine origin from: %s", query)

        # Urgency hints
        if any(w in query_lower for w in ["urgent", "critical", "emergency", "asap"]):
            parsed["urgency"] = "critical"
        elif any(w in query_lower for w in ["soon", "quickly", "hurry"]):
            parsed["urgency"] = "high"

        return parsed

    # ------------------------------------------------------------------
    # Conflict resolution via Claude
    # ------------------------------------------------------------------

    def resolve_conflicting_reports(
        self,
        reports: list[AgentReport],
        road_id: str,
    ) -> dict:
        """
        Use Claude to resolve conflicting reports about a road/location.

        Falls back to highest-confidence-wins heuristic if Claude is unavailable.

        Args:
            reports: Conflicting AgentReport objects about the same location.
            road_id: Identifier for the road or location in question.

        Returns:
            Dict with resolved_status, confidence, reasoning.
        """
        if self.client and len(reports) >= 2:
            try:
                return self._resolve_conflicts_with_claude(reports, road_id)
            except Exception as e:
                logger.warning("Claude conflict resolution failed, using fallback: %s", e)

        return self._resolve_conflicts_fallback(reports, road_id)

    def _resolve_conflicts_with_claude(
        self, reports: list[AgentReport], road_id: str
    ) -> dict:
        """Ask Claude to resolve conflicting reports."""
        reports_summary = []
        for r in reports:
            reports_summary.append({
                "agent": r.agent_name,
                "event_type": r.event_type.value,
                "confidence": r.confidence,
                "source": r.source.value,
                "description": r.description,
                "timestamp": r.timestamp.isoformat(),
            })

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system="You are a disaster relief intelligence analyst. Resolve conflicting field reports. Respond ONLY with valid JSON, no markdown fences.",
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"These reports about '{road_id}' are conflicting:\n"
                        f"{json.dumps(reports_summary, indent=2)}\n\n"
                        "Analyze source reliability, recency, and confidence to determine the true status.\n"
                        "Respond with JSON:\n"
                        '{"resolved_status": "blocked|damaged|clear", '
                        '"confidence": 0.0-1.0, '
                        '"reasoning": "explanation"}'
                    ),
                }
            ],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        result["road_id"] = road_id
        result["resolved_by"] = "claude"
        return result

    def _resolve_conflicts_fallback(
        self, reports: list[AgentReport], road_id: str
    ) -> dict:
        """Resolve conflicts by picking the highest-confidence report."""
        if not reports:
            return {
                "road_id": road_id,
                "resolved_status": "unknown",
                "confidence": 0.0,
                "reasoning": "No reports available.",
                "resolved_by": "fallback",
            }

        best = max(reports, key=lambda r: r.confidence)

        status_map = {
            EventType.ROAD_CLOSURE: "blocked",
            EventType.BRIDGE_COLLAPSE: "blocked",
            EventType.FLOODING: "blocked",
            EventType.ROAD_DAMAGE: "damaged",
            EventType.ROAD_CLEAR: "clear",
        }

        return {
            "road_id": road_id,
            "resolved_status": status_map.get(best.event_type, "unknown"),
            "confidence": best.confidence,
            "reasoning": (
                f"Resolved by highest confidence ({best.confidence:.0%}) from "
                f"{best.agent_name or best.source.value}: {best.description}"
            ),
            "resolved_by": "fallback",
        }

    # ------------------------------------------------------------------
    # Shelter & route planning (unchanged)
    # ------------------------------------------------------------------

    def _get_known_locations(self) -> list[dict]:
        """Build a list of all known named locations from shelters, depots, and landmarks."""
        locations = []

        # Add shelters and depots
        shelters_path = self.data_dir / "shelters" / "shelters.json"
        if shelters_path.exists():
            with open(shelters_path) as f:
                data = json.load(f)
            for s in data.get("shelters", []):
                loc = s.get("location", {})
                locations.append({
                    "name": s.get("name", s.get("address", "")),
                    "lat": loc.get("lat"),
                    "lon": loc.get("lon"),
                })
            for d in data.get("supply_depots", []):
                loc = d.get("location", {})
                locations.append({
                    "name": d.get("name", d.get("address", "")),
                    "lat": loc.get("lat"),
                    "lon": loc.get("lon"),
                })

        # Add well-known landmarks
        landmarks = [
            {"name": "Asheville Regional Airport", "lat": 35.4363, "lon": -82.5418},
            {"name": "Asheville Downtown", "lat": 35.5951, "lon": -82.5515},
            {"name": "Hendersonville", "lat": 35.4368, "lon": -82.4573},
            {"name": "Black Mountain", "lat": 35.6178, "lon": -82.3215},
            {"name": "Brevard", "lat": 35.2334, "lon": -82.7343},
            {"name": "Boone", "lat": 36.2168, "lon": -81.6746},
            {"name": "Cherokee", "lat": 35.4743, "lon": -83.3146},
            {"name": "Mars Hill", "lat": 35.7965, "lon": -82.5493},
            {"name": "Waynesville", "lat": 35.4887, "lon": -82.9887},
            {"name": "Weaverville", "lat": 35.6973, "lon": -82.5607},
            {"name": "Swannanoa", "lat": 35.5982, "lon": -82.3990},
            {"name": "Canton", "lat": 35.5329, "lon": -82.8373},
            {"name": "Marion", "lat": 35.6840, "lon": -82.0093},
            {"name": "Burnsville", "lat": 35.9174, "lon": -82.2929},
            {"name": "Spruce Pine", "lat": 35.9154, "lon": -82.0646},
            {"name": "Sylva", "lat": 35.3734, "lon": -83.2257},
            {"name": "Bryson City", "lat": 35.4312, "lon": -83.4496},
            {"name": "Old Fort", "lat": 35.6276, "lon": -82.1735},
            {"name": "Linville Falls", "lat": 35.9503, "lon": -81.9285},
            {"name": "Ingles Distribution Center", "lat": 35.4522, "lon": -82.4701},
        ]
        locations.extend(landmarks)

        return [loc for loc in locations if loc.get("lat") and loc.get("lon")]

    def _load_timeline_events(self) -> list[dict]:
        """Load raw event data from the timeline JSON for hazard polygon extraction."""
        timeline_path = self.data_dir / "events" / "helene_timeline.json"
        if not timeline_path.exists():
            return []
        with open(timeline_path) as f:
            data = json.load(f)
        return data.get("events", [])

    def _get_priority_shelters(self) -> list[dict]:
        """Get shelters prioritized by urgency of needs."""
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

        Ranks shelters by a combined score of:
        - How many of their needs match the user's supplies
        - How close they are to the origin (closer = better)
        - How full they are (fuller = more urgent)

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

        supplies = parsed_query.get("supplies", {})

        # Broader supply-to-need mapping
        supply_to_need = {
            "water_cases": "water",
            "blankets": "blankets",
            "medical_kits": "medical_supplies",
            "food_cases": "food",
            "generators": "generators",
            "fuel": "fuel",
            "diapers": "diapers",
            "baby_formula": "baby_formula",
            "pet_supplies": "pet_supplies",
            "hygiene_kits": "hygiene_kits",
            "cots": "cots",
            "medications": "medications",
            "charging_stations": "charging_stations",
        }

        # Score each shelter
        scored_shelters = []
        for shelter in shelters:
            shelter_needs = set(shelter.get("needs", []))
            if not shelter_needs:
                continue

            # Count matching needs
            matched_needs = []
            for supply_key, need_name in supply_to_need.items():
                if supply_key in supplies and need_name in shelter_needs:
                    matched_needs.append(need_name)

            # If user specified supplies and none match, still consider
            # shelters that have urgent needs (but lower score)
            need_score = len(matched_needs) / max(len(supplies), 1) if supplies else 1.0

            # Distance score (closer to origin = higher score)
            sloc = shelter.get("location", {})
            dist_deg = (
                (sloc.get("lat", 0) - origin.lat) ** 2
                + (sloc.get("lon", 0) - origin.lon) ** 2
            ) ** 0.5
            # Normalize: 0.01 deg ~ 1km. Max useful distance ~ 2 degrees
            proximity_score = max(0.0, 1.0 - dist_deg / 2.0)

            # Occupancy urgency (fuller = more urgent)
            occupancy_ratio = (
                shelter.get("current_occupancy", 0)
                / max(shelter.get("capacity", 1), 1)
            )

            # Combined score: needs match is most important, then proximity, then urgency
            total_score = (need_score * 0.4) + (proximity_score * 0.35) + (occupancy_ratio * 0.25)

            scored_shelters.append({
                "shelter": shelter,
                "matched_needs": matched_needs,
                "score": total_score,
            })

        # Sort by score descending
        scored_shelters.sort(key=lambda x: x["score"], reverse=True)

        # Plan routes to top shelters
        for entry in scored_shelters[:3]:
            shelter = entry["shelter"]
            matched = entry["matched_needs"]

            dest = Location(
                lat=shelter["location"]["lat"],
                lon=shelter["location"]["lon"],
                address=shelter.get("address"),
            )

            route = self.router.plan_route(origin, dest)
            if route:
                needs_str = ", ".join(matched) if matched else ", ".join(shelter.get("needs", [])[:3])
                route.reasoning = (
                    f"Delivering to {shelter['name']} - "
                    f"needs: {needs_str}. "
                    f"Occupancy: {shelter.get('current_occupancy', 0)}/{shelter.get('capacity', 0)}. "
                    + route.reasoning
                )
                routes.append(route)

        return routes

    # ------------------------------------------------------------------
    # Response generation
    # ------------------------------------------------------------------

    def _generate_response(
        self,
        parsed_query: dict,
        routes: list[Route],
        intelligence: dict[str, list[AgentReport]],
        resolved_conflicts: list[dict] | None = None,
    ) -> dict:
        """
        Generate final response with delivery plan and reasoning.
        """
        total_reports = sum(len(r) for r in intelligence.values())
        blocked_roads = len(self.road_network.get_blocked_edges())
        damaged_roads = len(self.road_network.get_damaged_edges())

        response = {
            "query": parsed_query.get("raw_query"),
            "parsed_by": parsed_query.get("parsed_by", "unknown"),
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
                "urgency": parsed_query.get("urgency", "medium"),
                "routes": [r.to_dict() for r in routes],
            },
            "conflicts_resolved": resolved_conflicts or [],
            "reasoning": self._build_reasoning(routes, intelligence, resolved_conflicts),
        }

        return response

    def _build_reasoning(
        self,
        routes: list[Route],
        intelligence: dict[str, list[AgentReport]],
        resolved_conflicts: list[dict] | None = None,
    ) -> str:
        """
        Build human-readable reasoning for the delivery plan.

        Uses Claude for natural-language explanation when available,
        falls back to a template.
        """
        if self.client:
            try:
                return self._build_reasoning_with_claude(routes, intelligence, resolved_conflicts)
            except Exception as e:
                logger.warning("Claude reasoning generation failed, using fallback: %s", e)

        return self._build_reasoning_fallback(routes, intelligence, resolved_conflicts)

    def _build_reasoning_with_claude(
        self,
        routes: list[Route],
        intelligence: dict[str, list[AgentReport]],
        resolved_conflicts: list[dict] | None = None,
    ) -> str:
        """Use Claude to generate human-readable reasoning."""
        # Build context for Claude
        blocked = self.road_network.get_blocked_edges()
        damaged = self.road_network.get_damaged_edges()

        context = {
            "num_routes": len(routes),
            "routes": [
                {
                    "destination": r.destination.to_dict() if r.destination else None,
                    "distance_km": round(r.distance_m / 1000, 1),
                    "duration_min": round(r.estimated_duration_min),
                    "hazards_avoided": r.hazards_avoided,
                    "confidence": r.confidence,
                }
                for r in routes
            ],
            "intelligence_summary": {
                source: len(reports) for source, reports in intelligence.items()
            },
            "blocked_roads": len(blocked),
            "damaged_roads": len(damaged),
            "conflicts_resolved": len(resolved_conflicts) if resolved_conflicts else 0,
        }

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=self.get_system_prompt(),
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Generate a concise briefing for a field relief team based on this delivery plan data. "
                        "Use markdown headings and bullet points. Keep it under 300 words. "
                        "Focus on: what data sources informed the plan, key hazards, recommended routes, and confidence levels.\n\n"
                        f"{json.dumps(context, indent=2)}"
                    ),
                }
            ],
        )

        return response.content[0].text.strip()

    def _build_reasoning_fallback(
        self,
        routes: list[Route],
        intelligence: dict[str, list[AgentReport]],
        resolved_conflicts: list[dict] | None = None,
    ) -> str:
        """Template-based reasoning fallback."""
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

        # Report on conflict resolutions
        if resolved_conflicts:
            parts.append(f"\n### Conflicts Resolved ({len(resolved_conflicts)})")
            for conflict in resolved_conflicts:
                parts.append(
                    f"- {conflict.get('road_id', 'Unknown')}: "
                    f"{conflict.get('resolved_status', '?')} "
                    f"(confidence: {conflict.get('confidence', 0):.0%}) "
                    f"[{conflict.get('resolved_by', 'unknown')}]"
                )

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

    # ------------------------------------------------------------------
    # Scenario time management
    # ------------------------------------------------------------------

    def set_scenario_time(self, time: datetime) -> None:
        """Set the current scenario time."""
        self._previous_scenario_time = self.scenario_time
        self.scenario_time = time
        self._last_intelligence = {}

    async def gather_new_intelligence(self) -> dict[str, list[AgentReport]]:
        """
        Gather only NEW intelligence since the last time advancement.

        Returns reports that occurred between _previous_scenario_time and scenario_time.
        """
        all_intelligence = await self.gather_all_intelligence()

        if self._previous_scenario_time is None:
            return all_intelligence

        new_intelligence = {}
        for source, reports in all_intelligence.items():
            new_reports = [
                r for r in reports
                if self._previous_scenario_time < r.timestamp <= self.scenario_time
            ]
            new_intelligence[source] = new_reports

        return new_intelligence

    def advance_scenario_time(self, hours: float) -> None:
        """Advance scenario time by specified hours."""
        from datetime import timedelta
        self._previous_scenario_time = self.scenario_time
        self.scenario_time += timedelta(hours=hours)
        self._last_intelligence = {}

    def load_road_network(self, geojson_path: str | Path) -> None:
        """Load road network from GeoJSON file."""
        self.road_network.load_from_geojson(geojson_path)

    # ------------------------------------------------------------------
    # Claude tool definitions & system prompt
    # ------------------------------------------------------------------

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
