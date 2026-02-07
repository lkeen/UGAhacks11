#!/usr/bin/env python3
"""
Initialize the SQLite database with schema.

Usage:
    python scripts/init_database.py

Output:
    backend/data/disaster_relief.db
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import Database


def init_database():
    """Initialize the database with schema."""
    print("Initializing database...")

    # Ensure data directory exists
    data_dir = Path(__file__).parent.parent / "backend" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    db_path = data_dir / "disaster_relief.db"

    # Create database
    db = Database(f"sqlite:///{db_path}")

    # Drop existing tables if any
    print("Dropping existing tables...")
    db.drop_tables()

    # Create new tables
    print("Creating tables...")
    db.create_tables()

    print(f"\nDatabase initialized at: {db_path}")
    print("\nTables created:")
    print("  - roads (OSM road segments with dynamic status)")
    print("  - events (timestamped disaster events)")
    print("  - shelters (emergency shelter locations)")
    print("  - deliveries (planned supply deliveries)")
    print("  - agent_reports (raw agent outputs)")

    return True


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
