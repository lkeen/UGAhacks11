# Disaster Relief Supply Chain Optimizer

A multi-agent AI system that optimizes disaster relief supply chain logistics by aggregating real-time data from satellites, social media, and official sources.

## Demo Scenario

**Hurricane Helene (September 2024, Western North Carolina)**
- Simulates the first 48 hours post-landfall
- Shows multi-agent coordination discovering road closures, shelter needs, and infrastructure damage
- Generates optimized delivery routes avoiding hazards

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/lkeen/UGAhacks11.git
cd UGAhacks11

# Copy environment file and add your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run both backend and frontend
docker compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

To stop: `docker compose down`

### Option 2: Local Development

#### Prerequisites
- Python 3.11+
- Node.js 18+

#### System Dependencies

**Fedora/RHEL:**
```bash
sudo dnf install gdal gdal-devel geos geos-devel proj proj-devel python3-devel gcc
```

**Ubuntu/Debian:**
```bash
sudo apt install gdal-bin libgdal-dev libgeos-dev libproj-dev python3-dev gcc
```

**macOS:**
```bash
brew install gdal geos proj
```

#### Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Initialize database
python scripts/init_database.py

# Load sample data
python scripts/load_events.py

# Start the API server
python -m uvicorn backend.api.main:app --reload --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

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
UGAhacks11/
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
│   ├── database/             # SQLite schema
│   ├── api/                  # FastAPI endpoints
│   └── Dockerfile
├── frontend/                 # Next.js dashboard
│   ├── src/
│   │   ├── app/              # Next.js app router
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom React hooks
│   │   └── types/            # TypeScript definitions
│   ├── package.json
│   └── Dockerfile
├── scripts/                  # Data & setup utilities
│   ├── init_database.py      # Create SQLite tables
│   ├── load_events.py        # Load sample disaster data
│   ├── download_osm.py       # Download road network
│   └── download_satellite.py # Download satellite imagery
├── docker-compose.yml
├── requirements.txt
└── .env.example
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

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Claude API key for orchestrator | Yes |
| `DATABASE_URL` | SQLite database path (default: auto) | No |
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: http://localhost:8000) | No |
| `COPERNICUS_USER` | Copernicus Hub username (for satellite data) | No |
| `COPERNICUS_PASSWORD` | Copernicus Hub password | No |

## Troubleshooting

### Database Issues
```bash
# Reset the database
rm backend/data/disaster_relief.db
python scripts/init_database.py
python scripts/load_events.py
```

### Docker Permission Issues
```bash
# If database was created by Docker with root permissions
sudo rm backend/data/disaster_relief.db
```

### Missing System Libraries (GDAL errors)
See the System Dependencies section above for your OS.

## License

MIT License - Built for UGAhacks 11
