"""Database schema for disaster relief optimizer."""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Text,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Road(Base):
    """Road segments from OpenStreetMap with dynamic status."""

    __tablename__ = "roads"

    id = Column(Integer, primary_key=True)
    osm_id = Column(String(50), unique=True, index=True)
    name = Column(String(255))
    highway_type = Column(String(50))  # motorway, primary, secondary, etc.

    # Geometry stored as WKT (Well-Known Text) for simplicity
    # In production, would use PostGIS geometry type
    geometry_wkt = Column(Text)

    # Start and end coordinates
    start_lat = Column(Float)
    start_lon = Column(Float)
    end_lat = Column(Float)
    end_lon = Column(Float)

    # Road attributes
    length_m = Column(Float)
    lanes = Column(Integer)
    max_speed = Column(Integer)
    surface = Column(String(50))
    oneway = Column(Boolean, default=False)

    # Dynamic status
    status = Column(String(20), default="open")  # open, damaged, closed
    weight_multiplier = Column(Float, default=1.0)
    last_status_update = Column(DateTime)
    status_confidence = Column(Float, default=1.0)
    status_source = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_road_status", "status"),
        Index("idx_road_type", "highway_type"),
    )


class Event(Base):
    """Timestamped disaster events from all sources."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String(50), unique=True, index=True)
    timestamp = Column(DateTime, index=True)

    # Event classification
    event_type = Column(String(50), index=True)
    severity = Column(String(20))  # low, medium, high, critical

    # Location
    lat = Column(Float)
    lon = Column(Float)
    address = Column(String(255))
    affected_radius_m = Column(Float)

    # Description
    title = Column(String(255))
    description = Column(Text)

    # Source information
    source = Column(String(50), index=True)
    source_id = Column(String(100))  # ID from source system
    confidence = Column(Float)
    corroborations = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    verified_by = Column(String(50))
    verified_at = Column(DateTime)

    # Raw data
    raw_data = Column(JSON)
    extra_data = Column(JSON)  # Renamed from 'metadata' (reserved in SQLAlchemy)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_event_location", "lat", "lon"),
        Index("idx_event_active", "is_active", "event_type"),
    )


class Shelter(Base):
    """Emergency shelter locations with capacity and needs."""

    __tablename__ = "shelters"

    id = Column(Integer, primary_key=True)
    shelter_id = Column(String(50), unique=True, index=True)
    name = Column(String(255))

    # Location
    lat = Column(Float)
    lon = Column(Float)
    address = Column(String(255))

    # Capacity
    capacity = Column(Integer)
    current_occupancy = Column(Integer, default=0)

    # Status
    status = Column(String(20), default="closed")  # closed, open, full
    opened_at = Column(DateTime)
    closed_at = Column(DateTime)

    # Needs (stored as JSON array)
    needs = Column(JSON, default=list)
    priority_needs = Column(JSON, default=list)

    # Facilities
    accepts_pets = Column(Boolean, default=False)
    wheelchair_accessible = Column(Boolean, default=True)
    has_generator = Column(Boolean, default=False)
    has_medical = Column(Boolean, default=False)

    # Contact
    contact_phone = Column(String(20))
    contact_name = Column(String(100))
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    deliveries = relationship("Delivery", back_populates="shelter")

    __table_args__ = (Index("idx_shelter_status", "status"),)


class Delivery(Base):
    """Planned and executed supply deliveries."""

    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True)
    delivery_id = Column(String(50), unique=True, index=True)

    # Origin
    origin_name = Column(String(255))
    origin_lat = Column(Float)
    origin_lon = Column(Float)

    # Destination (shelter)
    shelter_id = Column(Integer, ForeignKey("shelters.id"))
    shelter = relationship("Shelter", back_populates="deliveries")

    # Supplies being delivered (JSON object)
    supplies = Column(JSON)  # {"water_cases": 100, "blankets": 50}

    # Route information
    route_geometry = Column(Text)  # WKT LineString
    route_distance_m = Column(Float)
    route_duration_min = Column(Float)
    waypoints = Column(JSON)  # List of lat/lon waypoints

    # Status
    status = Column(String(20), default="planned")  # planned, in_transit, delivered, failed
    priority = Column(Integer, default=5)  # 1-10, 1 is highest

    # Timing
    planned_departure = Column(DateTime)
    actual_departure = Column(DateTime)
    estimated_arrival = Column(DateTime)
    actual_arrival = Column(DateTime)

    # Planning metadata
    planned_by = Column(String(50))  # orchestrator, manual
    planning_reasoning = Column(Text)
    avoided_hazards = Column(JSON)  # List of hazard descriptions

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_delivery_status", "status"),
        Index("idx_delivery_priority", "priority", "status"),
    )


class AgentReportModel(Base):
    """Raw agent outputs with confidence scores."""

    __tablename__ = "agent_reports"

    id = Column(Integer, primary_key=True)
    report_id = Column(String(50), unique=True, index=True)

    # Agent info
    agent_name = Column(String(50), index=True)
    agent_type = Column(String(50))

    # Report content
    timestamp = Column(DateTime, index=True)
    event_type = Column(String(50))
    lat = Column(Float)
    lon = Column(Float)
    description = Column(Text)

    # Confidence
    raw_confidence = Column(Float)
    adjusted_confidence = Column(Float)
    confidence_factors = Column(JSON)

    # Source
    source = Column(String(50))
    source_id = Column(String(100))
    corroborations = Column(Integer, default=0)

    # Processing
    processed = Column(Boolean, default=False)
    linked_event_id = Column(Integer, ForeignKey("events.id"))
    linked_road_id = Column(Integer, ForeignKey("roads.id"))

    # Raw data
    raw_data = Column(JSON)
    extra_data = Column(JSON)  # Renamed from 'metadata' (reserved in SQLAlchemy)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_report_agent", "agent_name", "timestamp"),
        Index("idx_report_location", "lat", "lon"),
    )
