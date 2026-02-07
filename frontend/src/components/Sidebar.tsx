'use client';

import { useState } from 'react';
import {
  Home,
  MapPin,
  Users,
  Package,
  ChevronDown,
  ChevronRight,
  Filter,
  AlertCircle,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import type { Shelter, Event, EventType } from '@/types';
import clsx from 'clsx';

interface SidebarProps {
  shelters: Shelter[];
  events: Event[];
  selectedShelter: Shelter | null;
  onShelterSelect: (shelter: Shelter) => void;
}

// Event type colors and icons
const EVENT_TYPE_CONFIG: Record<EventType, { color: string; label: string }> = {
  road_closure: { color: 'text-danger-600', label: 'Road Closure' },
  flooding: { color: 'text-blue-600', label: 'Flooding' },
  bridge_collapse: { color: 'text-danger-700', label: 'Bridge Collapse' },
  shelter_opening: { color: 'text-success-600', label: 'Shelter Opening' },
  shelter_closing: { color: 'text-warning-600', label: 'Shelter Closing' },
  supply_request: { color: 'text-purple-600', label: 'Supply Request' },
  power_outage: { color: 'text-gray-600', label: 'Power Outage' },
  infrastructure_damage: { color: 'text-orange-600', label: 'Infrastructure Damage' },
  rescue_needed: { color: 'text-danger-500', label: 'Rescue Needed' },
  road_clear: { color: 'text-success-500', label: 'Road Clear' },
};

export function Sidebar({
  shelters,
  events,
  selectedShelter,
  onShelterSelect,
}: SidebarProps) {
  const [sheltersExpanded, setSheltersExpanded] = useState(true);
  const [eventsExpanded, setEventsExpanded] = useState(true);
  const [filterOpen, setFilterOpen] = useState(false);

  // Group events by type for display
  const eventsByType = events.reduce((acc, event) => {
    const type = event.event_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(event);
    return acc;
  }, {} as Record<EventType, Event[]>);

  const getShelterStatusIcon = (status: string) => {
    switch (status) {
      case 'open':
        return <CheckCircle className="w-4 h-4 text-success-500" />;
      case 'full':
        return <AlertCircle className="w-4 h-4 text-warning-500" />;
      case 'closed':
        return <XCircle className="w-4 h-4 text-gray-400" />;
      default:
        return null;
    }
  };

  const getOccupancyColor = (shelter: Shelter) => {
    const ratio = shelter.current_occupancy / shelter.capacity;
    if (ratio >= 0.9) return 'bg-danger-500';
    if (ratio >= 0.7) return 'bg-warning-500';
    return 'bg-success-500';
  };

  return (
    <aside className="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            Situation Overview
          </h2>
          <button
            onClick={() => setFilterOpen(!filterOpen)}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            title="Filter"
          >
            <Filter className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        {/* Stats summary */}
        <div className="mt-3 grid grid-cols-3 gap-2">
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-primary-600">{shelters.length}</div>
            <div className="text-xs text-gray-500">Shelters</div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-warning-600">
              {events.filter((e) => e.event_type === 'road_closure').length}
            </div>
            <div className="text-xs text-gray-500">Closures</div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-danger-600">
              {events.filter((e) => e.event_type === 'flooding').length}
            </div>
            <div className="text-xs text-gray-500">Floods</div>
          </div>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {/* Shelters section */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setSheltersExpanded(!sheltersExpanded)}
            className="w-full p-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <div className="flex items-center gap-2">
              <Home className="w-4 h-4 text-primary-600" />
              <span className="font-medium text-gray-900 dark:text-white">
                Shelters ({shelters.length})
              </span>
            </div>
            {sheltersExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {sheltersExpanded && (
            <div className="pb-2">
              {shelters.length === 0 ? (
                <div className="px-4 py-2 text-sm text-gray-500">
                  No shelters loaded
                </div>
              ) : (
                shelters.map((shelter) => (
                  <button
                    key={shelter.id}
                    onClick={() => onShelterSelect(shelter)}
                    className={clsx(
                      'w-full px-4 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors',
                      selectedShelter?.id === shelter.id && 'bg-primary-50 dark:bg-primary-900/20'
                    )}
                  >
                    <div className="flex items-start gap-2">
                      {getShelterStatusIcon(shelter.status)}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {shelter.name}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <Users className="w-3 h-3 text-gray-400" />
                          <span className="text-xs text-gray-500">
                            {shelter.current_occupancy}/{shelter.capacity}
                          </span>
                          {/* Occupancy bar */}
                          <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                            <div
                              className={clsx('h-full rounded-full', getOccupancyColor(shelter))}
                              style={{
                                width: `${Math.min(100, (shelter.current_occupancy / shelter.capacity) * 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                        {/* Needs tags */}
                        {shelter.needs.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {shelter.needs.slice(0, 3).map((need) => (
                              <span
                                key={need}
                                className="inline-flex items-center px-1.5 py-0.5 text-xs
                                         bg-warning-100 dark:bg-warning-900/30
                                         text-warning-700 dark:text-warning-400 rounded"
                              >
                                <Package className="w-2.5 h-2.5 mr-0.5" />
                                {need}
                              </span>
                            ))}
                            {shelter.needs.length > 3 && (
                              <span className="text-xs text-gray-400">
                                +{shelter.needs.length - 3} more
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* Events section */}
        <div>
          <button
            onClick={() => setEventsExpanded(!eventsExpanded)}
            className="w-full p-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-danger-600" />
              <span className="font-medium text-gray-900 dark:text-white">
                Events ({events.length})
              </span>
            </div>
            {eventsExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {eventsExpanded && (
            <div className="pb-2 px-4 space-y-2">
              {Object.entries(eventsByType).map(([type, typeEvents]) => {
                const config = EVENT_TYPE_CONFIG[type as EventType];
                return (
                  <div key={type} className="text-sm">
                    <div className={clsx('font-medium', config?.color || 'text-gray-600')}>
                      {config?.label || type} ({typeEvents.length})
                    </div>
                    {/* TODO: Expand to show individual events */}
                  </div>
                );
              })}
              {events.length === 0 && (
                <div className="text-sm text-gray-500">No events loaded</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Filter panel */}
      {filterOpen && (
        <div className="absolute left-80 top-16 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 z-50">
          <h3 className="font-medium text-gray-900 dark:text-white mb-3">Filters</h3>
          {/* TODO: Implement filter checkboxes for event types, sources, etc. */}
          <p className="text-sm text-gray-500">Filter options coming soon...</p>
        </div>
      )}
    </aside>
  );
}
