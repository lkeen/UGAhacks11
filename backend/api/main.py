"""FastAPI application for disaster relief optimizer."""

import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.orchestrator import Orchestrator
from backend.database import get_db

# Initialize FastAPI app
app = FastAPI(
    title="Disaster Relief Supply Chain Optimizer",
    description="Multi-agent AI system for coordinating disaster relief logistics",
    version="1.0.0",
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator (lazy loading)
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
        # Set default scenario time
        _orchestrator.set_scenario_time(
            datetime.fromisoformat("2024-09-27T14:00:00+00:00")
        )
    return _orchestrator


# Request/Response models
class QueryRequest(BaseModel):
    """Request model for natural language queries."""
    query: str
    scenario_time: Optional[str] = None


class RouteRequest(BaseModel):
    """Request model for route planning."""
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float


class ScenarioTimeRequest(BaseModel):
    """Request model for setting scenario time."""
    time: str  # ISO format


class AdvanceTimeRequest(BaseModel):
    """Request model for advancing scenario time."""
    hours: float = 1.0


# Endpoints
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Disaster Relief Supply Chain Optimizer",
        "version": "1.0.0",
        "scenario": "Hurricane Helene - Western NC",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/query")
async def process_query(request: QueryRequest):
    """
    Process a natural language query about supply routing.

    Example:
        {"query": "I have 200 cases of water at Asheville airport. Where should they go?"}
    """
    orchestrator = get_orchestrator()

    # Set scenario time if provided
    if request.scenario_time:
        try:
            scenario_time = datetime.fromisoformat(request.scenario_time)
            orchestrator.set_scenario_time(scenario_time)
        except ValueError:
            raise HTTPException(400, "Invalid scenario_time format. Use ISO format.")

    # Process the query
    try:
        response = await orchestrator.process_query(request.query)
        return response
    except Exception as e:
        raise HTTPException(500, f"Error processing query: {str(e)}")


@app.get("/events")
async def list_events(
    event_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 50,
):
    """
    List disaster events from the database.

    Query parameters:
        - event_type: Filter by type (road_closure, flooding, etc.)
        - start_time: Filter events after this time (ISO format)
        - end_time: Filter events before this time (ISO format)
        - limit: Maximum events to return
    """
    db = get_db()

    try:
        with db.session() as session:
            from backend.database.schema import Event

            query = session.query(Event)

            if event_type:
                query = query.filter(Event.event_type == event_type)

            if start_time:
                start = datetime.fromisoformat(start_time)
                query = query.filter(Event.timestamp >= start)

            if end_time:
                end = datetime.fromisoformat(end_time)
                query = query.filter(Event.timestamp <= end)

            events = query.order_by(Event.timestamp.desc()).limit(limit).all()

            return {
                "count": len(events),
                "events": [
                    {
                        "id": e.event_id,
                        "type": e.event_type,
                        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                        "location": {"lat": e.lat, "lon": e.lon},
                        "description": e.description,
                        "source": e.source,
                        "confidence": e.confidence,
                    }
                    for e in events
                ],
            }
    except Exception as e:
        raise HTTPException(500, f"Error fetching events: {str(e)}")


@app.get("/shelters")
async def list_shelters(status: Optional[str] = None):
    """
    List emergency shelters.

    Query parameters:
        - status: Filter by status (open, closed, full)
    """
    db = get_db()

    try:
        with db.session() as session:
            from backend.database.schema import Shelter

            query = session.query(Shelter)

            if status:
                query = query.filter(Shelter.status == status)

            shelters = query.all()

            return {
                "count": len(shelters),
                "shelters": [
                    {
                        "id": s.shelter_id,
                        "name": s.name,
                        "location": {"lat": s.lat, "lon": s.lon},
                        "address": s.address,
                        "capacity": s.capacity,
                        "current_occupancy": s.current_occupancy,
                        "status": s.status,
                        "needs": s.needs,
                        "accepts_pets": s.accepts_pets,
                        "has_generator": s.has_generator,
                    }
                    for s in shelters
                ],
            }
    except Exception as e:
        raise HTTPException(500, f"Error fetching shelters: {str(e)}")


@app.post("/route")
async def plan_route(request: RouteRequest):
    """
    Plan optimal route between two points.

    Returns route details including distance, time, and hazards avoided.
    """
    from backend.agents.base_agent import Location

    orchestrator = get_orchestrator()

    origin = Location(lat=request.origin_lat, lon=request.origin_lon)
    destination = Location(lat=request.destination_lat, lon=request.destination_lon)

    route = orchestrator.router.plan_route(origin, destination)

    if route is None:
        raise HTTPException(404, "No route found between the specified locations")

    return route.to_dict()


@app.get("/network/status")
async def get_network_status():
    """Get current road network status summary."""
    orchestrator = get_orchestrator()

    stats = orchestrator.road_network.get_network_stats()
    blocked = orchestrator.road_network.get_blocked_edges()
    damaged = orchestrator.road_network.get_damaged_edges()

    return {
        "stats": stats,
        "blocked_roads": blocked[:10],  # Limit to first 10
        "damaged_roads": damaged[:10],
    }


@app.post("/scenario/time")
async def set_scenario_time(request: ScenarioTimeRequest):
    """Set the current scenario simulation time."""
    orchestrator = get_orchestrator()

    try:
        scenario_time = datetime.fromisoformat(request.time)
        orchestrator.set_scenario_time(scenario_time)
        return {
            "message": "Scenario time updated",
            "scenario_time": scenario_time.isoformat(),
        }
    except ValueError:
        raise HTTPException(400, "Invalid time format. Use ISO format.")


@app.post("/scenario/advance")
async def advance_scenario_time(request: AdvanceTimeRequest):
    """Advance scenario time by specified hours."""
    orchestrator = get_orchestrator()
    orchestrator.advance_scenario_time(request.hours)
    return {
        "message": f"Advanced scenario by {request.hours} hours",
        "scenario_time": orchestrator.scenario_time.isoformat(),
    }


@app.get("/intelligence")
async def gather_intelligence():
    """
    Gather intelligence from all agents.

    Returns aggregated reports from satellite, social media, and official sources.
    """
    orchestrator = get_orchestrator()

    try:
        intelligence = await orchestrator.gather_all_intelligence()

        return {
            "scenario_time": orchestrator.scenario_time.isoformat(),
            "summary": {
                source: len(reports) for source, reports in intelligence.items()
            },
            "reports": {
                source: [r.to_dict() for r in reports[:10]]  # Limit per source
                for source, reports in intelligence.items()
            },
        }
    except Exception as e:
        raise HTTPException(500, f"Error gathering intelligence: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
