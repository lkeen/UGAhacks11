'use client';

import { useState, useEffect, useCallback } from 'react';
import { Header } from '@/components/Header';
import { Map } from '@/components/Map';
import { Sidebar } from '@/components/Sidebar';
import { QueryPanel } from '@/components/QueryPanel';
import { AgentLogs } from '@/components/AgentLogs';
import { StatusBar } from '@/components/StatusBar';
import type {
  Shelter,
  Event,
  EventType,
  QueryResponse,
  AgentReport,
  NetworkStatus,
  AgentLogEntry,
} from '@/types';
import * as api from '@/lib/api';

// Default scenario time: Early morning before major events
const DEFAULT_SCENARIO_TIME = '2024-09-27T03:00:00Z';

// Western NC bounding box (Asheville area)
const DEFAULT_VIEW = {
  longitude: -82.5515,
  latitude: 35.5951,
  zoom: 10,
};

export default function Home() {
  // =========================================================================
  // State
  // =========================================================================

  // Data state
  const [shelters, setShelters] = useState<Shelter[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus | null>(null);
  const [agentReports, setAgentReports] = useState<AgentReport[]>([]);

  // Query state
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null);
  const [isQueryLoading, setIsQueryLoading] = useState(false);

  // UI state
  const [scenarioTime, setScenarioTime] = useState(DEFAULT_SCENARIO_TIME);
  const [agentLogs, setAgentLogs] = useState<AgentLogEntry[]>([]);
  const [selectedShelter, setSelectedShelter] = useState<Shelter | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [highlightedEventType, setHighlightedEventType] = useState<EventType | null>(null);
  const [highlightedEventId, setHighlightedEventId] = useState<number | string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Map state
  const [mapView, setMapView] = useState(DEFAULT_VIEW);

  // =========================================================================
  // Data Fetching
  // =========================================================================

  const fetchInitialData = useCallback(async () => {
    try {
      setError(null);

      // Fetch all initial data in parallel
      const [sheltersData, eventsData, networkData] = await Promise.all([
        api.getShelters(),
        api.getEvents(),
        api.getNetworkStatus(),
      ]);

      setShelters(sheltersData);
      setEvents(eventsData);
      setNetworkStatus(networkData);
      setIsConnected(true);

      addLogEntry('system', 'Connected to backend successfully', 'success');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to connect to backend';
      setError(message);
      setIsConnected(false);
      addLogEntry('system', `Connection failed: ${message}`, 'error');
    }
  }, []);

  const fetchIntelligence = useCallback(async () => {
    try {
      const intelligence = await api.gatherIntelligence();
      setAgentReports(intelligence.reports);

      // Log agent activity
      Object.entries(intelligence.summary.by_agent).forEach(([agent, count]) => {
        addLogEntry(agent, `Gathered ${count} reports`, 'info');
      });
    } catch (err) {
      console.error('Failed to fetch intelligence:', err);
    }
  }, []);

  // =========================================================================
  // Event Handlers
  // =========================================================================

  const handleQuerySubmit = async (query: string) => {
    setIsQueryLoading(true);
    setError(null);
    addLogEntry('orchestrator', `Processing query: "${query}"`, 'info');

    try {
      const response = await api.submitQuery({
        query,
        scenario_time: scenarioTime,
      });

      setQueryResponse(response);
      addLogEntry('orchestrator', `Generated delivery plan with ${response.delivery_plan.routes.length} routes`, 'success');

      // Refresh data after query
      await fetchInitialData();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Query failed';
      setError(message);
      addLogEntry('orchestrator', `Query failed: ${message}`, 'error');
    } finally {
      setIsQueryLoading(false);
    }
  };

  const handleTimeChange = async (newTime: string) => {
    try {
      await api.setScenarioTime(newTime);
      setScenarioTime(newTime);
      addLogEntry('system', `Scenario time set to ${newTime}`, 'info');

      // Refresh data for new time
      await fetchIntelligence();
    } catch (err) {
      console.error('Failed to set scenario time:', err);
    }
  };

  const handleAdvanceTime = async (hours: number) => {
    try {
      const response = await api.advanceScenarioTime(hours);
      setScenarioTime(response.scenario_time);
      addLogEntry('system', `Advanced time by ${hours} hours`, 'info');

      // Log new reports per agent
      Object.entries(response.new_reports).forEach(([agent, count]) => {
        if (count > 0) {
          addLogEntry(agent, `Found ${count} new report${count > 1 ? 's' : ''}`, 'info');
        }
      });

      // Add new agent reports to the reports state
      if (response.new_agent_reports && response.new_agent_reports.length > 0) {
        setAgentReports((prevReports) => {
          const existingIds = new Set(prevReports.map((r) => r.id));
          const newReports = response.new_agent_reports
            .filter((r) => !existingIds.has(r.id))
            .map((r) => ({
              id: r.id,
              timestamp: r.timestamp,
              event_type: r.event_type as EventType,
              location: r.location,
              description: r.description,
              source: r.source as AgentReport['source'],
              confidence: r.confidence,
              raw_data: {},
              corroborations: r.corroborations || 0,
              agent_name: r.agent_name,
              metadata: r.metadata || {},
            }));
          return [...prevReports, ...newReports];
        });
      }

      // Add new events to the events list
      if (response.new_events && response.new_events.length > 0) {
        setEvents((prevEvents) => {
          let updatedEvents = [...prevEvents];

          for (const e of response.new_events) {
            // Check if this is a road_clear event
            if (e.event_type === 'road_clear') {
              // Remove any previous road_closure or road_damage events at similar location
              updatedEvents = updatedEvents.filter((existingEvent) => {
                if (
                  existingEvent.event_type === 'road_closure' ||
                  existingEvent.event_type === 'road_damage'
                ) {
                  // Check if within ~0.01 degrees (~1km)
                  const latDiff = Math.abs(existingEvent.location_lat - e.location_lat);
                  const lonDiff = Math.abs(existingEvent.location_lon - e.location_lon);
                  if (latDiff < 0.01 && lonDiff < 0.01) {
                    addLogEntry('system', `Road cleared: ${existingEvent.description.substring(0, 50)}...`, 'success');
                    return false; // Remove this event
                  }
                }
                return true;
              });
            }

            // Check for duplicate - if same location and type, increment corroborations
            const existingIndex = updatedEvents.findIndex((existing) => {
              const latDiff = Math.abs(existing.location_lat - e.location_lat);
              const lonDiff = Math.abs(existing.location_lon - e.location_lon);
              return (
                existing.event_type === e.event_type &&
                latDiff < 0.005 &&
                lonDiff < 0.005
              );
            });

            if (existingIndex >= 0) {
              // Increment corroborations on existing event
              updatedEvents[existingIndex] = {
                ...updatedEvents[existingIndex],
                corroborations: (updatedEvents[existingIndex].corroborations || 0) + 1,
              };
            } else {
              // Add as new event
              updatedEvents.push({
                id: e.id as unknown as number,
                timestamp: e.timestamp,
                event_type: e.event_type as EventType,
                location_lat: e.location_lat,
                location_lon: e.location_lon,
                description: e.description,
                source: e.source as Event['source'],
                confidence: e.confidence,
                severity: 5,
                affected_radius_m: 100,
                corroborations: 0,
                is_active: true,
                created_at: e.timestamp,
                updated_at: e.timestamp,
              });
            }
          }

          return updatedEvents;
        });

        const newEventCount = response.new_events.length;
        addLogEntry('system', `${newEventCount} new report${newEventCount > 1 ? 's' : ''} processed`, 'success');
      }
    } catch (err) {
      console.error('Failed to advance time:', err);
    }
  };

  const handleShelterSelect = (shelter: Shelter | null) => {
    setSelectedShelter(shelter);
    // Center map on selected shelter
    if (shelter) {
      setMapView({
        longitude: shelter.location_lon,
        latitude: shelter.location_lat,
        zoom: 13,
      });
    }
  };

  const handleEventSelect = (event: Event | null) => {
    setSelectedEvent(event);
    if (event) {
      // Select event and zoom to its location
      setHighlightedEventId(event.id);
      if (event.location_lat !== undefined && event.location_lon !== undefined) {
        setMapView({
          longitude: event.location_lon,
          latitude: event.location_lat,
          zoom: 14,
        });
      }
    } else {
      // Deselect event and zoom back out
      setHighlightedEventId(null);
      setMapView(DEFAULT_VIEW);
    }
  };

  // =========================================================================
  // Helpers
  // =========================================================================

  const addLogEntry = (
    agentName: string,
    message: string,
    level: AgentLogEntry['level']
  ) => {
    const entry: AgentLogEntry = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      agent_name: agentName,
      message,
      level,
    };
    setAgentLogs((prev) => [entry, ...prev].slice(0, 100)); // Keep last 100 entries
  };

  // =========================================================================
  // Effects
  // =========================================================================

  // Initial data fetch
  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  // TODO: Set up WebSocket or polling for real-time updates
  // For now, we'll just fetch data on initial load and after queries

  // =========================================================================
  // Render
  // =========================================================================

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <Header
        scenarioTime={scenarioTime}
        onTimeChange={handleTimeChange}
        onAdvanceTime={handleAdvanceTime}
        isConnected={isConnected}
      />

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar - Shelters & Filters */}
        <Sidebar
          shelters={shelters}
          events={events}
          selectedShelter={selectedShelter}
          onShelterSelect={handleShelterSelect}
          highlightedEventType={highlightedEventType}
          onEventTypeSelect={setHighlightedEventType}
          highlightedEventId={highlightedEventId}
          onEventSelect={handleEventSelect}
          selectedEvent={selectedEvent}
          agentReports={agentReports}
        />

        {/* Map area */}
        <div className="flex-1 relative">
          <Map
            viewState={mapView}
            onViewStateChange={setMapView}
            shelters={shelters}
            events={events}
            routes={queryResponse?.delivery_plan.routes || []}
            selectedShelter={selectedShelter}
            onShelterClick={handleShelterSelect}
            highlightedEventType={highlightedEventType}
            highlightedEventId={highlightedEventId}
          />

          {/* Query panel overlay */}
          <QueryPanel
            onSubmit={handleQuerySubmit}
            isLoading={isQueryLoading}
            response={queryResponse}
            error={error}
          />
        </div>

        {/* Right panel - Agent Logs */}
        <AgentLogs
          logs={agentLogs}
          reports={agentReports}
        />
      </div>

      {/* Status bar */}
      <StatusBar
        networkStatus={networkStatus}
        scenarioTime={scenarioTime}
        totalEvents={events.length}
        totalShelters={shelters.length}
      />
    </div>
  );
}
