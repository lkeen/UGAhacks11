"""Satellite Intelligence Agent for disaster relief coordination."""

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


class SatelliteAgent(BaseAgent):
    """
    Agent that analyzes satellite imagery to detect disaster damage.

    Compares pre-disaster and post-disaster imagery to detect:
    - Flooded areas (water where there wasn't before)
    - Road damage/blockages
    - Infrastructure damage
    - Landslides

    For the demo, we use pre-computed detections from a mock dataset.
    In production, would use real change detection algorithms on
    Sentinel-2 or other satellite imagery.
    """

    # Detection types and their default confidence
    DETECTION_CONFIDENCE = {
        "flooding": 0.90,
        "road_damage": 0.85,
        "bridge_damage": 0.88,
        "landslide": 0.80,
        "building_damage": 0.75,
        "debris": 0.70,
    }

    def __init__(
        self,
        name: str = "SatelliteAgent",
        confidence_weight: float = 0.9,
        detections_path: str | Path | None = None,
    ):
        """
        Initialize the Satellite Agent.

        Args:
            name: Agent name
            confidence_weight: Base confidence multiplier (high for satellite)
            detections_path: Path to pre-computed detections JSON
        """
        super().__init__(name, confidence_weight)
        self.detections_path = Path(detections_path) if detections_path else None
        self._detections: list[dict] = []

    def load_detections(self, filepath: str | Path) -> None:
        """Load pre-computed satellite detections from JSON file."""
        filepath = Path(filepath)
        if filepath.exists():
            with open(filepath) as f:
                data = json.load(f)
                self._detections = data.get("detections", [])

    async def gather_intelligence(
        self,
        scenario_time: datetime,
        bbox: BoundingBox,
    ) -> list[AgentReport]:
        """
        Gather intelligence from satellite imagery analysis.

        For the demo, returns pre-computed detections.
        In production, would run change detection on real imagery.

        Args:
            scenario_time: Current time in the disaster scenario
            bbox: Geographic area to analyze

        Returns:
            List of structured reports from satellite analysis
        """
        # Clear previous reports to avoid duplicates
        self._reports = []
        reports = []
        seen_ids = set()

        # Load detections if path set and not loaded
        if self.detections_path and not self._detections:
            self.load_detections(self.detections_path)

        for detection in self._detections:
            # Skip duplicates
            if detection["id"] in seen_ids:
                continue
            seen_ids.add(detection["id"])
            # Parse detection timestamp (when imagery was captured)
            detection_time = datetime.fromisoformat(
                detection["timestamp"].replace("Z", "+00:00")
            )

            # Skip detections after scenario time
            if detection_time > scenario_time:
                continue

            # Check if detection is in bounding box
            location = Location(
                lat=detection["location"]["lat"],
                lon=detection["location"]["lon"],
            )
            if not bbox.contains(location):
                continue

            # Map detection type to event type
            event_type = self._map_detection_to_event(detection["type"])
            if event_type is None:
                continue

            # Get confidence from detection or use default
            confidence = detection.get(
                "confidence",
                self.DETECTION_CONFIDENCE.get(detection["type"], 0.75),
            )

            # Create report
            report = AgentReport(
                timestamp=detection_time,
                event_type=event_type,
                location=location,
                description=detection.get("description", f"Satellite detected: {detection['type']}"),
                source=DataSource.SATELLITE,
                confidence=confidence,
                raw_data=detection,
                agent_name=self.name,
                metadata={
                    "detection_type": detection["type"],
                    "imagery_source": detection.get("imagery_source", "sentinel-2"),
                    "tile_id": detection.get("tile_id"),
                    "area_sqm": detection.get("area_sqm"),
                    "pre_image_date": detection.get("pre_image_date"),
                    "post_image_date": detection.get("post_image_date"),
                },
            )

            reports.append(report)
            self._reports.append(report)

        return reports

    def assess_confidence(self, report: AgentReport) -> float:
        """
        Calculate final confidence score for a satellite detection.

        Satellite imagery is generally high confidence, but can be
        affected by cloud cover, resolution, and detection algorithm accuracy.
        """
        base_confidence = report.confidence

        # Apply agent weight (satellite is trusted)
        final_confidence = base_confidence * self.confidence_weight

        # Slight reduction if detection area is small (might be noise)
        area = report.metadata.get("area_sqm", 1000)
        if area < 100:
            final_confidence *= 0.8
        elif area < 500:
            final_confidence *= 0.9

        return max(0.0, min(1.0, final_confidence))

    def _map_detection_to_event(self, detection_type: str) -> EventType | None:
        """Map satellite detection type to standardized event type."""
        mapping = {
            "flooding": EventType.FLOODING,
            "road_damage": EventType.ROAD_DAMAGE,
            "road_blocked": EventType.ROAD_CLOSURE,
            "bridge_damage": EventType.BRIDGE_COLLAPSE,
            "landslide": EventType.ROAD_CLOSURE,
            "debris": EventType.ROAD_DAMAGE,
            "building_damage": EventType.INFRASTRUCTURE_DAMAGE,
        }
        return mapping.get(detection_type)

    def analyze_imagery(
        self,
        pre_image_path: str,
        post_image_path: str,
    ) -> list[dict]:
        """
        Analyze pre/post disaster imagery for changes.

        This is a placeholder for real change detection.
        In production, would use rasterio to load GeoTIFFs and
        compute NDWI (water index) or other change detection metrics.

        Args:
            pre_image_path: Path to pre-disaster GeoTIFF
            post_image_path: Path to post-disaster GeoTIFF

        Returns:
            List of detection dictionaries
        """
        # TODO: Implement real change detection
        # For now, return empty (use mock data instead)
        return []

    def detect_flooding_ndwi(self, pre_ndwi: float, post_ndwi: float) -> bool:
        """
        Detect flooding using Normalized Difference Water Index.

        NDWI = (Green - NIR) / (Green + NIR)
        Water typically has NDWI > 0, while land has NDWI < 0.

        Args:
            pre_ndwi: NDWI value before disaster
            post_ndwi: NDWI value after disaster

        Returns:
            True if flooding likely detected
        """
        # Significant increase in NDWI suggests new water
        return post_ndwi - pre_ndwi > 0.3 and post_ndwi > 0
