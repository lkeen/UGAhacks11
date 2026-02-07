"""Database connection and utilities."""

import os
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .schema import Base, Road, Event, Shelter, Delivery, AgentReportModel


class Database:
    """Database manager for disaster relief optimizer."""

    def __init__(self, db_url: str | None = None):
        """
        Initialize database connection.

        Args:
            db_url: SQLAlchemy database URL. Defaults to SQLite in data directory.
        """
        if db_url is None:
            db_path = Path(__file__).parent.parent / "data" / "disaster_relief.db"
            db_url = f"sqlite:///{db_path}"

        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all tables from the database."""
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def session(self):
        """Get a database session context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    # Event operations
    def add_event(
        self,
        session: Session,
        event_id: str,
        event_type: str,
        lat: float,
        lon: float,
        description: str,
        source: str,
        timestamp: datetime | None = None,
        confidence: float = 0.5,
        **kwargs,
    ) -> Event:
        """Add a new event to the database."""
        event = Event(
            event_id=event_id,
            event_type=event_type,
            lat=lat,
            lon=lon,
            description=description,
            source=source,
            timestamp=timestamp or datetime.utcnow(),
            confidence=confidence,
            **kwargs,
        )
        session.add(event)
        return event

    def get_events_by_type(
        self,
        session: Session,
        event_type: str,
        active_only: bool = True,
    ) -> list[Event]:
        """Get all events of a specific type."""
        query = session.query(Event).filter(Event.event_type == event_type)
        if active_only:
            query = query.filter(Event.is_active == True)
        return query.all()

    def get_events_in_timerange(
        self,
        session: Session,
        start: datetime,
        end: datetime,
        event_type: str | None = None,
    ) -> list[Event]:
        """Get events within a time range."""
        query = session.query(Event).filter(
            Event.timestamp >= start,
            Event.timestamp <= end,
        )
        if event_type:
            query = query.filter(Event.event_type == event_type)
        return query.order_by(Event.timestamp).all()

    def get_events_near_location(
        self,
        session: Session,
        lat: float,
        lon: float,
        radius_deg: float = 0.1,  # ~11km
    ) -> list[Event]:
        """Get events near a location (simple bounding box query)."""
        return (
            session.query(Event)
            .filter(
                Event.lat >= lat - radius_deg,
                Event.lat <= lat + radius_deg,
                Event.lon >= lon - radius_deg,
                Event.lon <= lon + radius_deg,
            )
            .all()
        )

    # Shelter operations
    def add_shelter(
        self,
        session: Session,
        shelter_id: str,
        name: str,
        lat: float,
        lon: float,
        capacity: int,
        **kwargs,
    ) -> Shelter:
        """Add a new shelter to the database."""
        shelter = Shelter(
            shelter_id=shelter_id,
            name=name,
            lat=lat,
            lon=lon,
            capacity=capacity,
            **kwargs,
        )
        session.add(shelter)
        return shelter

    def get_open_shelters(self, session: Session) -> list[Shelter]:
        """Get all currently open shelters."""
        return session.query(Shelter).filter(Shelter.status == "open").all()

    def get_shelters_with_needs(self, session: Session) -> list[Shelter]:
        """Get shelters that have supply needs."""
        return (
            session.query(Shelter)
            .filter(Shelter.status == "open")
            .filter(Shelter.needs != None)
            .filter(Shelter.needs != [])
            .all()
        )

    def update_shelter_occupancy(
        self,
        session: Session,
        shelter_id: str,
        occupancy: int,
    ) -> Shelter | None:
        """Update shelter occupancy count."""
        shelter = (
            session.query(Shelter).filter(Shelter.shelter_id == shelter_id).first()
        )
        if shelter:
            shelter.current_occupancy = occupancy
            if occupancy >= shelter.capacity:
                shelter.status = "full"
        return shelter

    # Road operations
    def update_road_status(
        self,
        session: Session,
        osm_id: str,
        status: str,
        weight_multiplier: float,
        confidence: float = 1.0,
        source: str = "agent",
    ) -> Road | None:
        """Update road status and weight."""
        road = session.query(Road).filter(Road.osm_id == osm_id).first()
        if road:
            road.status = status
            road.weight_multiplier = weight_multiplier
            road.status_confidence = confidence
            road.status_source = source
            road.last_status_update = datetime.utcnow()
        return road

    def get_blocked_roads(self, session: Session) -> list[Road]:
        """Get all roads currently marked as closed."""
        return session.query(Road).filter(Road.status == "closed").all()

    def get_damaged_roads(self, session: Session) -> list[Road]:
        """Get all roads with damage (slow but passable)."""
        return (
            session.query(Road)
            .filter(Road.status == "damaged")
            .filter(Road.weight_multiplier > 1.0)
            .all()
        )

    # Delivery operations
    def add_delivery(
        self,
        session: Session,
        delivery_id: str,
        origin_name: str,
        origin_lat: float,
        origin_lon: float,
        shelter_id: int,
        supplies: dict,
        **kwargs,
    ) -> Delivery:
        """Add a new delivery plan."""
        delivery = Delivery(
            delivery_id=delivery_id,
            origin_name=origin_name,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            shelter_id=shelter_id,
            supplies=supplies,
            **kwargs,
        )
        session.add(delivery)
        return delivery

    def get_pending_deliveries(self, session: Session) -> list[Delivery]:
        """Get all planned deliveries not yet dispatched."""
        return (
            session.query(Delivery)
            .filter(Delivery.status == "planned")
            .order_by(Delivery.priority)
            .all()
        )

    # Agent report operations
    def add_agent_report(
        self,
        session: Session,
        report_id: str,
        agent_name: str,
        event_type: str,
        lat: float,
        lon: float,
        description: str,
        confidence: float,
        source: str,
        timestamp: datetime | None = None,
        **kwargs,
    ) -> AgentReportModel:
        """Add a raw agent report to the database."""
        report = AgentReportModel(
            report_id=report_id,
            agent_name=agent_name,
            event_type=event_type,
            lat=lat,
            lon=lon,
            description=description,
            raw_confidence=confidence,
            adjusted_confidence=confidence,
            source=source,
            timestamp=timestamp or datetime.utcnow(),
            **kwargs,
        )
        session.add(report)
        return report

    def get_unprocessed_reports(self, session: Session) -> list[AgentReportModel]:
        """Get all agent reports not yet processed into events."""
        return (
            session.query(AgentReportModel)
            .filter(AgentReportModel.processed == False)
            .order_by(AgentReportModel.timestamp)
            .all()
        )


# Global database instance
_db: Database | None = None


def get_db() -> Database:
    """Get or create the global database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db
