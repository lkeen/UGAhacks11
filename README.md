# Disaster Relief Supply Chain Optimizer

A multi-agent AI system that optimizes disaster relief supply chain logistics by aggregating real-time data from satellites, social media, and official sources.

## Demo Scenario

**Hurricane Helene (September 2024, Western North Carolina)**
- Simulates the first 48 hours post-landfall
- Shows multi-agent coordination discovering road closures, shelter needs, and infrastructure damage
- Generates optimized delivery routes avoiding hazards

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (optional, for easy setup)

### Installation

```bash
# Clone the repository
git clone https://github.com/lkeen/UGAhacks11.git
cd UGAhacks11

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Data Setup

```bash
# Download OpenStreetMap road network for Western NC
python scripts/download_osm.py

# Download satellite imagery (requires Copernicus account)
python scripts/download_satellite.py

# Initialize database with schema
python scripts/init_database.py

# Load mock disaster events
python scripts/load_events.py
```

### Run the Demo

```bash
# Start the API server
uvicorn backend.api.main:app --reload

# Or run the CLI demo
python -m backend.orchestrator.cli
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                            │
│                   (Claude Sonnet API)                        │
│  "I have 200 water cases at Asheville depot, where should   │
│   they go?"                                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ Queries
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐    ┌──────────┐
│Satellite│    │Social Media │    │ Official │
│  Agent  │    │   Agent     │    │   Agent  │
└────┬────┘    └──────┬──────┘    └────┬─────┘
     │                │                 │
     └────────────────┼─────────────────┘
                      ▼
            ┌─────────────────┐
            │  Road Network   │
            │    Manager      │
            └────────┬────────┘
                     ▼
            ┌─────────────────┐
            │ Routing Engine  │
            │  (NetworkX)     │
            └────────┬────────┘
                     ▼
            ┌─────────────────┐
            │ Delivery Plan   │
            └─────────────────┘
```

## Project Structure

```
disaster-relief-optimizer/
├── backend/
│   ├── agents/               # Multi-agent implementations
│   │   ├── base_agent.py     # Abstract base class
│   │   ├── satellite_agent.py
│   │   ├── social_media_agent.py
│   │   ├── official_data_agent.py
│   │   └── road_network_agent.py
│   ├── orchestrator/         # Claude-powered coordinator
│   ├── routing/              # Graph algorithms
│   ├── data/                 # Local data storage
│   ├── database/             # SQLite + SpatiaLite
│   └── api/                  # FastAPI endpoints
├── frontend/                 # React dashboard (Phase 2)
├── scripts/                  # Data download utilities
├── tests/
├── docker-compose.yml
└── requirements.txt
```

## Agents

| Agent | Data Source | Latency | Confidence |
|-------|-------------|---------|------------|
| Satellite | Sentinel-2 imagery | Hours | High (0.9) |
| Social Media | Twitter/Reddit | Minutes | Medium (0.6) |
| Official | FEMA, NCDOT | Hours-Days | Very High (0.95) |
| Road Network | OSM + Agent Reports | Real-time | Weighted |

## API Endpoints

- `GET /health` - Health check
- `POST /query` - Submit natural language query
- `GET /events` - List disaster events
- `GET /shelters` - List shelters and needs
- `POST /route` - Calculate optimal route
- `GET /map` - Get current situation map

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key for orchestrator |
| `DATABASE_URL` | SQLite database path |
| `COPERNICUS_USER` | Copernicus Open Access Hub username |
| `COPERNICUS_PASSWORD` | Copernicus Open Access Hub password |

## License

MIT License - Built for UGAhacks 11
