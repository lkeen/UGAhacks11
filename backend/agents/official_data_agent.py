"""Official Data Agent for disaster relief coordination."""

import json
from datetime import datetime
from pathlib import Path

from .base_agent import (
    AgentReport,
    BaseAgent,
    BoundingBox,
    DataSource,
    EventType,
    Location,
)


class OfficialDataAgent(BaseAgent):
    """
    Agent that aggregates official data from government sources.

    Sources include:
    - FEMA situation reports
    - State DOT road closure data
    - USGS flood gauges
    - Local emergency management agencies
    - National Weather Service

    Official data is slower but highly reliable.
    For the demo, we load from archived/mock official reports.
    """

    # Source reliability ratings
    SOURCE_RELIABILITY = {
        DataSource.FEMA: 0.98,
        DataSource.NCDOT: 0.95,
        DataSource.USGS: 0.97,
        DataSource.LOCAL_EMERGENCY: 0.90,
        DataSource.NEWS: 0.80,
    }

    def __init__(
        self,
        name: str = "OfficialDataAgent",
        confidence_weight: float = 0.95,
        data_path: str | Path | None = None,
    ):
        """
        Initialize the Official Data Agent.

        Args:
            name: Agent name
            confidence_weight: Base confidence multiplier (high for official sources)
            data_path: Path to official data JSON file
        """
        super().__init__(name, confidence_weight)
        self.data_path = Path(data_path) if data_path else None
        self._official_reports: list[dict] = []
        self._shelters: list[dict] = []

    def load_data(self, filepath: str | Path) -> None:
        """Load official reports and shelter data from JSON file."""
        filepath = Path(filepath)
        if filepath.exists():
            with open(filepath) as f:
                data = json.load(f)
                # Support both "reports" and "events" keys
                self._official_reports = data.get("reports", data.get("events", []))
                self._shelters = data.get("shelters", [])

    async def gather_intelligence(
        self,
        scenario_time: datetime,
        bbox: BoundingBox,
    ) -> list[AgentReport]:
        """
        Gather intelligence from official government sources.

        For the demo, returns archived official reports.
        In production, would poll FEMA, DOT, USGS APIs.

        Args:
            scenario_time: Current time in the disaster scenario
            bbox: Geographic area to search

        Returns:
            List of structured reports from official sources
        """
        # Clear previous reports to avoid duplicates
        self._reports = []
        reports = []
        seen_ids = set()

        # Load data if path set and not loaded
        if self.data_path and not self._official_reports:
            self.load_data(self.data_path)

        # Process official reports
        for report_data in self._official_reports:
            # Skip duplicates
            if report_data.get("id") in seen_ids:
                continue
            seen_ids.add(report_data.get("id"))

            report = self._process_official_report(report_data, scenario_time, bbox)
            if report:
                reports.append(report)
                self._reports.append(report)

        # Process shelter information
        for shelter in self._shelters:
            # Skip duplicates
            shelter_id = shelter.get("id", shelter.get("name"))
            if shelter_id in seen_ids:
                continue
            seen_ids.add(shelter_id)

            report = self._process_shelter(shelter, scenario_time, bbox)
            if report:
                reports.append(report)
                self._reports.append(report)

        return reports

    def _process_official_report(
        self,
        report_data: dict,
        scenario_time: datetime,
        bbox: BoundingBox,
    ) -> AgentReport | None:
        """Process a single official report into an AgentReport."""
        # Parse timestamp
        report_time = datetime.fromisoformat(
            report_data["timestamp"].replace("Z", "+00:00")
        )

        # Skip reports after scenario time
        if report_time > scenario_time:
            return None

        # Check location
        location = Location(
            lat=report_data["location"]["lat"],
            lon=report_data["location"]["lon"],
            address=report_data.get("address"),
        )
        if not bbox.contains(location):
            return None

        # Map source string to DataSource enum
        source_str = report_data.get("source", "fema").lower()

        # Map source - allow all sources from the timeline
        source = self._map_source(source_str)

        # Map report type to event type
        event_type = self._map_report_type(report_data.get("type", "road_closure"))
        if event_type is None:
            return None

        # Get reliability-based confidence
        confidence = self.SOURCE_RELIABILITY.get(source, 0.85)

        return AgentReport(
            timestamp=report_time,
            event_type=event_type,
            location=location,
            description=report_data.get("description", ""),
            source=source,
            confidence=confidence,
            raw_data=report_data,
            agent_name=self.name,
            metadata={
                "report_id": report_data.get("report_id"),
                "agency": report_data.get("agency"),
                "verified": True,
                "official": True,
            },
        )

    def _process_shelter(
        self,
        shelter: dict,
        scenario_time: datetime,
        bbox: BoundingBox,
    ) -> AgentReport | None:
        """Process shelter information into an AgentReport."""
        # Parse opening time
        if shelter.get("opened_at") is not None:
            opened_time = datetime.fromisoformat(
                shelter["opened_at"].replace("Z", "+00:00")
            )
            if opened_time > scenario_time:
                return None
        else:
            opened_time = scenario_time

        # Check if shelter closed
        if "closed_at" in shelter:
            closed_time = datetime.fromisoformat(
                shelter["closed_at"].replace("Z", "+00:00")
            )
            if closed_time <= scenario_time:
                return None  # Shelter has closed

        # Check location
        location = Location(
            lat=shelter["location"]["lat"],
            lon=shelter["location"]["lon"],
            address=shelter.get("address"),
        )
        if not bbox.contains(location):
            return None

        # Build description with needs
        needs = shelter.get("needs", [])
        needs_str = ", ".join(needs) if needs else "General supplies"
        description = f"{shelter['name']} - Capacity: {shelter.get('capacity', 'Unknown')}, Needs: {needs_str}"

        return AgentReport(
            timestamp=opened_time,
            event_type=EventType.SHELTER_OPENING,
            location=location,
            description=description,
            source=DataSource.LOCAL_EMERGENCY,
            confidence=0.95,
            raw_data=shelter,
            agent_name=self.name,
            metadata={
                "shelter_name": shelter["name"],
                "capacity": shelter.get("capacity"),
                "current_occupancy": shelter.get("current_occupancy", 0),
                "needs": needs,
                "contact": shelter.get("contact"),
                "accepts_pets": shelter.get("accepts_pets", False),
            },
        )

    def assess_confidence(self, report: AgentReport) -> float:
        """
        Calculate final confidence score for an official report.

        Official sources are highly trusted, but may be delayed.
        """
        base_confidence = report.confidence

        # Apply agent weight
        final_confidence = base_confidence * self.confidence_weight

        # Official data is almost always reliable
        return max(0.0, min(1.0, final_confidence))

    def _map_source(self, source_str: str) -> DataSource:
        """Map source string to DataSource enum."""
        mapping = {
            "fema": DataSource.FEMA,
            "ncdot": DataSource.NCDOT,
            "usgs": DataSource.USGS,
            "local_emergency": DataSource.LOCAL_EMERGENCY,
            "news": DataSource.NEWS,
            "twitter": DataSource.TWITTER,
            "citizen_report": DataSource.CITIZEN_REPORT,
        }
        return mapping.get(source_str.lower(), DataSource.CITIZEN_REPORT)

    def _map_report_type(self, report_type: str) -> EventType | None:
        """Map official report type to event type."""
        mapping = {
            "road_closure": EventType.ROAD_CLOSURE,
            "road_damage": EventType.ROAD_DAMAGE,
            "road_clear": EventType.ROAD_CLEAR,
            "bridge_closure": EventType.BRIDGE_COLLAPSE,
            "bridge_collapse": EventType.BRIDGE_COLLAPSE,
            "flooding": EventType.FLOODING,
            "power_outage": EventType.POWER_OUTAGE,
            "shelter_opening": EventType.SHELTER_OPENING,
            "shelter_closing": EventType.SHELTER_CLOSING,
            "infrastructure_damage": EventType.INFRASTRUCTURE_DAMAGE,
            "rescue_needed": EventType.RESCUE_NEEDED,
            "supplies_needed": EventType.SUPPLIES_NEEDED,
        }
        return mapping.get(report_type.lower())

    def get_shelters(self, scenario_time: datetime) -> list[dict]:
        """Get list of currently open shelters with their needs."""
        active_shelters = []

        for shelter in self._shelters:
            # Check if opened
            if shelter.get("opened_at") is not None:
                opened_time = datetime.fromisoformat(
                    shelter["opened_at"].replace("Z", "+00:00")
                )
                if opened_time > scenario_time:
                    continue

            # Check if closed
            if "closed_at" in shelter:
                closed_time = datetime.fromisoformat(
                    shelter["closed_at"].replace("Z", "+00:00")
                )
                if closed_time <= scenario_time:
                    continue

            active_shelters.append(shelter)

        return active_shelters

    def get_shelter_needs(self, scenario_time: datetime) -> dict[str, list[str]]:
        """Get aggregated needs across all active shelters."""
        needs_by_shelter = {}
        for shelter in self.get_shelters(scenario_time):
            needs_by_shelter[shelter["name"]] = shelter.get("needs", [])
        return needs_by_shelter
