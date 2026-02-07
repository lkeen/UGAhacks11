'use client';

import { useState } from 'react';
import {
  Home,
  Users,
  Package,
  ChevronDown,
  ChevronRight,
  Filter,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Phone,
  MapPin,
  Zap,
  Heart,
  PawPrint,
  Accessibility,
  X,
  Target,
} from 'lucide-react';
import type { Shelter, Event, EventType } from '@/types';
import clsx from 'clsx';
import { format } from 'date-fns';

interface SidebarProps {
  shelters: Shelter[];
  events: Event[];
  selectedShelter: Shelter | null;
  onShelterSelect: (shelter: Shelter | null) => void;
  highlightedEventType: EventType | null;
  onEventTypeSelect: (type: EventType | null) => void;
  highlightedEventId: number | string | null;
  onEventSelect: (event: Event | null) => void;
}

// Event type colors - comprehensive list matching Map.tsx
const EVENT_TYPE_CONFIG: Record<string, { color: string; hex: string; label: string }> = {
  road_closure: { color: 'text-red-600', hex: '#dc2626', label: 'Road Closures' },
  road_damage: { color: 'text-orange-500', hex: '#f97316', label: 'Road Damage' },
  flooding: { color: 'text-blue-600', hex: '#2563eb', label: 'Flooding' },
  bridge_collapse: { color: 'text-red-800', hex: '#991b1b', label: 'Bridge Collapse' },
  shelter_opening: { color: 'text-green-600', hex: '#16a34a', label: 'Shelter Opening' },
  shelter_closing: { color: 'text-yellow-600', hex: '#ca8a04', label: 'Shelter Closing' },
  supply_request: { color: 'text-purple-600', hex: '#9333ea', label: 'Supply Request' },
  supplies_needed: { color: 'text-purple-500', hex: '#a855f7', label: 'Supplies Needed' },
  power_outage: { color: 'text-gray-500', hex: '#6b7280', label: 'Power Outage' },
  infrastructure_damage: { color: 'text-orange-600', hex: '#ea580c', label: 'Infrastructure Damage' },
  rescue_needed: { color: 'text-rose-600', hex: '#e11d48', label: 'Rescue Needed' },
  road_clear: { color: 'text-green-500', hex: '#22c55e', label: 'Road Clear' },
  evacuation: { color: 'text-red-600', hex: '#dc2626', label: 'Evacuation' },
  medical_emergency: { color: 'text-pink-500', hex: '#ec4899', label: 'Medical Emergency' },
  water_contamination: { color: 'text-cyan-600', hex: '#0891b2', label: 'Water Contamination' },
};

export function Sidebar({
  shelters,
  events,
  selectedShelter,
  onShelterSelect,
  highlightedEventType,
  onEventTypeSelect,
  highlightedEventId,
  onEventSelect,
}: SidebarProps) {
  const [sheltersExpanded, setSheltersExpanded] = useState(true);
  const [eventsExpanded, setEventsExpanded] = useState(true);
  const [expandedEventTypes, setExpandedEventTypes] = useState<Set<string>>(new Set());
  const [filterOpen, setFilterOpen] = useState(false);

  // Group events by type for display
  const eventsByType = (events || []).reduce((acc, event) => {
    const type = event.event_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(event);
    return acc;
  }, {} as Record<string, Event[]>);

  const toggleEventType = (type: string) => {
    const newExpanded = new Set(expandedEventTypes);
    if (newExpanded.has(type)) {
      newExpanded.delete(type);
      // If collapsing, also unhighlight
      if (highlightedEventType === type) {
        onEventTypeSelect(null);
      }
      onEventSelect(null);
    } else {
      newExpanded.add(type);
      // Highlight this type on the map
      onEventTypeSelect(type as EventType);
      onEventSelect(null);
    }
    setExpandedEventTypes(newExpanded);
  };

  const handleEventClick = (event: Event) => {
    if (highlightedEventId === event.id) {
      // Deselect if already selected - restore type highlighting
      onEventSelect(null);
      onEventTypeSelect(event.event_type as EventType);
    } else {
      // Select this specific event
      onEventSelect(event);
      // Clear type-level highlighting
      onEventTypeSelect(null);
    }
  };

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

  const formatEventTime = (timestamp: string | undefined) => {
    if (!timestamp) return '';
    try {
      return format(new Date(timestamp), 'MMM d, h:mm a');
    } catch {
      return '';
    }
  };

  const getEventConfig = (type: string) => {
    return EVENT_TYPE_CONFIG[type] || { color: 'text-gray-600', hex: '#6b7280', label: type.replace(/_/g, ' ') };
  };

  // If a shelter is selected, show the detail view
  if (selectedShelter) {
    return (
      <aside className="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden">
        {/* Header with back button */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Shelter Details
            </h2>
            <button
              onClick={() => onShelterSelect(null)}
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
              title="Close"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Shelter detail content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Name and status */}
          <div className="mb-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">
              {selectedShelter.name}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              {getShelterStatusIcon(selectedShelter.status)}
              <span className={clsx(
                'text-sm font-medium capitalize',
                selectedShelter.status === 'open' ? 'text-success-600' :
                selectedShelter.status === 'full' ? 'text-warning-600' : 'text-gray-500'
              )}>
                {selectedShelter.status}
              </span>
            </div>
          </div>

          {/* Address */}
          {selectedShelter.address && (
            <div className="mb-4">
              <div className="flex items-start gap-2">
                <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  {selectedShelter.address}
                </p>
              </div>
            </div>
          )}

          {/* Occupancy */}
          <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Occupancy</span>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {selectedShelter.current_occupancy} / {selectedShelter.capacity}
              </span>
            </div>
            <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
              <div
                className={clsx('h-full rounded-full transition-all', getOccupancyColor(selectedShelter))}
                style={{
                  width: `${Math.min(100, (selectedShelter.current_occupancy / selectedShelter.capacity) * 100)}%`,
                }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {Math.round((selectedShelter.current_occupancy / selectedShelter.capacity) * 100)}% full
              ({selectedShelter.capacity - selectedShelter.current_occupancy} spots available)
            </p>
          </div>

          {/* Needs */}
          {selectedShelter.needs && selectedShelter.needs.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Current Needs
              </h4>
              <div className="flex flex-wrap gap-2">
                {selectedShelter.needs.map((need) => (
                  <span
                    key={need}
                    className="inline-flex items-center px-2 py-1 text-sm
                             bg-warning-100 dark:bg-warning-900/30
                             text-warning-700 dark:text-warning-400 rounded-lg"
                  >
                    <Package className="w-3.5 h-3.5 mr-1" />
                    {need}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Contact */}
          {(selectedShelter.contact_name || selectedShelter.contact_phone) && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Contact
              </h4>
              {selectedShelter.contact_name && (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedShelter.contact_name}
                </p>
              )}
              {selectedShelter.contact_phone && (
                <div className="flex items-center gap-2 mt-1">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <a
                    href={`tel:${selectedShelter.contact_phone}`}
                    className="text-sm text-primary-600 hover:underline"
                  >
                    {selectedShelter.contact_phone}
                  </a>
                </div>
              )}
            </div>
          )}

          {/* Amenities */}
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Amenities
            </h4>
            <div className="grid grid-cols-2 gap-2">
              <div className={clsx(
                'flex items-center gap-2 p-2 rounded-lg text-sm',
                selectedShelter.has_generator ? 'bg-success-50 text-success-700' : 'bg-gray-100 text-gray-400'
              )}>
                <Zap className="w-4 h-4" />
                <span>Generator</span>
              </div>
              <div className={clsx(
                'flex items-center gap-2 p-2 rounded-lg text-sm',
                selectedShelter.has_medical ? 'bg-success-50 text-success-700' : 'bg-gray-100 text-gray-400'
              )}>
                <Heart className="w-4 h-4" />
                <span>Medical</span>
              </div>
              <div className={clsx(
                'flex items-center gap-2 p-2 rounded-lg text-sm',
                selectedShelter.accepts_pets ? 'bg-success-50 text-success-700' : 'bg-gray-100 text-gray-400'
              )}>
                <PawPrint className="w-4 h-4" />
                <span>Pets OK</span>
              </div>
              <div className={clsx(
                'flex items-center gap-2 p-2 rounded-lg text-sm',
                selectedShelter.wheelchair_accessible ? 'bg-success-50 text-success-700' : 'bg-gray-100 text-gray-400'
              )}>
                <Accessibility className="w-4 h-4" />
                <span>Accessible</span>
              </div>
            </div>
          </div>

          {/* Coordinates */}
          <div className="text-xs text-gray-400">
            <p>Lat: {selectedShelter.location_lat?.toFixed(4)}</p>
            <p>Lon: {selectedShelter.location_lon?.toFixed(4)}</p>
          </div>
        </div>
      </aside>
    );
  }

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
              {(events || []).filter((e) => e.event_type === 'road_closure').length}
            </div>
            <div className="text-xs text-gray-500">Closures</div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-danger-600">
              {(events || []).filter((e) => e.event_type === 'flooding').length}
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
                    className="w-full px-4 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
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
                        {shelter.needs && shelter.needs.length > 0 && (
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
                Events ({(events || []).length})
              </span>
            </div>
            {eventsExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {eventsExpanded && (
            <div className="pb-2">
              {Object.entries(eventsByType).map(([type, typeEvents]) => {
                const config = getEventConfig(type);
                const isExpanded = expandedEventTypes.has(type);
                const isHighlighted = highlightedEventType === type;

                return (
                  <div key={type} className="border-b border-gray-100 dark:border-gray-700 last:border-0">
                    {/* Category header - clickable */}
                    <button
                      onClick={() => toggleEventType(type)}
                      className={clsx(
                        'w-full px-4 py-2 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors',
                        isHighlighted && 'bg-gray-100 dark:bg-gray-700'
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: config.hex }}
                        />
                        <span className={clsx('text-sm font-medium', config.color)}>
                          {config.label}
                        </span>
                        <span className="text-xs text-gray-400">({typeEvents.length})</span>
                      </div>
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      )}
                    </button>

                    {/* Expanded event list */}
                    {isExpanded && (
                      <div className="px-4 pb-2 space-y-2">
                        {typeEvents.slice(0, 10).map((event, idx) => {
                          const isSelected = highlightedEventId === event.id;
                          return (
                            <button
                              key={event.id || idx}
                              onClick={() => handleEventClick(event)}
                              className={clsx(
                                'w-full text-left p-2 rounded-lg text-xs transition-all',
                                isSelected
                                  ? 'bg-primary-100 dark:bg-primary-900/30 ring-2 ring-primary-500'
                                  : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600'
                              )}
                              style={{ borderLeft: `3px solid ${config.hex}` }}
                            >
                              <div className="flex items-start justify-between gap-2">
                                <p className="text-gray-700 dark:text-gray-300 line-clamp-2 flex-1">
                                  {event.description || 'No description'}
                                </p>
                                {isSelected && (
                                  <Target className="w-4 h-4 text-primary-500 flex-shrink-0" />
                                )}
                              </div>
                              <div className="flex items-center gap-2 mt-1 text-gray-500">
                                <Clock className="w-3 h-3" />
                                <span>{formatEventTime(event.timestamp)}</span>
                                {event.source && (
                                  <>
                                    <span>•</span>
                                    <span className="capitalize">{event.source}</span>
                                  </>
                                )}
                              </div>
                            </button>
                          );
                        })}
                        {typeEvents.length > 10 && (
                          <p className="text-xs text-gray-400 text-center">
                            +{typeEvents.length - 10} more events
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
              {(events || []).length === 0 && (
                <div className="px-4 py-2 text-sm text-gray-500">No events loaded</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Filter panel */}
      {filterOpen && (
        <div className="absolute left-80 top-16 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 z-50">
          <h3 className="font-medium text-gray-900 dark:text-white mb-3">Filters</h3>
          <p className="text-sm text-gray-500">Filter options coming soon...</p>
        </div>
      )}
    </aside>
  );
}
