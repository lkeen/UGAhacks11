/**
 * API client for the Disaster Relief Supply Chain Optimizer backend
 *
 * This client handles all communication with the FastAPI backend.
 * TODO: Add error handling, retry logic, and caching as needed.
 */

import type {
  QueryRequest,
  QueryResponse,
  RouteRequest,
  Route,
  Event,
  Shelter,
  NetworkStatus,
  IntelligenceResponse,
  HealthResponse,
  AgentReport,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Base fetch wrapper with error handling
 */
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    // TODO: Better error handling with error types
    const errorText = await response.text();
    throw new Error(`API Error (${response.status}): ${errorText}`);
  }

  return response.json();
}

// ============================================================================
// Health & Status
// ============================================================================

/**
 * Check if the backend is healthy
 */
export async function checkHealth(): Promise<HealthResponse> {
  return fetchAPI<HealthResponse>('/health');
}

/**
 * Get current network status (blocked/damaged roads)
 */
export async function getNetworkStatus(): Promise<NetworkStatus> {
  const response = await fetchAPI<{
    stats: Record<string, any>;
    blocked_roads: any[];
    damaged_roads: any[];
  }>('/network/status');

  return {
    total_edges: response.stats?.total_edges || 0,
    blocked_edges: response.blocked_roads?.length || 0,
    damaged_edges: response.damaged_roads?.length || 0,
    average_confidence: response.stats?.average_confidence || 0,
  };
}

// ============================================================================
// Query Processing
// ============================================================================

/**
 * Submit a natural language query to the orchestrator
 * Example: "I have 200 cases of water at Asheville airport. Where should they go?"
 */
export async function submitQuery(request: QueryRequest): Promise<QueryResponse> {
  return fetchAPI<QueryResponse>('/query', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// ============================================================================
// Events
// ============================================================================

interface GetEventsParams {
  event_type?: string;
  start_time?: string;
  end_time?: string;
  is_active?: boolean;
}

/**
 * Get disaster events with optional filtering
 */
export async function getEvents(params: GetEventsParams = {}): Promise<Event[]> {
  const searchParams = new URLSearchParams();

  if (params.event_type) searchParams.set('event_type', params.event_type);
  if (params.start_time) searchParams.set('start_time', params.start_time);
  if (params.end_time) searchParams.set('end_time', params.end_time);
  if (params.is_active !== undefined) searchParams.set('is_active', String(params.is_active));

  const queryString = searchParams.toString();
  const endpoint = `/events${queryString ? `?${queryString}` : ''}`;

  const response = await fetchAPI<{ count: number; events: any[] }>(endpoint);
  // Map backend response to frontend Event type
  return (response.events || []).map((e) => ({
    ...e,
    event_type: e.type || e.event_type,
    location_lat: e.location?.lat ?? e.location_lat,
    location_lon: e.location?.lon ?? e.location_lon,
  }));
}

// ============================================================================
// Shelters
// ============================================================================

interface GetSheltersParams {
  status?: 'open' | 'closed' | 'full';
}

/**
 * Get shelters with optional status filtering
 */
export async function getShelters(params: GetSheltersParams = {}): Promise<Shelter[]> {
  const searchParams = new URLSearchParams();

  if (params.status) searchParams.set('status', params.status);

  const queryString = searchParams.toString();
  const endpoint = `/shelters${queryString ? `?${queryString}` : ''}`;

  const response = await fetchAPI<{ count: number; shelters: any[] }>(endpoint);
  // Map backend response to frontend Shelter type
  return (response.shelters || []).map((s) => ({
    ...s,
    location_lat: s.location?.lat ?? s.location_lat,
    location_lon: s.location?.lon ?? s.location_lon,
    needs: s.needs || [],
  }));
}

// ============================================================================
// Routing
// ============================================================================

/**
 * Calculate a route between two points
 */
export async function calculateRoute(request: RouteRequest): Promise<Route> {
  return fetchAPI<Route>('/route', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// ============================================================================
// Intelligence Gathering
// ============================================================================

/**
 * Gather and return all agent intelligence reports
 */
export async function gatherIntelligence(): Promise<IntelligenceResponse> {
  const response = await fetchAPI<{
    scenario_time: string;
    summary: Record<string, number>;
    reports: Record<string, any[]>;
  }>('/intelligence');

  // Flatten reports from { agent: [...] } to flat array with agent_name
  const flatReports: AgentReport[] = [];
  for (const [agentName, reports] of Object.entries(response.reports || {})) {
    for (const report of reports) {
      flatReports.push({
        ...report,
        agent_name: agentName,
      });
    }
  }

  return {
    scenario_time: response.scenario_time,
    reports: flatReports,
    summary: {
      total_reports: flatReports.length,
      by_agent: response.summary || {},
      by_type: {},
    },
  };
}

// ============================================================================
// Scenario Management (Demo Mode)
// ============================================================================

/**
 * Set the scenario simulation time
 */
export async function setScenarioTime(time: string): Promise<{ scenario_time: string }> {
  return fetchAPI<{ scenario_time: string }>('/scenario/time', {
    method: 'POST',
    body: JSON.stringify({ time }),
  });
}

/**
 * Response from advancing scenario time
 */
interface AdvanceTimeResponse {
  scenario_time: string;
  previous_time: string;
  new_reports: Record<string, number>;
  new_events: Array<{
    id: string;
    event_type: string;
    timestamp: string;
    location_lat: number;
    location_lon: number;
    description: string;
    source: string;
    confidence: number;
    agent_name: string;
  }>;
}

/**
 * Advance the scenario time by specified hours
 */
export async function advanceScenarioTime(hours: number): Promise<AdvanceTimeResponse> {
  return fetchAPI<AdvanceTimeResponse>('/scenario/advance', {
    method: 'POST',
    body: JSON.stringify({ hours }),
  });
}

// ============================================================================
// WebSocket / Polling for Real-time Updates
// ============================================================================

// TODO: Implement WebSocket connection for real-time agent updates
// The backend currently doesn't have WebSocket support, but this is where
// we'd add it for live updates during the demo.

/**
 * Poll for agent updates at regular intervals
 * This is a fallback for when WebSockets aren't available
 */
export function startPolling(
  callback: (reports: AgentReport[]) => void,
  intervalMs: number = 5000
): () => void {
  let isActive = true;

  const poll = async () => {
    if (!isActive) return;

    try {
      const intelligence = await gatherIntelligence();
      callback(intelligence.reports);
    } catch (error) {
      console.error('Polling error:', error);
      // TODO: Implement exponential backoff
    }

    if (isActive) {
      setTimeout(poll, intervalMs);
    }
  };

  // Start polling
  poll();

  // Return cleanup function
  return () => {
    isActive = false;
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Convert a Location object to a Mapbox-compatible [lon, lat] tuple
 */
export function locationToLngLat(location: { lat: number; lon: number }): [number, number] {
  return [location.lon, location.lat];
}

/**
 * Format duration in minutes to human-readable string
 */
export function formatDuration(minutes: number): string {
  if (minutes < 60) {
    return `${Math.round(minutes)} min`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

/**
 * Format distance in meters to human-readable string
 */
export function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }
  const km = meters / 1000;
  return `${km.toFixed(1)} km`;
}
