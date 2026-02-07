"""Base agent class for disaster relief intelligence gathering."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class EventType(str, Enum):
    """Types of disaster events that agents can report."""
    ROAD_CLOSURE = "road_closure"
    ROAD_DAMAGE = "road_damage"
    ROAD_CLEAR = "road_clear"
    FLOODING = "flooding"
    BRIDGE_COLLAPSE = "bridge_collapse"
    SHELTER_OPENING = "shelter_opening"
    SHELTER_CLOSING = "shelter_closing"
    SHELTER_NEED = "shelter_need"
    POWER_OUTAGE = "power_outage"
    INFRASTRUCTURE_DAMAGE = "infrastructure_damage"
    RESCUE_NEEDED = "rescue_needed"
    SUPPLIES_NEEDED = "supplies_needed"


class DataSource(str, Enum):
    """Sources of intelligence data."""
    SATELLITE = "satellite"
    TWITTER = "twitter"
    REDDIT = "reddit"
    FEMA = "fema"
    NCDOT = "ncdot"
    USGS = "usgs"
    LOCAL_EMERGENCY = "local_emergency"
    NEWS = "news"
    CITIZEN_REPORT = "citizen_report"


@dataclass
class Location:
    """Geographic location with optional address."""
    lat: float
    lon: float
    address: str | None = None

    def to_dict(self) -> dict:
        return {"lat": self.lat, "lon": self.lon, "address": self.address}

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        return cls(lat=data["lat"], lon=data["lon"], address=data.get("address"))


@dataclass
class BoundingBox:
    """Geographic bounding box for queries."""
    west: float
    south: float
    east: float
    north: float

    def contains(self, location: Location) -> bool:
        """Check if a location is within this bounding box."""
        return (
            self.west <= location.lon <= self.east
            and self.south <= location.lat <= self.north
        )

    def to_tuple(self) -> tuple[float, float, float, float]:
        """Return as (west, south, east, north) tuple."""
        return (self.west, self.south, self.east, self.north)

    def to_dict(self) -> dict:
        return {
            "west": self.west,
            "south": self.south,
            "east": self.east,
            "north": self.north,
        }


# Default bounding box for Western NC (Asheville region)
WESTERN_NC_BBOX = BoundingBox(
    west=-83.5,
    south=35.0,
    east=-81.5,
    north=36.5,
)


@dataclass
class AgentReport:
    """Standardized report from any agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: EventType = EventType.ROAD_CLOSURE
    location: Location = field(default_factory=lambda: Location(0, 0))
    description: str = ""
    source: DataSource = DataSource.CITIZEN_REPORT
    confidence: float = 0.5
    raw_data: dict = field(default_factory=dict)
    corroborations: int = 0
    agent_name: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert report to dictionary for storage/serialization."""
        import math

        def sanitize_floats(obj):
            """Replace inf/nan with JSON-safe values."""
            if isinstance(obj, float):
                if math.isinf(obj):
                    return None  # or "infinite" if you want a string
                if math.isnan(obj):
                    return None
                return obj
            if isinstance(obj, dict):
                return {k: sanitize_floats(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize_floats(v) for v in obj]
            return obj

        return sanitize_floats({
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "location": self.location.to_dict(),
            "description": self.description,
            "source": self.source.value,
            "confidence": self.confidence,
            "raw_data": self.raw_data,
            "corroborations": self.corroborations,
            "agent_name": self.agent_name,
            "metadata": self.metadata,
        })

    @classmethod
    def from_dict(cls, data: dict) -> "AgentReport":
        """Create report from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data.get("timestamp"), str) else data.get("timestamp", datetime.utcnow()),
            event_type=EventType(data["event_type"]) if isinstance(data.get("event_type"), str) else data.get("event_type", EventType.ROAD_CLOSURE),
            location=Location.from_dict(data["location"]) if isinstance(data.get("location"), dict) else data.get("location", Location(0, 0)),
            description=data.get("description", ""),
            source=DataSource(data["source"]) if isinstance(data.get("source"), str) else data.get("source", DataSource.CITIZEN_REPORT),
            confidence=data.get("confidence", 0.5),
            raw_data=data.get("raw_data", {}),
            corroborations=data.get("corroborations", 0),
            agent_name=data.get("agent_name", ""),
            metadata=data.get("metadata", {}),
        )


class BaseAgent(ABC):
    """Abstract base class for all intelligence agents."""

    def __init__(self, name: str, confidence_weight: float = 1.0):
        """
        Initialize an agent.

        Args:
            name: Human-readable name for this agent
            confidence_weight: Multiplier for confidence scores (higher = more trusted)
        """
        self.name = name
        self.confidence_weight = confidence_weight
        self._reports: list[AgentReport] = []

    @property
    def reports(self) -> list[AgentReport]:
        """Get all reports gathered by this agent."""
        return self._reports

    @abstractmethod
    async def gather_intelligence(
        self,
        scenario_time: datetime,
        bbox: BoundingBox,
    ) -> list[AgentReport]:
        """
        Query data sources and return structured events.

        Args:
            scenario_time: The current time in the disaster scenario
            bbox: Geographic bounding box to search within

        Returns:
            List of AgentReport objects with structured event data
        """
        pass

    @abstractmethod
    def assess_confidence(self, report: AgentReport) -> float:
        """
        Calculate final confidence score for a report.

        Args:
            report: The report to assess

        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass

    def get_reports_by_type(self, event_type: EventType) -> list[AgentReport]:
        """Filter reports by event type."""
        return [r for r in self._reports if r.event_type == event_type]

    def get_reports_in_timerange(
        self,
        start: datetime,
        end: datetime,
    ) -> list[AgentReport]:
        """Filter reports by time range."""
        return [r for r in self._reports if start <= r.timestamp <= end]

    def get_reports_near_location(
        self,
        location: Location,
        radius_km: float = 5.0,
    ) -> list[AgentReport]:
        """
        Filter reports within radius of a location.

        Uses simple Euclidean distance approximation (good enough for small areas).
        """
        # Approximate km per degree at this latitude
        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * abs(location.lat * 3.14159 / 180)

        results = []
        for report in self._reports:
            dlat = (report.location.lat - location.lat) * km_per_deg_lat
            dlon = (report.location.lon - location.lon) * km_per_deg_lon
            distance = (dlat**2 + dlon**2) ** 0.5
            if distance <= radius_km:
                results.append(report)
        return results

    def clear_reports(self) -> None:
        """Clear all stored reports."""
        self._reports = []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', reports={len(self._reports)})"
