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
        # Clear previous reports to avoid duplicates
        self._reports = []

        # Process any pending updates
        self._process_pending_updates()

        # Return current road status as reports
        reports = []
        seen_ids = set()
        for edge_id, status in self._road_status.items():
            # Skip duplicates
            if edge_id in seen_ids:
                continue
            seen_ids.add(edge_id)
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
        """Receive multiple updates at once. Clears previous pending updates first."""
        self._pending_updates = []
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

        Uses timestamp-based priority: newer reports override older ones.
        Road_clear events remove previous hazards.
        """
        if not reports:
            return

        # Sort reports by timestamp (newest first)
        sorted_reports = sorted(reports, key=lambda r: r.timestamp, reverse=True)
        latest_report = sorted_reports[0]

        # Check if the most recent report is a road_clear
        if latest_report.event_type == EventType.ROAD_CLEAR:
            # Only trust the ROAD_CLEAR if no hazard report has higher confidence
            hazard_reports = [r for r in sorted_reports if r.event_type != EventType.ROAD_CLEAR]
            higher_conf_hazard = [r for r in hazard_reports if r.confidence > latest_report.confidence]

            if not higher_conf_hazard:
                # ROAD_CLEAR wins — remove this location from road status
                if loc_key in self._road_status:
                    del self._road_status[loc_key]

                # Reset road network if manager available
                if self.road_network_manager:
                    self.road_network_manager.update_edge_weight_by_location(
                        latest_report.location,
                        1.0,  # Normal weight
                        latest_report.confidence,
                    )
                return
            # Fall through to hazard processing below

        # Use the most recent hazard report
        hazard_reports = [r for r in sorted_reports if r.event_type != EventType.ROAD_CLEAR]

        if not hazard_reports:
            return

        latest_hazard = hazard_reports[0]
        weight_multiplier = self.EVENT_WEIGHT_IMPACT.get(latest_hazard.event_type, 1.0)

        if weight_multiplier == float("inf"):
            status = "blocked"
        elif weight_multiplier > 1.0:
            status = "damaged"
        else:
            status = "clear"

        # Update road status
        self._road_status[loc_key] = {
            "status": status,
            "event_type": latest_hazard.event_type,
            "weight_multiplier": weight_multiplier,
            "confidence": latest_hazard.confidence,
            "report_count": len(hazard_reports),
            "last_update": latest_hazard.timestamp,
            "location": latest_hazard.location,
        }

        # Update road network manager if available
        if self.road_network_manager:
            self.road_network_manager.update_edge_weight_by_location(
                latest_hazard.location,
                weight_multiplier,
                latest_hazard.confidence,
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
