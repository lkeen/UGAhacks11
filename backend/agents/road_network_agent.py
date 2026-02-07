"""Road Network Agent for disaster relief coordination."""

from datetime import datetime

from .base_agent import (
    AgentReport,
    BaseAgent,
    BoundingBox,
    DataSource,
    EventType,
    Location,
)


class RoadNetworkAgent(BaseAgent):
    """
    Agent that maintains and queries the live road network state.

    This agent doesn't gather external intelligence directly.
    Instead, it:
    - Maintains the road network graph
    - Aggregates reports from other agents
    - Resolves conflicting reports using confidence-weighted voting
    - Provides routing queries with current network state

    Works in conjunction with the RoadNetworkManager in the routing module.
    """

    # Event types that affect road passability
    ROAD_AFFECTING_EVENTS = {
        EventType.ROAD_CLOSURE,
        EventType.ROAD_DAMAGE,
        EventType.BRIDGE_COLLAPSE,
        EventType.FLOODING,
    }

    # How events affect road weights (multipliers)
    EVENT_WEIGHT_IMPACT = {
        EventType.ROAD_CLOSURE: float("inf"),  # Impassable
        EventType.BRIDGE_COLLAPSE: float("inf"),  # Impassable
        EventType.ROAD_DAMAGE: 3.0,  # Slow but passable
        EventType.FLOODING: 5.0,  # Very slow/risky
        EventType.ROAD_CLEAR: 1.0,  # Normal
    }

    def __init__(
        self,
        name: str = "RoadNetworkAgent",
        confidence_weight: float = 1.0,
        road_network_manager=None,
    ):
        """
        Initialize the Road Network Agent.

        Args:
            name: Agent name
            confidence_weight: Base confidence multiplier
            road_network_manager: Reference to RoadNetworkManager instance
        """
        super().__init__(name, confidence_weight)
        self.road_network_manager = road_network_manager
        self._pending_updates: list[AgentReport] = []
        self._road_status: dict[str, dict] = {}  # edge_id -> status info

    async def gather_intelligence(
        self,
        scenario_time: datetime,
        bbox: BoundingBox,
    ) -> list[AgentReport]:
        """
        The Road Network Agent doesn't gather external intelligence.

        Instead, it processes pending updates from other agents
        and returns its current understanding of road conditions.

        Args:
            scenario_time: Current time in scenario
            bbox: Area of interest

        Returns:
            List of current road status reports
        """
        # Process any pending updates
        self._process_pending_updates()

        # Return current road status as reports
        reports = []
        for edge_id, status in self._road_status.items():
            if status.get("last_update"):
                location = status.get("location", Location(0, 0))
                if bbox.contains(location):
                    reports.append(
                        AgentReport(
                            timestamp=status["last_update"],
                            event_type=status["event_type"],
                            location=location,
                            description=f"Road segment {edge_id}: {status['status']}",
                            source=DataSource.CITIZEN_REPORT,  # Aggregated
                            confidence=status["confidence"],
                            agent_name=self.name,
                            metadata={
                                "edge_id": edge_id,
                                "weight_multiplier": status["weight_multiplier"],
                                "report_count": status["report_count"],
                            },
                        )
                    )

        return reports

    def assess_confidence(self, report: AgentReport) -> float:
        """
        Assess confidence of a road status report.

        Confidence increases with more corroborating reports from different sources.
        """
        base_confidence = report.confidence

        # Boost for multiple sources
        report_count = report.metadata.get("report_count", 1)
        if report_count >= 3:
            base_confidence = min(0.95, base_confidence + 0.15)
        elif report_count >= 2:
            base_confidence = min(0.90, base_confidence + 0.10)

        return base_confidence * self.confidence_weight

    def receive_update(self, report: AgentReport) -> None:
        """
        Receive an update from another agent about road conditions.

        Updates are queued for processing to handle conflicts.

        Args:
            report: AgentReport from another agent
        """
        if report.event_type in self.ROAD_AFFECTING_EVENTS or report.event_type == EventType.ROAD_CLEAR:
            self._pending_updates.append(report)

    def receive_updates(self, reports: list[AgentReport]) -> None:
        """Receive multiple updates at once."""
        for report in reports:
            self.receive_update(report)

    def _process_pending_updates(self) -> None:
        """
        Process all pending updates and resolve conflicts.

        Uses confidence-weighted voting when reports conflict.
        """
        if not self._pending_updates:
            return

        # Group updates by approximate location (road segment)
        updates_by_location: dict[str, list[AgentReport]] = {}

        for report in self._pending_updates:
            # Create location key (rounded to ~100m precision)
            loc_key = f"{report.location.lat:.3f},{report.location.lon:.3f}"

            if loc_key not in updates_by_location:
                updates_by_location[loc_key] = []
            updates_by_location[loc_key].append(report)

        # Process each location
        for loc_key, reports in updates_by_location.items():
            self._resolve_location_status(loc_key, reports)

        # Clear pending updates
        self._pending_updates = []

    def _resolve_location_status(
        self,
        loc_key: str,
        reports: list[AgentReport],
    ) -> None:
        """
        Resolve conflicting reports for a single location.

        Uses confidence-weighted voting.
        """
        if not reports:
            return

        # Separate into "blocked" and "clear" reports
        blocked_confidence = 0.0
        clear_confidence = 0.0
        blocked_reports = []
        clear_reports = []

        for report in reports:
            if report.event_type == EventType.ROAD_CLEAR:
                clear_confidence += report.confidence
                clear_reports.append(report)
            else:
                blocked_confidence += report.confidence
                blocked_reports.append(report)

        # Determine winning status
        if blocked_confidence > clear_confidence:
            winning_reports = blocked_reports
            status = "blocked"
            # Get worst event type
            worst_event = max(
                (r.event_type for r in blocked_reports),
                key=lambda e: self.EVENT_WEIGHT_IMPACT.get(e, 1.0),
            )
            weight_multiplier = self.EVENT_WEIGHT_IMPACT.get(worst_event, 1.0)
        else:
            winning_reports = clear_reports
            status = "clear"
            worst_event = EventType.ROAD_CLEAR
            weight_multiplier = 1.0

        # Calculate combined confidence
        combined_confidence = sum(r.confidence for r in winning_reports) / len(
            winning_reports
        )

        # Get most recent update
        latest_report = max(reports, key=lambda r: r.timestamp)

        # Update road status
        self._road_status[loc_key] = {
            "status": status,
            "event_type": worst_event,
            "weight_multiplier": weight_multiplier,
            "confidence": combined_confidence,
            "report_count": len(winning_reports),
            "last_update": latest_report.timestamp,
            "location": latest_report.location,
        }

        # Update road network manager if available
        if self.road_network_manager:
            self.road_network_manager.update_edge_weight_by_location(
                latest_report.location,
                weight_multiplier,
                combined_confidence,
            )

    def get_road_status(self, location: Location) -> dict | None:
        """
        Get current status of road near a location.

        Args:
            location: Location to query

        Returns:
            Status dict or None if no information
        """
        loc_key = f"{location.lat:.3f},{location.lon:.3f}"
        return self._road_status.get(loc_key)

    def get_blocked_roads(self) -> list[dict]:
        """Get all roads currently marked as blocked."""
        return [
            {"location_key": k, **v}
            for k, v in self._road_status.items()
            if v["status"] == "blocked"
        ]

    def get_damaged_roads(self) -> list[dict]:
        """Get all roads with damage (slow but passable)."""
        return [
            {"location_key": k, **v}
            for k, v in self._road_status.items()
            if v["weight_multiplier"] > 1.0 and v["weight_multiplier"] < float("inf")
        ]

    def clear_status(self) -> None:
        """Clear all road status information."""
        self._road_status = {}
        self._pending_updates = []
