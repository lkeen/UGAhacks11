'use client';

import { useRef, useEffect, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { Shelter, Event, Route, MapViewState, EventType } from '@/types';

// Free OpenStreetMap-based tile styles (swap as needed):
// const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';      // Light
// const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';   // Dark
// const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json';       // Colorful
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

// Event type colors
const EVENT_COLORS: Record<string, string> = {
  road_closure: '#dc2626',      // red-600
  flooding: '#2563eb',          // blue-600
  bridge_collapse: '#991b1b',   // red-800
  shelter_opening: '#16a34a',   // green-600
  shelter_closing: '#ca8a04',   // yellow-600
  supply_request: '#9333ea',    // purple-600
  power_outage: '#4b5563',      // gray-600
  infrastructure_damage: '#ea580c', // orange-600
  rescue_needed: '#e11d48',     // rose-600
  road_clear: '#22c55e',        // green-500
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
}: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const shelterMarkersRef = useRef<maplibregl.Marker[]>([]);
  const eventMarkersRef = useRef<maplibregl.Marker[]>([]);

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

      const isHighlighted = highlightedEventType === event.event_type;
      const el = document.createElement('div');
      el.className = 'event-marker';
      el.innerHTML = getEventMarkerHTML(event, isHighlighted);

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([lon, lat])
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(getEventPopupHTML(event))
        )
        .addTo(map.current!);

      eventMarkersRef.current.push(marker);
    });
  }, [events, mapLoaded, highlightedEventType]);

  // Add route lines
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    // Remove existing route layers
    if (map.current.getLayer('routes')) {
      map.current.removeLayer('routes');
    }
    if (map.current.getSource('routes')) {
      map.current.removeSource('routes');
    }

    if (routes.length === 0) return;

    // Convert routes to GeoJSON
    const routeFeatures = routes.map((route, index) => ({
      type: 'Feature' as const,
      properties: {
        id: route.id,
        index,
        confidence: route.confidence,
      },
      geometry: {
        type: 'LineString' as const,
        coordinates: route.waypoints,
      },
    }));

    map.current.addSource('routes', {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: routeFeatures,
      },
    });

    map.current.addLayer({
      id: 'routes',
      type: 'line',
      source: 'routes',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': '#3b82f6',
        'line-width': 4,
        'line-opacity': 0.8,
      },
    });
  }, [routes, mapLoaded]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Map legend */}
      <div className="absolute bottom-8 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-3 text-xs">
        <h4 className="font-medium text-gray-900 dark:text-white mb-2">Legend</h4>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-success-500" />
            <span className="text-gray-600 dark:text-gray-400">Open Shelter</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-warning-500" />
            <span className="text-gray-600 dark:text-gray-400">Full Shelter</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-danger-500" />
            <span className="text-gray-600 dark:text-gray-400">Road Closure</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-gray-600 dark:text-gray-400">Flooding</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-6 h-0.5 bg-primary-500" />
            <span className="text-gray-600 dark:text-gray-400">Delivery Route</span>
          </div>
        </div>
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

function getEventMarkerHTML(event: Event, isHighlighted: boolean): string {
  const color = EVENT_COLORS[event.event_type] || '#6b7280';
  const size = isHighlighted ? 24 : 12;
  const opacity = isHighlighted ? 1 : 0.8;
  const border = isHighlighted ? '3px solid white' : 'none';
  const shadow = isHighlighted ? '0 0 10px rgba(0,0,0,0.5)' : '0 2px 4px rgba(0,0,0,0.3)';

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
    "></div>
  `;
}

function getEventPopupHTML(event: Event): string {
  const typeLabel = event.event_type.replace(/_/g, ' ');
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
