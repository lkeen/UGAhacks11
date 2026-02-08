'use client';

import { useState } from 'react';
import {
  Send,
  Loader2,
  ChevronDown,
  ChevronUp,
  Truck,
  MapPin,
  Clock,
  AlertTriangle,
  CheckCircle,
  Navigation,
  ArrowRight,
  CornerUpRight,
  CornerUpLeft,
  ArrowUp,
} from 'lucide-react';
import type { QueryResponse, DirectionStep } from '@/types';
import { formatDistance, formatDuration } from '@/lib/api';
import clsx from 'clsx';

interface QueryPanelProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
  response: QueryResponse | null;
  error: string | null;
  selectedRouteId: string | null;
  onRouteSelect: (routeId: string | null) => void;
}

// Example queries for quick access
const EXAMPLE_QUERIES = [
  'I have 200 cases of water at Asheville Regional Airport. Where should they go?',
  'We have medical supplies at the FEMA staging area. Which shelters need them most?',
  'A truck with 100 blankets and 50 cots is available at Hendersonville. Plan deliveries.',
  'What are the current road conditions to reach Brevard College shelter?',
];

export function QueryPanel({
  onSubmit,
  isLoading,
  response,
  error,
  selectedRouteId,
  onRouteSelect,
}: QueryPanelProps) {
  const [query, setQuery] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);
  const [showExamples, setShowExamples] = useState(false);
  const [isPlanExpanded, setIsPlanExpanded] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  const handleExampleClick = (example: string) => {
    setQuery(example);
    setShowExamples(false);
  };

  const handleRouteClick = (routeId: string) => {
    onRouteSelect(selectedRouteId === routeId ? null : routeId);
  };

  // Compute totals from actual routes
  const routes = response?.delivery_plan?.routes || [];
  const totalDistance = routes.reduce((sum, r) => sum + (r.distance_m || 0), 0);
  const totalDuration = routes.reduce((sum, r) => sum + (r.estimated_duration_min || 0), 0);
  const sheltersServed = routes.length;

  return (
    <div className="w-80 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden flex-shrink-0">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between bg-primary-600 text-white flex-shrink-0"
      >
        <div className="flex items-center gap-2">
          <Truck className="w-5 h-5" />
          <span className="font-medium text-sm">Delivery Planner</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      {isExpanded && (
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {/* Query input */}
          <div className="p-3">
            <form onSubmit={handleSubmit}>
              <div className="relative">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Describe your supplies and location..."
                  className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm
                           focus:ring-2 focus:ring-primary-500 focus:border-transparent
                           resize-none"
                  rows={2}
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={!query.trim() || isLoading}
                  className="absolute right-1.5 bottom-1.5 p-1.5 bg-primary-600 text-white rounded-lg
                           hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed
                           transition-colors"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </div>
            </form>

            {/* Example queries toggle */}
            <button
              onClick={() => setShowExamples(!showExamples)}
              className="mt-1.5 text-xs text-primary-600 dark:text-primary-400 hover:underline"
            >
              {showExamples ? 'Hide examples' : 'Show examples'}
            </button>

            {showExamples && (
              <div className="mt-1.5 space-y-1">
                {EXAMPLE_QUERIES.map((example, i) => (
                  <button
                    key={i}
                    onClick={() => handleExampleClick(example)}
                    className="w-full text-left text-xs text-gray-600 dark:text-gray-400
                             hover:text-primary-600 dark:hover:text-primary-400 py-0.5"
                  >
                    &ldquo;{example}&rdquo;
                  </button>
                ))}
              </div>
            )}

            {/* Error display */}
            {error && (
              <div className="mt-2 p-2 bg-danger-50 dark:bg-danger-900/20 rounded-lg flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-danger-600 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-danger-700 dark:text-danger-400">{error}</p>
              </div>
            )}
          </div>

          {/* Delivery plan response */}
          {response && !error && (
            <div className="border-t border-gray-200 dark:border-gray-700">
              {/* Collapsible header */}
              <button
                onClick={() => setIsPlanExpanded(!isPlanExpanded)}
                className="w-full px-3 py-2 flex items-center justify-between bg-success-50 dark:bg-success-900/20"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-success-600" />
                  <span className="text-sm font-medium text-success-700 dark:text-success-400">
                    Delivery Plan
                  </span>
                </div>
                {isPlanExpanded ? (
                  <ChevronUp className="w-4 h-4 text-success-600" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-success-600" />
                )}
              </button>

              {isPlanExpanded && (
                <div className="p-3">
                  {/* Situational awareness summary */}
                  <div className="grid grid-cols-3 gap-1.5 text-center mb-3">
                    <div className="bg-gray-50 dark:bg-gray-700 rounded p-1.5">
                      <div className="text-sm font-bold text-primary-600">
                        {response.situational_awareness.total_reports}
                      </div>
                      <div className="text-[10px] text-gray-500">Reports</div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700 rounded p-1.5">
                      <div className="text-sm font-bold text-danger-600">
                        {response.situational_awareness.blocked_roads}
                      </div>
                      <div className="text-[10px] text-gray-500">Blocked</div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700 rounded p-1.5">
                      <div className="text-sm font-bold text-success-600">
                        {sheltersServed}
                      </div>
                      <div className="text-[10px] text-gray-500">Shelters</div>
                    </div>
                  </div>

                  {/* Routes list */}
                  <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Routes ({routes.length})
                  </h4>

                  <div className="space-y-2">
                    {routes.map((route, index) => (
                      <button
                        key={route.id}
                        onClick={() => handleRouteClick(route.id)}
                        className={clsx(
                          'w-full text-left p-2.5 rounded-lg transition-all',
                          selectedRouteId === route.id
                            ? 'bg-primary-50 dark:bg-primary-900/30 ring-2 ring-primary-500'
                            : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600'
                        )}
                      >
                        <div className="flex items-start justify-between gap-1">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="w-5 h-5 rounded-full bg-primary-600 text-white text-[10px]
                                           flex items-center justify-center font-medium flex-shrink-0">
                              {index + 1}
                            </span>
                            <div className="min-w-0">
                              <p className="text-xs font-medium text-gray-900 dark:text-white truncate">
                                {route.destination.address || `Route ${index + 1}`}
                              </p>
                              <div className="flex items-center gap-2 text-[10px] text-gray-500 mt-0.5">
                                <span className="flex items-center gap-0.5">
                                  <MapPin className="w-2.5 h-2.5" />
                                  {formatDistance(route.distance_m)}
                                </span>
                                <span className="flex items-center gap-0.5">
                                  <Clock className="w-2.5 h-2.5" />
                                  {formatDuration(route.estimated_duration_min)}
                                </span>
                              </div>
                            </div>
                          </div>
                          <div
                            className={clsx(
                              'px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0',
                              route.confidence >= 0.8
                                ? 'bg-success-100 text-success-700'
                                : route.confidence >= 0.6
                                ? 'bg-warning-100 text-warning-700'
                                : 'bg-danger-100 text-danger-700'
                            )}
                          >
                            {Math.round(route.confidence * 100)}%
                          </div>
                        </div>

                        {/* Hazards avoided */}
                        {route.hazards_avoided.length > 0 && (
                          <div className="mt-1.5 text-[10px] text-gray-600 dark:text-gray-400">
                            <span className="font-medium">Avoiding:</span>{' '}
                            {route.hazards_avoided
                              .map((h) => h.name || h.description || 'Unknown hazard')
                              .filter(Boolean)
                              .slice(0, 2)
                              .join(', ')}
                            {route.hazards_avoided.length > 2 &&
                              ` +${route.hazards_avoided.length - 2} more`}
                          </div>
                        )}
                      </button>
                    ))}
                  </div>

                  {/* Turn-by-turn directions for selected route */}
                  {selectedRouteId && (() => {
                    const selectedRoute = routes.find(r => r.id === selectedRouteId);
                    if (!selectedRoute?.directions?.length) return null;
                    return (
                      <div className="mt-3 border border-primary-200 dark:border-primary-800 rounded-lg overflow-hidden">
                        <div className="px-3 py-1.5 bg-primary-50 dark:bg-primary-900/30 flex items-center gap-1.5">
                          <Navigation className="w-3.5 h-3.5 text-primary-600" />
                          <span className="text-xs font-medium text-primary-700 dark:text-primary-400">
                            Directions
                          </span>
                        </div>
                        <div className="max-h-48 overflow-y-auto custom-scrollbar">
                          {selectedRoute.directions
                            .filter(step => step.maneuver_type !== 'arrive' || step.instruction)
                            .map((step: DirectionStep, i: number) => (
                            <div
                              key={i}
                              className="flex items-start gap-2 px-3 py-1.5 border-t border-gray-100 dark:border-gray-700 first:border-t-0"
                            >
                              <div className="mt-0.5 flex-shrink-0">
                                {step.maneuver_type === 'turn' && step.maneuver_modifier?.includes('left') ? (
                                  <CornerUpLeft className="w-3 h-3 text-primary-500" />
                                ) : step.maneuver_type === 'turn' && step.maneuver_modifier?.includes('right') ? (
                                  <CornerUpRight className="w-3 h-3 text-primary-500" />
                                ) : step.maneuver_type === 'arrive' ? (
                                  <MapPin className="w-3 h-3 text-success-500" />
                                ) : step.maneuver_type === 'depart' ? (
                                  <ArrowUp className="w-3 h-3 text-primary-500" />
                                ) : (
                                  <ArrowRight className="w-3 h-3 text-gray-400" />
                                )}
                              </div>
                              <div className="min-w-0 flex-1">
                                <p className="text-[11px] text-gray-800 dark:text-gray-200 leading-tight">
                                  {step.instruction}
                                </p>
                                {step.distance_m > 0 && (
                                  <p className="text-[10px] text-gray-500 mt-0.5">
                                    {formatDistance(step.distance_m)}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Totals */}
                  {routes.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-600 space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-600 dark:text-gray-400">Total Distance:</span>
                        <span className="font-medium text-gray-900 dark:text-white">
                          {formatDistance(totalDistance)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-600 dark:text-gray-400">Total Time:</span>
                        <span className="font-medium text-gray-900 dark:text-white">
                          {formatDuration(totalDuration)}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Reasoning (collapsible) */}
                  {response.reasoning && (
                    <details className="mt-3">
                      <summary className="text-[10px] text-primary-600 dark:text-primary-400 cursor-pointer hover:underline">
                        View AI Reasoning
                      </summary>
                      <div className="mt-1.5 p-2 bg-gray-50 dark:bg-gray-700 rounded text-[10px] text-gray-600 dark:text-gray-400 whitespace-pre-wrap max-h-32 overflow-y-auto custom-scrollbar">
                        {response.reasoning}
                      </div>
                    </details>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
