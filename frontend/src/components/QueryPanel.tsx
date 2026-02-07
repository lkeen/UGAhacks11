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
} from 'lucide-react';
import type { QueryResponse } from '@/types';
import { formatDistance, formatDuration } from '@/lib/api';
import clsx from 'clsx';

interface QueryPanelProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
  response: QueryResponse | null;
  error: string | null;
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
}: QueryPanelProps) {
  const [query, setQuery] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);
  const [showExamples, setShowExamples] = useState(false);

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

  return (
    <div className="absolute top-4 left-4 right-4 max-w-2xl mx-auto z-10">
      {/* Main query input card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
        {/* Header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between bg-primary-600 text-white"
        >
          <div className="flex items-center gap-2">
            <Truck className="w-5 h-5" />
            <span className="font-medium">Delivery Planner</span>
          </div>
          {isExpanded ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>

        {isExpanded && (
          <div className="p-4">
            {/* Query input */}
            <form onSubmit={handleSubmit}>
              <div className="relative">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Describe your supplies and location..."
                  className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-primary-500 focus:border-transparent
                           resize-none"
                  rows={2}
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={!query.trim() || isLoading}
                  className="absolute right-2 bottom-2 p-2 bg-primary-600 text-white rounded-lg
                           hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed
                           transition-colors"
                >
                  {isLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </div>
            </form>

            {/* Example queries toggle */}
            <button
              onClick={() => setShowExamples(!showExamples)}
              className="mt-2 text-xs text-primary-600 dark:text-primary-400 hover:underline"
            >
              {showExamples ? 'Hide examples' : 'Show example queries'}
            </button>

            {showExamples && (
              <div className="mt-2 space-y-1">
                {EXAMPLE_QUERIES.map((example, i) => (
                  <button
                    key={i}
                    onClick={() => handleExampleClick(example)}
                    className="w-full text-left text-xs text-gray-600 dark:text-gray-400
                             hover:text-primary-600 dark:hover:text-primary-400 py-1"
                  >
                    "{example}"
                  </button>
                ))}
              </div>
            )}

            {/* Error display */}
            {error && (
              <div className="mt-3 p-3 bg-danger-50 dark:bg-danger-900/20 rounded-lg flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-danger-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-danger-700 dark:text-danger-400">{error}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Response card */}
      {response && !error && (
        <div className="mt-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          {/* Response header */}
          <div className="px-4 py-3 bg-success-600 text-white flex items-center gap-2">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">Delivery Plan Generated</span>
          </div>

          <div className="p-4">
            {/* Situational awareness summary */}
            <div className="mb-4 grid grid-cols-3 gap-2 text-center">
              <div className="bg-gray-50 dark:bg-gray-700 rounded p-2">
                <div className="text-lg font-bold text-primary-600">
                  {response.situational_awareness.total_reports}
                </div>
                <div className="text-xs text-gray-500">Reports</div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded p-2">
                <div className="text-lg font-bold text-danger-600">
                  {response.situational_awareness.blocked_roads}
                </div>
                <div className="text-xs text-gray-500">Blocked Roads</div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded p-2">
                <div className="text-lg font-bold text-success-600">
                  {response.delivery_plan.shelters_served}
                </div>
                <div className="text-xs text-gray-500">Shelters Served</div>
              </div>
            </div>

            {/* Routes list */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Planned Routes ({response.delivery_plan.routes.length})
              </h4>
              {response.delivery_plan.routes.map((route, index) => (
                <div
                  key={route.id}
                  className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-primary-600 text-white text-xs
                                     flex items-center justify-center font-medium">
                        {index + 1}
                      </span>
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {route.destination.address || `Route ${index + 1}`}
                        </p>
                        <div className="flex items-center gap-3 text-xs text-gray-500 mt-0.5">
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {formatDistance(route.distance_m)}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatDuration(route.estimated_duration_min)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div
                      className={clsx(
                        'px-2 py-0.5 rounded text-xs font-medium',
                        route.confidence >= 0.8
                          ? 'bg-success-100 text-success-700'
                          : route.confidence >= 0.6
                          ? 'bg-warning-100 text-warning-700'
                          : 'bg-danger-100 text-danger-700'
                      )}
                    >
                      {Math.round(route.confidence * 100)}% confidence
                    </div>
                  </div>

                  {/* Hazards avoided */}
                  {route.hazards_avoided.length > 0 && (
                    <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Avoiding:</span>{' '}
                      {route.hazards_avoided
                        .map((h) => h.description)
                        .slice(0, 2)
                        .join(', ')}
                      {route.hazards_avoided.length > 2 &&
                        ` +${route.hazards_avoided.length - 2} more`}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Totals */}
            <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-600 flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Total Distance:</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {formatDistance(response.delivery_plan.total_distance_m)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Total Time:</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {formatDuration(response.delivery_plan.total_duration_min)}
              </span>
            </div>

            {/* Reasoning (collapsible) */}
            {response.reasoning && (
              <details className="mt-4">
                <summary className="text-xs text-primary-600 dark:text-primary-400 cursor-pointer hover:underline">
                  View AI Reasoning
                </summary>
                <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-700 rounded text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap max-h-40 overflow-y-auto custom-scrollbar">
                  {response.reasoning}
                </div>
              </details>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
