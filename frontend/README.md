# Disaster Relief Optimizer - Frontend

Next.js frontend for the Disaster Relief Supply Chain Optimizer.

## Quick Start

```bash
# Install dependencies
npm install

# Set up environment variables (copy from project root)
# Add NEXT_PUBLIC_MAPBOX_TOKEN and NEXT_PUBLIC_API_URL to .env.local
# See ../.env.example for all available variables

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: http://localhost:8000) | No |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Mapbox access token for map display | Yes |

Get a free Mapbox token at [mapbox.com](https://mapbox.com).

## Features

### Implemented (Skeleton)

- **Dashboard Layout**: Header, sidebar, map area, agent logs panel, status bar
- **Map Component**: Mapbox GL JS integration with markers and route display
- **Query Panel**: Natural language query input with example queries
- **Shelter List**: View shelters with occupancy and needs indicators
- **Event Summary**: Grouped events by type
- **Agent Logs**: Real-time agent activity display
- **Scenario Time Controls**: Set and advance simulation time
- **API Client**: TypeScript client for all backend endpoints

### TODO (Pending Backend APIs)

- [ ] WebSocket/real-time updates (backend needs WebSocket support)
- [ ] Event marker display on map (needs GeoJSON from events endpoint)
- [ ] Road status overlay (blocked/damaged roads visualization)
- [ ] Filter panel implementation (event types, sources, time range)
- [ ] Shelter detail panel with delivery planning
- [ ] Route visualization with waypoints and hazards
- [ ] Delivery status tracking
- [ ] Agent report drill-down view
- [ ] Historical playback controls

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js app router
│   │   ├── layout.tsx       # Root layout
│   │   ├── page.tsx         # Main dashboard page
│   │   └── globals.css      # Global styles
│   ├── components/          # React components
│   │   ├── Header.tsx       # Top navigation bar
│   │   ├── Sidebar.tsx      # Left panel (shelters, events)
│   │   ├── Map.tsx          # Mapbox GL map
│   │   ├── QueryPanel.tsx   # Query input and results
│   │   ├── AgentLogs.tsx    # Right panel (logs, reports)
│   │   ├── StatusBar.tsx    # Bottom status bar
│   │   └── ShelterDetail.tsx # Shelter detail overlay
│   ├── lib/                 # Utilities
│   │   └── api.ts           # API client
│   ├── hooks/               # Custom React hooks
│   │   └── useApi.ts        # Data fetching hooks
│   └── types/               # TypeScript definitions
│       └── index.ts         # All type definitions
├── package.json
├── next.config.js
├── tailwind.config.ts
└── Dockerfile
```

## API Integration

The frontend expects the backend API at `NEXT_PUBLIC_API_URL`. Key endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/query` | POST | Submit natural language query |
| `/events` | GET | List disaster events |
| `/shelters` | GET | List shelters |
| `/route` | POST | Calculate route |
| `/network/status` | GET | Get road network status |
| `/intelligence` | GET | Gather agent reports |
| `/scenario/time` | POST | Set simulation time |
| `/scenario/advance` | POST | Advance simulation time |

## Development Notes

- Uses Tailwind CSS for styling
- TypeScript for type safety (types mirror backend models)
- Components are client-side rendered ('use client' directive)
- Map requires Mapbox token - shows placeholder without it
- Polling used for updates (WebSocket support planned)

## Docker

```bash
# Build and run with docker-compose (from project root)
docker-compose up frontend

# Or build standalone
docker build -t disaster-relief-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_MAPBOX_TOKEN=your_token disaster-relief-frontend
```
