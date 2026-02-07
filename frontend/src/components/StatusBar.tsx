'use client';

import {
  Clock,
  Home,
  AlertTriangle,
  Route,
  Activity,
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import type { NetworkStatus } from '@/types';

interface StatusBarProps {
  networkStatus: NetworkStatus | null;
  scenarioTime: string;
  totalEvents: number;
  totalShelters: number;
}

export function StatusBar({
  networkStatus,
  scenarioTime,
  totalEvents,
  totalShelters,
}: StatusBarProps) {
  const formattedTime = (() => {
    try {
      return format(parseISO(scenarioTime), 'MMM d, yyyy HH:mm:ss');
    } catch {
      return scenarioTime;
    }
  })();

  return (
    <footer className="bg-gray-800 text-white px-4 py-2 flex items-center justify-between text-xs">
      {/* Left section - scenario info */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-gray-400" />
          <span className="text-gray-400">Scenario:</span>
          <span className="font-mono">{formattedTime}</span>
        </div>
        <div className="h-4 w-px bg-gray-600" />
        <div className="flex items-center gap-1.5">
          <Home className="w-3.5 h-3.5 text-gray-400" />
          <span>{totalShelters} shelters</span>
        </div>
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-gray-400" />
          <span>{totalEvents} events</span>
        </div>
      </div>

      {/* Center section - network status */}
      {networkStatus && (
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <Route className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-gray-400">Network:</span>
            <span>{networkStatus.total_edges.toLocaleString()} edges</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-danger-500" />
            <span>{networkStatus.blocked_edges} blocked</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-warning-500" />
            <span>{networkStatus.damaged_edges} damaged</span>
          </div>
        </div>
      )}

      {/* Right section - system status */}
      <div className="flex items-center gap-2">
        <Activity className="w-3.5 h-3.5 text-success-500 status-pulse" />
        <span className="text-gray-400">System Online</span>
        <span className="text-gray-500">|</span>
        <span className="text-gray-500">
          Disaster Relief Supply Chain Optimizer v0.1.0
        </span>
      </div>
    </footer>
  );
}
