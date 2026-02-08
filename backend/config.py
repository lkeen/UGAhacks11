"""Centralized configuration for the disaster relief optimizer."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")


# API Keys
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///backend/data/disaster_relief.db")

# Data paths
DATA_DIR: Path = Path(__file__).parent / "data"

# Bounding box for Western NC
BBOX_WEST: float = float(os.getenv("BBOX_WEST", "-83.5"))
BBOX_SOUTH: float = float(os.getenv("BBOX_SOUTH", "35.0"))
BBOX_EAST: float = float(os.getenv("BBOX_EAST", "-81.5"))
BBOX_NORTH: float = float(os.getenv("BBOX_NORTH", "36.5"))

# Agent confidence weights
SATELLITE_CONFIDENCE_WEIGHT: float = 0.90
SOCIAL_MEDIA_CONFIDENCE_WEIGHT: float = 0.70
OFFICIAL_DATA_CONFIDENCE_WEIGHT: float = 0.85

# Conflict resolution thresholds
CONFLICT_PROXIMITY_KM: float = 0.5
CONSENSUS_MIN_REPORTS: int = 2

# Claude model settings
CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
CLAUDE_MAX_TOKENS: int = 1024
