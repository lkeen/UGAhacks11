/**
 * TypeScript type definitions for the Disaster Relief Supply Chain Optimizer
 * These types mirror the backend Python dataclasses and SQLAlchemy models
 */

// ============================================================================
// Enums
// ============================================================================

export type EventType =
  | 'road_closure'
  | 'road_damage'
  | 'road_clear'
  | 'flooding'
  | 'bridge_collapse'
  | 'shelter_opening'
  | 'shelter_closing'
  | 'shelter_need'
  | 'supply_request'
  | 'supplies_needed'
  | 'power_outage'
  | 'infrastructure_damage'
  | 'rescue_needed';

export type DataSource =
  | 'satellite'
  | 'twitter'
  | 'reddit'
  | 'facebook'
  | 'fema'
  | 'ncdot'
  | 'usgs'
  | 'local_emergency'
  | 'news'
  | 'citizen_report';

export type RoadStatus = 'open' | 'damaged' | 'closed';

export type ShelterStatus = 'closed' | 'open' | 'full';

export type DeliveryStatus = 'planned' | 'in_transit' | 'delivered' | 'failed';

// ============================================================================
// Core Data Types
// ============================================================================

export interface Location {
  lat: number;
  lon: number;
  address?: string;
}

export interface BoundingBox {
  min_lat: number;
  max_lat: number;
  min_lon: number;
  max_lon: number;
}

// ============================================================================
// Agent Reports
// ============================================================================

export interface AgentReport {
  id: string;
  timestamp: string; // ISO datetime
  event_type: EventType;
  location: Location;
  description: string;
  source: DataSource;
  confidence: number;
  raw_data: Record<string, unknown>;
  corroborations: number;
  agent_name: string;
  metadata: Record<string, unknown>;
}

// ============================================================================
// Events
// ============================================================================

export interface Event {
  id: number;
  timestamp: string;
  event_type: EventType;
  location_lat: number;
  location_lon: number;
  location_address?: string;
  description: string;
  severity: number;
  affected_radius_m: number;
  source: DataSource;
  source_id?: string;
  confidence: number;
  corroborations: number;
  is_active: boolean;
  verified_by?: string;
  verified_at?: string;
  raw_data?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Shelters
// ============================================================================

export interface Shelter {
  id: number;
  name: string;
  location_lat: number;
  location_lon: number;
  address?: string;
  capacity: number;
  current_occupancy: number;
  status: ShelterStatus;
  opened_at?: string;
  closed_at?: string;
  needs: string[]; // JSON array of supply needs
  contact_name?: string;
  contact_phone?: string;
  has_generator: boolean;
  has_medical: boolean;
  accepts_pets: boolean;
  wheelchair_accessible: boolean;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Roads
// ============================================================================

export interface Road {
  id: number;
  osm_id: string;
  name?: string;
  highway_type: string;
  geometry_wkt: string;
  coordinates: [number, number][]; // Array of [lon, lat] pairs
  status: RoadStatus;
  weight_multiplier: number;
  last_updated: string;
  confidence: number;
  created_at: string;
}

// ============================================================================
// Routes & Deliveries
// ============================================================================

export interface Route {
  id: string;
  origin: Location;
  destination: Location;
  waypoints: [number, number][]; // Array of [lon, lat] pairs
  distance_m: number;
  estimated_duration_min: number;
  hazards_avoided: HazardInfo[];
  confidence: number;
  reasoning: string;
  created_at: string;
}

export interface HazardInfo {
  type: EventType;
  location: Location;
  description: string;
  source: DataSource;
}

export interface Delivery {
  id: number;
  origin_lat: number;
  origin_lon: number;
  origin_address?: string;
  shelter_id: number;
  shelter?: Shelter;
  supplies: Record<string, number>; // e.g., { "water": 200, "blankets": 50 }
  route_geometry?: string;
  distance_m?: number;
  estimated_duration_min?: number;
  status: DeliveryStatus;
  priority: number;
  reasoning?: string;
  hazards_avoided?: HazardInfo[];
  planned_at: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface QueryRequest {
  query: string;
  scenario_time?: string;
}

export interface SituationalAwareness {
  total_reports: number;
  blocked_roads: number;
  damaged_roads: number;
  reports_by_agent: Record<string, number>;
  reports_by_type: Record<string, number>;
}

export interface DeliveryPlan {
  routes: Route[];
  total_distance_m: number;
  total_duration_min: number;
  shelters_served: number;
}

export interface QueryResponse {
  query: string;
  scenario_time: string;
  situational_awareness: SituationalAwareness;
  delivery_plan: DeliveryPlan;
  reasoning: string;
}

export interface RouteRequest {
  origin_lat: number;
  origin_lon: number;
  destination_lat: number;
  destination_lon: number;
}

export interface NetworkStatus {
  total_edges: number;
  blocked_edges: number;
  damaged_edges: number;
  average_confidence: number;
}

export interface IntelligenceResponse {
  scenario_time: string;
  reports: AgentReport[];
  summary: {
    total_reports: number;
    by_agent: Record<string, number>;
    by_type: Record<string, number>;
  };
}

export interface HealthResponse {
  status: string;
  version: string;
  scenario_time?: string;
}

// ============================================================================
// UI State Types
// ============================================================================

export interface MapViewState {
  longitude: number;
  latitude: number;
  zoom: number;
}

export interface FilterState {
  eventTypes: EventType[];
  sources: DataSource[];
  timeRange: {
    start: string;
    end: string;
  };
  showShelters: boolean;
  showRoutes: boolean;
  showHazards: boolean;
}

export interface AgentLogEntry {
  id: string;
  timestamp: string;
  agent_name: string;
  message: string;
  level: 'info' | 'warning' | 'error' | 'success';
  data?: Record<string, unknown>;
}
