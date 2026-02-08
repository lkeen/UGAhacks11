'use client';

import { useRef, useEffect, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { Shelter, Event, Route, MapViewState, EventType } from '@/types';

// Free OpenStreetMap-based tile styles (swap as needed):
// const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';      // Light
// const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';   // Dark
// const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json';       // Colorful
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

// Event type colors - comprehensive list
export const EVENT_COLORS: Record<string, string> = {
  road_closure: '#dc2626',        // red-600
  road_damage: '#f97316',         // orange-500
  flooding: '#2563eb',            // blue-600
  bridge_collapse: '#991b1b',     // red-800
  shelter_opening: '#16a34a',     // green-600
  shelter_closing: '#ca8a04',     // yellow-600
  supply_request: '#9333ea',      // purple-600
  supplies_needed: '#a855f7',     // purple-500
  power_outage: '#6b7280',        // gray-500
  infrastructure_damage: '#ea580c', // orange-600
  rescue_needed: '#e11d48',       // rose-600
  road_clear: '#22c55e',          // green-500
  evacuation: '#dc2626',          // red-600
  medical_emergency: '#ec4899',   // pink-500
  water_contamination: '#0891b2', // cyan-600
};

// Event type labels
export const EVENT_LABELS: Record<string, string> = {
  road_closure: 'Road Closure',
  road_damage: 'Road Damage',
  flooding: 'Flooding',
  bridge_collapse: 'Bridge Collapse',
  shelter_opening: 'Shelter Opening',
  shelter_closing: 'Shelter Closing',
  supply_request: 'Supply Request',
  supplies_needed: 'Supplies Needed',
  power_outage: 'Power Outage',
  infrastructure_damage: 'Infrastructure Damage',
  rescue_needed: 'Rescue Needed',
  road_clear: 'Road Clear',
  evacuation: 'Evacuation',
  medical_emergency: 'Medical Emergency',
  water_contamination: 'Water Contamination',
};

interface MapProps {
  viewState: MapViewState;
  onViewStateChange: (viewState: MapViewState) => void;
  shelters: Shelter[];
  events: Event[];
  routes: Route[];
  selectedShelter: Shelter | null;
  onShelterClick: (shelter: Shelter) => void;
  highlightedEventType: EventType | null;
  highlightedEventId: number | string | null;
  selectedRouteId: string | null;
}

/** Convert waypoints to [lon, lat] arrays regardless of input format */
function toCoords(waypoints: any[]): [number, number][] {
  return waypoints.map((wp: any): [number, number] =>
    Array.isArray(wp) ? [wp[0], wp[1]] : [wp.lon, wp.lat]
  );
}

export function Map({
  viewState,
  onViewStateChange,
  shelters,
  events,
  routes,
  selectedShelter,
  onShelterClick,
  highlightedEventType,
  highlightedEventId,
  selectedRouteId,
}: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [legendExpanded, setLegendExpanded] = useState(true);
  const shelterMarkersRef = useRef<maplibregl.Marker[]>([]);
  const eventMarkersRef = useRef<maplibregl.Marker[]>([]);

  // Get unique event types from current events
  const activeEventTypes = Array.from(new Set(events.map(e => e.event_type)));

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: MAP_STYLE,
      center: [viewState.longitude, viewState.latitude],
      zoom: viewState.zoom,
    });

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.current.addControl(new maplibregl.ScaleControl(), 'bottom-left');

    map.current.on('load', () => {
      setMapLoaded(true);
    });

    map.current.on('moveend', () => {
      if (!map.current) return;
      const center = map.current.getCenter();
      onViewStateChange({
        longitude: center.lng,
        latitude: center.lat,
        zoom: map.current.getZoom(),
      });
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // Update map center when viewState changes externally
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const currentCenter = map.current.getCenter();
    const currentZoom = map.current.getZoom();

    // Only update if significantly different (prevents infinite loops)
    if (
      Math.abs(currentCenter.lng - viewState.longitude) > 0.001 ||
      Math.abs(currentCenter.lat - viewState.latitude) > 0.001 ||
      Math.abs(currentZoom - viewState.zoom) > 0.5
    ) {
      map.current.flyTo({
        center: [viewState.longitude, viewState.latitude],
        zoom: viewState.zoom,
        duration: 1000,
      });
    }
  }, [viewState, mapLoaded]);

  // Add shelter markers
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    // Clear existing markers
    shelterMarkersRef.current.forEach((marker) => marker.remove());
    shelterMarkersRef.current = [];

    // Add shelter markers
    shelters.forEach((shelter) => {
      const el = document.createElement('div');
      el.className = 'shelter-marker';
      el.innerHTML = getShelterMarkerHTML(shelter, shelter.id === selectedShelter?.id);

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([shelter.location_lon, shelter.location_lat])
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(getShelterPopupHTML(shelter))
        )
        .addTo(map.current!);

      el.addEventListener('click', () => onShelterClick(shelter));

      shelterMarkersRef.current.push(marker);
    });
  }, [shelters, selectedShelter, mapLoaded, onShelterClick]);

  // Add event markers
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    // Clear existing event markers
    eventMarkersRef.current.forEach((marker) => marker.remove());
    eventMarkersRef.current = [];

    // Add event markers
    events.forEach((event) => {
      const lat = event.location_lat;
      const lon = event.location_lon;

      if (lat === undefined || lon === undefined) return;

      // Check if this specific event is highlighted
      const isHighlightedById = highlightedEventId !== null && event.id === highlightedEventId;
      // Check if this event type is highlighted (but not a specific event)
      const isHighlightedByType = highlightedEventId === null && highlightedEventType === event.event_type;
      const isHighlighted = isHighlightedById || isHighlightedByType;

      const el = document.createElement('div');
      el.className = 'event-marker';
      el.innerHTML = getEventMarkerHTML(event, isHighlighted, isHighlightedById);

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([lon, lat])
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(getEventPopupHTML(event))
        )
        .addTo(map.current!);

      eventMarkersRef.current.push(marker);
    });
  }, [events, mapLoaded, highlightedEventType, highlightedEventId]);

  // Add route lines with selected-route highlighting
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    // Remove existing route layers and sources
    ['routes-selected', 'routes'].forEach((id) => {
      if (map.current!.getLayer(id)) map.current!.removeLayer(id);
    });
    ['routes-selected', 'routes'].forEach((id) => {
      if (map.current!.getSource(id)) map.current!.removeSource(id);
    });

    if (routes.length === 0) return;

    // Convert routes to GeoJSON features
    const routeFeatures = routes.map((route, index) => ({
      type: 'Feature' as const,
      properties: {
        id: route.id,
        index,
        confidence: route.confidence,
      },
      geometry: {
        type: 'LineString' as const,
        coordinates: toCoords(route.waypoints),
      },
    }));

    map.current.addSource('routes', {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: routeFeatures,
      },
    });

    // All-routes layer: dim when a route is selected, normal otherwise
    map.current.addLayer({
      id: 'routes',
      type: 'line',
      source: 'routes',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': selectedRouteId ? '#94a3b8' : '#3b82f6',
        'line-width': selectedRouteId ? 2 : 4,
        'line-opacity': selectedRouteId ? 0.4 : 0.8,
      },
    });

    // Selected-route highlight layer
    if (selectedRouteId) {
      const selectedRoute = routes.find((r) => r.id === selectedRouteId);
      if (selectedRoute) {
        const coords = toCoords(selectedRoute.waypoints);

        map.current.addSource('routes-selected', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: [
              {
                type: 'Feature' as const,
                properties: { id: selectedRoute.id },
                geometry: {
                  type: 'LineString' as const,
                  coordinates: coords,
                },
              },
            ],
          },
        });

        map.current.addLayer({
          id: 'routes-selected',
          type: 'line',
          source: 'routes-selected',
          layout: {
            'line-join': 'round',
            'line-cap': 'round',
          },
          paint: {
            'line-color': '#3b82f6',
            'line-width': 6,
            'line-opacity': 0.9,
          },
        });

        // Fly to fit selected route bounds
        if (coords.length >= 2) {
          const bounds = coords.reduce(
            (b, coord) => b.extend(coord as [number, number]),
            new maplibregl.LngLatBounds(coords[0] as [number, number], coords[0] as [number, number])
          );
          map.current.fitBounds(bounds, { padding: 80, duration: 1000 });
        }
      }
    }
  }, [routes, mapLoaded, selectedRouteId]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Map legend - minimizable */}
      <div className="absolute bottom-8 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg text-xs overflow-hidden">
        {/* Legend header */}
        <button
          onClick={() => setLegendExpanded(!legendExpanded)}
          className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          <span className="font-medium text-gray-900 dark:text-white">Legend</span>
          {legendExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          )}
        </button>

        {/* Legend content */}
        {legendExpanded && (
          <div className="px-3 pb-3 space-y-2">
            {/* Shelters section */}
            <div>
              <p className="text-gray-500 text-xs font-medium mb-1">Shelters</p>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="text-gray-600 dark:text-gray-400">Open</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-yellow-500" />
                  <span className="text-gray-600 dark:text-gray-400">Full</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-gray-400" />
                  <span className="text-gray-600 dark:text-gray-400">Closed</span>
                </div>
              </div>
            </div>

            {/* Events section - dynamic based on active events */}
            {activeEventTypes.length > 0 && (
              <div>
                <p className="text-gray-500 text-xs font-medium mb-1">Events</p>
                <div className="space-y-1">
                  {activeEventTypes.map((type) => (
                    <div key={type} className="flex items-center gap-2">
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: EVENT_COLORS[type] || '#6b7280' }}
                      />
                      <span className="text-gray-600 dark:text-gray-400">
                        {EVENT_LABELS[type] || type.replace(/_/g, ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Routes */}
            {routes.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="w-6 h-0.5 bg-blue-500" />
                <span className="text-gray-600 dark:text-gray-400">Delivery Route</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Helper functions for marker/popup HTML
function getShelterMarkerHTML(shelter: Shelter, isSelected: boolean): string {
  const statusColors = {
    open: 'bg-success-500',
    full: 'bg-warning-500',
    closed: 'bg-gray-400',
  };

  const color = statusColors[shelter.status] || 'bg-gray-400';
  const size = isSelected ? 'w-6 h-6' : 'w-4 h-4';
  const ring = isSelected ? 'ring-2 ring-primary-500 ring-offset-2' : '';

  return `
    <div class="${size} ${color} ${ring} rounded-full cursor-pointer shadow-lg
                 flex items-center justify-center text-white text-xs font-bold
                 transition-transform hover:scale-110">
    </div>
  `;
}

function getShelterPopupHTML(shelter: Shelter): string {
  const occupancyPercent = Math.round(
    (shelter.current_occupancy / shelter.capacity) * 100
  );

  return `
    <div class="p-2">
      <h3 class="font-bold text-gray-900">${shelter.name}</h3>
      <p class="text-sm text-gray-600 mt-1">${shelter.address || 'Address unavailable'}</p>
      <div class="mt-2 text-sm">
        <span class="font-medium">Status:</span>
        <span class="capitalize ${
          shelter.status === 'open'
            ? 'text-success-600'
            : shelter.status === 'full'
            ? 'text-warning-600'
            : 'text-gray-600'
        }">${shelter.status}</span>
      </div>
      <div class="text-sm">
        <span class="font-medium">Occupancy:</span>
        ${shelter.current_occupancy}/${shelter.capacity} (${occupancyPercent}%)
      </div>
      ${
        shelter.needs.length > 0
          ? `<div class="mt-2">
              <span class="text-sm font-medium">Needs:</span>
              <div class="flex flex-wrap gap-1 mt-1">
                ${shelter.needs
                  .map(
                    (need) =>
                      `<span class="px-1.5 py-0.5 text-xs bg-warning-100 text-warning-700 rounded">${need}</span>`
                  )
                  .join('')}
              </div>
            </div>`
          : ''
      }
    </div>
  `;
}

function getEventMarkerHTML(event: Event, isHighlighted: boolean, isSpecificHighlight: boolean): string {
  const color = EVENT_COLORS[event.event_type] || '#6b7280';
  const size = isHighlighted ? (isSpecificHighlight ? 28 : 20) : 12;
  const opacity = isHighlighted ? 1 : 0.8;
  const border = isSpecificHighlight ? '4px solid white' : (isHighlighted ? '2px solid white' : 'none');
  const shadow = isHighlighted ? '0 0 12px rgba(0,0,0,0.5)' : '0 2px 4px rgba(0,0,0,0.3)';
  const zIndex = isSpecificHighlight ? 1000 : (isHighlighted ? 100 : 1);

  return `
    <div style="
      width: ${size}px;
      height: ${size}px;
      background-color: ${color};
      opacity: ${opacity};
      border: ${border};
      box-shadow: ${shadow};
      border-radius: 50%;
      cursor: pointer;
      transition: all 0.2s ease;
      z-index: ${zIndex};
    "></div>
  `;
}

function getEventPopupHTML(event: Event): string {
  const typeLabel = (EVENT_LABELS[event.event_type] || event.event_type).replace(/_/g, ' ');
  const color = EVENT_COLORS[event.event_type] || '#6b7280';

  return `
    <div class="p-2 max-w-xs">
      <div class="flex items-center gap-2 mb-1">
        <span style="width: 10px; height: 10px; background: ${color}; border-radius: 50%;"></span>
        <h3 class="font-bold text-gray-900 capitalize">${typeLabel}</h3>
      </div>
      <p class="text-sm text-gray-600">${event.description || 'No description available'}</p>
      ${event.timestamp ? `<p class="text-xs text-gray-400 mt-1">${new Date(event.timestamp).toLocaleString()}</p>` : ''}
      ${event.source ? `<p class="text-xs text-gray-400">Source: ${event.source}</p>` : ''}
    </div>
  `;
}
