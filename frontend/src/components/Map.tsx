'use client';

import { useRef, useEffect, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import type { Shelter, Event, Route, MapViewState } from '@/types';

// TODO: Move to environment variable
// For now, using a placeholder - users need to add their own Mapbox token
const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || '';

interface MapProps {
  viewState: MapViewState;
  onViewStateChange: (viewState: MapViewState) => void;
  shelters: Shelter[];
  events: Event[];
  routes: Route[];
  selectedShelter: Shelter | null;
  onShelterClick: (shelter: Shelter) => void;
}

export function Map({
  viewState,
  onViewStateChange,
  shelters,
  events,
  routes,
  selectedShelter,
  onShelterClick,
}: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const markersRef = useRef<mapboxgl.Marker[]>([]);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    // Check for Mapbox token
    if (!MAPBOX_TOKEN) {
      console.warn('Mapbox token not configured. Map functionality will be limited.');
      return;
    }

    mapboxgl.accessToken = MAPBOX_TOKEN;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [viewState.longitude, viewState.latitude],
      zoom: viewState.zoom,
    });

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');
    map.current.addControl(new mapboxgl.ScaleControl(), 'bottom-left');

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
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    // Add shelter markers
    shelters.forEach((shelter) => {
      const el = document.createElement('div');
      el.className = 'shelter-marker';
      el.innerHTML = getShelterMarkerHTML(shelter, shelter.id === selectedShelter?.id);

      const marker = new mapboxgl.Marker({ element: el })
        .setLngLat([shelter.location_lon, shelter.location_lat])
        .setPopup(
          new mapboxgl.Popup({ offset: 25 }).setHTML(getShelterPopupHTML(shelter))
        )
        .addTo(map.current!);

      el.addEventListener('click', () => onShelterClick(shelter));

      markersRef.current.push(marker);
    });
  }, [shelters, selectedShelter, mapLoaded, onShelterClick]);

  // Add event markers
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    // TODO: Add event markers (flooding, road closures, etc.)
    // For now, this is a placeholder for event visualization
    // Events should be shown as colored circles or icons based on event_type
  }, [events, mapLoaded]);

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

      {/* Fallback when no Mapbox token */}
      {!MAPBOX_TOKEN && (
        <div className="absolute inset-0 bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
          <div className="text-center p-8 bg-white dark:bg-gray-700 rounded-lg shadow-lg max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Map Not Configured
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
              To display the map, add your Mapbox access token to the environment
              variable <code className="bg-gray-100 dark:bg-gray-600 px-1 rounded">NEXT_PUBLIC_MAPBOX_TOKEN</code>
            </p>
            <p className="text-xs text-gray-500">
              Get a free token at{' '}
              <a
                href="https://mapbox.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline"
              >
                mapbox.com
              </a>
            </p>

            {/* Static map placeholder showing Western NC */}
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-600 rounded text-left">
              <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                Demo Area: Western North Carolina
              </p>
              <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                <li>Center: Asheville ({viewState.latitude.toFixed(4)}, {viewState.longitude.toFixed(4)})</li>
                <li>Shelters: {shelters.length}</li>
                <li>Active Routes: {routes.length}</li>
              </ul>
            </div>
          </div>
        </div>
      )}

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
