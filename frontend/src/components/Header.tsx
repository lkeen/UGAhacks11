'use client';

import { useState } from 'react';
import {
  Clock,
  FastForward,
  Wifi,
  WifiOff,
  AlertTriangle,
} from 'lucide-react';
import { format, parseISO } from 'date-fns';

interface HeaderProps {
  scenarioTime: string;
  onTimeChange: (time: string) => void;
  onAdvanceTime: (hours: number) => void;
  isConnected: boolean;
}

export function Header({
  scenarioTime,
  onTimeChange,
  onAdvanceTime,
  isConnected,
}: HeaderProps) {
  const [isTimePickerOpen, setIsTimePickerOpen] = useState(false);

  const formattedTime = (() => {
    try {
      return format(parseISO(scenarioTime), 'MMM d, yyyy HH:mm');
    } catch {
      return scenarioTime;
    }
  })();

  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Logo and Title */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
            <AlertTriangle className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white">
              Disaster Relief Optimizer
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Hurricane Helene Response - Western NC
            </p>
          </div>
        </div>

        {/* Scenario Time Controls */}
        <div className="flex items-center gap-4">
          {/* Time display */}
          <div className="flex items-center gap-2 bg-gray-100 dark:bg-gray-700 rounded-lg px-3 py-2">
            <Clock className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Scenario Time:
            </span>
            <button
              onClick={() => setIsTimePickerOpen(!isTimePickerOpen)}
              className="text-sm font-bold text-primary-600 dark:text-primary-400 hover:underline"
            >
              {formattedTime}
            </button>
          </div>

          {/* Quick time advance buttons */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500 mr-1">Advance:</span>
            {[1, 6, 12, 24].map((hours) => (
              <button
                key={hours}
                onClick={() => onAdvanceTime(hours)}
                className="px-2 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700
                         hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
                title={`Advance time by ${hours} hour${hours > 1 ? 's' : ''}`}
              >
                <FastForward className="w-3 h-3 inline mr-1" />
                {hours}h
              </button>
            ))}
          </div>

          {/* Connection status */}
          <div
            className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
              isConnected
                ? 'bg-success-50 dark:bg-success-900/20'
                : 'bg-danger-50 dark:bg-danger-900/20'
            }`}
          >
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4 text-success-600" />
                <span className="text-xs font-medium text-success-700 dark:text-success-400">
                  Connected
                </span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-danger-600" />
                <span className="text-xs font-medium text-danger-700 dark:text-danger-400">
                  Disconnected
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Time picker dropdown */}
      {isTimePickerOpen && (
        <div className="absolute top-16 right-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 z-50">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Set Scenario Time
          </h3>
          <input
            type="datetime-local"
            value={scenarioTime.slice(0, 16)}
            onChange={(e) => {
              onTimeChange(new Date(e.target.value).toISOString());
              setIsTimePickerOpen(false);
            }}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
          <div className="mt-2 text-xs text-gray-500">
            Hurricane Helene timeline: Sept 26-30, 2024
          </div>
          {/* Quick presets */}
          <div className="mt-3 flex flex-wrap gap-1">
            {[
              { label: 'Landfall', time: '2024-09-27T03:00:00Z' },
              { label: '+6h', time: '2024-09-27T09:00:00Z' },
              { label: '+12h', time: '2024-09-27T15:00:00Z' },
              { label: '+24h', time: '2024-09-28T03:00:00Z' },
              { label: '+48h', time: '2024-09-29T03:00:00Z' },
            ].map((preset) => (
              <button
                key={preset.label}
                onClick={() => {
                  onTimeChange(preset.time);
                  setIsTimePickerOpen(false);
                }}
                className="px-2 py-1 text-xs bg-primary-100 dark:bg-primary-900
                         text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}
