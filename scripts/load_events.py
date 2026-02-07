#!/usr/bin/env python3
"""
Load mock disaster events into the database.

Usage:
    python scripts/load_events.py

Loads:
    - Disaster events from helene_timeline.json
    - Shelter data from shelters.json
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import Database


def load_events():
    """Load events from JSON files into database."""
    data_dir = Path(__file__).parent.parent / "backend" / "data"

    # Initialize database connection
    db = Database()

    # Load events timeline
    events_file = data_dir / "events" / "helene_timeline.json"
    if events_file.exists():
        print(f"Loading events from {events_file}...")
        with open(events_file) as f:
            data = json.load(f)

        events = data.get("events", [])

        with db.session() as session:
            for event in events:
                db.add_event(
                    session,
                    event_id=event["id"],
                    event_type=event["type"],
                    lat=event["location"]["lat"],
                    lon=event["location"]["lon"],
                    description=event.get("description", ""),
                    source=event.get("source", "unknown"),
                    timestamp=datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")),
                    confidence=event.get("confidence", 0.5),
                    raw_data=event,
                )

        print(f"  Loaded {len(events)} events")
    else:
        print(f"Events file not found: {events_file}")

    # Load shelters
    shelters_file = data_dir / "shelters" / "shelters.json"
    if shelters_file.exists():
        print(f"\nLoading shelters from {shelters_file}...")
        with open(shelters_file) as f:
            data = json.load(f)

        shelters = data.get("shelters", [])

        with db.session() as session:
            for shelter in shelters:
                # Parse opened_at if present
                opened_at = None
                if shelter.get("opened_at"):
                    opened_at = datetime.fromisoformat(
                        shelter["opened_at"].replace("Z", "+00:00")
                    )

                db.add_shelter(
                    session,
                    shelter_id=shelter["id"],
                    name=shelter["name"],
                    lat=shelter["location"]["lat"],
                    lon=shelter["location"]["lon"],
                    capacity=shelter.get("capacity", 0),
                    address=shelter.get("address"),
                    current_occupancy=shelter.get("current_occupancy", 0),
                    status="open" if opened_at else "closed",
                    opened_at=opened_at,
                    needs=shelter.get("needs", []),
                    accepts_pets=shelter.get("accepts_pets", False),
                    wheelchair_accessible=shelter.get("wheelchair_accessible", True),
                    has_generator=shelter.get("has_generator", False),
                    contact_phone=shelter.get("contact"),
                )

        print(f"  Loaded {len(shelters)} shelters")
    else:
        print(f"Shelters file not found: {shelters_file}")

    print("\nData loading complete!")
    return True


def query_sample_data():
    """Query and display sample data to verify loading."""
    print("\n" + "=" * 50)
    print("SAMPLE DATA VERIFICATION")
    print("=" * 50)

    db = Database()

    with db.session() as session:
        # Query events
        from backend.database.schema import Event, Shelter

        # Road closures
        road_closures = session.query(Event).filter(
            Event.event_type == "road_closure"
        ).all()
        print(f"\nRoad closures: {len(road_closures)}")
        for event in road_closures[:3]:
            print(f"  - {event.timestamp}: {event.description[:60]}...")

        # Flooding events
        floods = session.query(Event).filter(Event.event_type == "flooding").all()
        print(f"\nFlooding events: {len(floods)}")

        # Open shelters
        shelters = session.query(Shelter).filter(Shelter.status == "open").all()
        print(f"\nOpen shelters: {len(shelters)}")
        for shelter in shelters[:3]:
            needs = shelter.needs if shelter.needs else []
            print(f"  - {shelter.name}: capacity {shelter.capacity}, needs: {', '.join(needs[:3])}")


if __name__ == "__main__":
    success = load_events()
    if success:
        query_sample_data()
    sys.exit(0 if success else 1)
