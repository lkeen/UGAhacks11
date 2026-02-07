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
  QueryResponse,
  AgentReport,
  NetworkStatus,
  AgentLogEntry,
} from '@/types';
import * as api from '@/lib/api';

// Default scenario time: Hurricane Helene landfall
const DEFAULT_SCENARIO_TIME = '2024-09-27T14:00:00Z';

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

      // Refresh data
      await fetchIntelligence();
    } catch (err) {
      console.error('Failed to advance time:', err);
    }
  };

  const handleShelterSelect = (shelter: Shelter) => {
    setSelectedShelter(shelter);
    // Center map on selected shelter
    setMapView({
      longitude: shelter.location_lon,
      latitude: shelter.location_lat,
      zoom: 13,
    });
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
