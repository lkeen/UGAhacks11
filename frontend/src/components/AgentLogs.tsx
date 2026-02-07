'use client';

import { useState } from 'react';
import {
  Activity,
  Satellite,
  MessageSquare,
  Building,
  Route,
  Bot,
  Info,
  AlertTriangle,
  XCircle,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import type { AgentLogEntry, AgentReport } from '@/types';
import clsx from 'clsx';

interface AgentLogsProps {
  logs: AgentLogEntry[];
  reports: AgentReport[];
}

// Agent configuration for display
const AGENT_CONFIG: Record<string, { icon: React.ComponentType<any>; color: string }> = {
  satellite: { icon: Satellite, color: 'text-purple-500' },
  social_media: { icon: MessageSquare, color: 'text-blue-500' },
  official_data: { icon: Building, color: 'text-green-500' },
  road_network: { icon: Route, color: 'text-orange-500' },
  orchestrator: { icon: Bot, color: 'text-primary-500' },
  system: { icon: Activity, color: 'text-gray-500' },
};

const LOG_LEVEL_CONFIG: Record<AgentLogEntry['level'], { icon: React.ComponentType<any>; color: string }> = {
  info: { icon: Info, color: 'text-blue-500' },
  warning: { icon: AlertTriangle, color: 'text-warning-500' },
  error: { icon: XCircle, color: 'text-danger-500' },
  success: { icon: CheckCircle, color: 'text-success-500' },
};

export function AgentLogs({ logs, reports }: AgentLogsProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<'logs' | 'reports'>('logs');

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className="bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 p-2 flex flex-col items-center gap-2"
      >
        <ChevronLeft className="w-4 h-4 text-gray-500" />
        <span className="text-xs text-gray-500 writing-vertical">Agent Logs</span>
      </button>
    );
  }

  return (
    <aside className="w-80 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden">
      {/* Header with collapse button */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary-600" />
          <h2 className="font-semibold text-gray-900 dark:text-white">Agent Activity</h2>
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
        >
          <ChevronRight className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* Tab switcher */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('logs')}
          className={clsx(
            'flex-1 px-4 py-2 text-sm font-medium transition-colors',
            activeTab === 'logs'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          )}
        >
          Logs ({logs.length})
        </button>
        <button
          onClick={() => setActiveTab('reports')}
          className={clsx(
            'flex-1 px-4 py-2 text-sm font-medium transition-colors',
            activeTab === 'reports'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          )}
        >
          Reports ({reports.length})
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {activeTab === 'logs' ? (
          <LogsList logs={logs} />
        ) : (
          <ReportsList reports={reports} />
        )}
      </div>

      {/* Agent status indicators */}
      <div className="p-3 border-t border-gray-200 dark:border-gray-700">
        <h3 className="text-xs font-medium text-gray-500 mb-2">Agent Status</h3>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(AGENT_CONFIG).map(([name, config]) => {
            if (name === 'system') return null;
            const Icon = config.icon;
            // TODO: Track actual agent status from backend
            const isActive = logs.some(
              (log) => log.agent_name === name && Date.now() - new Date(log.timestamp).getTime() < 60000
            );
            return (
              <div
                key={name}
                className="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-700 rounded"
              >
                <Icon className={clsx('w-4 h-4', config.color)} />
                <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">
                  {name.replace('_', ' ')}
                </span>
                <span
                  className={clsx(
                    'w-2 h-2 rounded-full ml-auto',
                    isActive ? 'bg-success-500 status-pulse' : 'bg-danger-500'
                  )}
                />
              </div>
            );
          })}
        </div>
      </div>
    </aside>
  );
}

function LogsList({ logs }: { logs: AgentLogEntry[] }) {
  if (logs.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No activity logs yet
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-100 dark:divide-gray-700">
      {logs.map((log) => {
        const agentConfig = AGENT_CONFIG[log.agent_name] || AGENT_CONFIG.system;
        const levelConfig = LOG_LEVEL_CONFIG[log.level];
        const AgentIcon = agentConfig.icon;
        const LevelIcon = levelConfig.icon;

        return (
          <div
            key={log.id}
            className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 log-entry-animate"
          >
            <div className="flex items-start gap-2">
              <AgentIcon className={clsx('w-4 h-4 mt-0.5', agentConfig.color)} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1">
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300 capitalize">
                    {log.agent_name.replace('_', ' ')}
                  </span>
                  <LevelIcon className={clsx('w-3 h-3', levelConfig.color)} />
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5 break-words">
                  {log.message}
                </p>
                <span className="text-xs text-gray-400 mt-1 block">
                  {formatTimestamp(log.timestamp)}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ReportsList({ reports }: { reports: AgentReport[] }) {
  if (reports.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No agent reports yet. Click &quot;Gather Intelligence&quot; to fetch reports.
      </div>
    );
  }

  // Group reports by agent
  const reportsByAgent = reports.reduce((acc, report) => {
    const agent = report.agent_name;
    if (!acc[agent]) acc[agent] = [];
    acc[agent].push(report);
    return acc;
  }, {} as Record<string, AgentReport[]>);

  return (
    <div className="divide-y divide-gray-100 dark:divide-gray-700">
      {Object.entries(reportsByAgent).map(([agent, agentReports]) => {
        const config = AGENT_CONFIG[agent] || AGENT_CONFIG.system;
        const Icon = config.icon;

        return (
          <details key={agent} className="group">
            <summary className="p-3 flex items-center gap-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50">
              <Icon className={clsx('w-4 h-4', config.color)} />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                {agent.replace('_', ' ')}
              </span>
              <span className="text-xs text-gray-500 ml-auto">
                {agentReports.length} reports
              </span>
            </summary>
            <div className="px-3 pb-3 space-y-2">
              {agentReports.slice(0, 5).map((report) => (
                <div
                  key={report.id}
                  className="p-2 bg-gray-50 dark:bg-gray-700 rounded text-xs"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-gray-700 dark:text-gray-300 capitalize">
                      {report.event_type.replace('_', ' ')}
                    </span>
                    <span
                      className={clsx(
                        'px-1.5 py-0.5 rounded text-xs',
                        report.confidence >= 0.8
                          ? 'bg-success-100 text-success-700'
                          : report.confidence >= 0.6
                          ? 'bg-warning-100 text-warning-700'
                          : 'bg-danger-100 text-danger-700'
                      )}
                    >
                      {Math.round(report.confidence * 100)}%
                    </span>
                  </div>
                  <p className="text-gray-600 dark:text-gray-400 line-clamp-2">
                    {report.description}
                  </p>
                </div>
              ))}
              {agentReports.length > 5 && (
                <p className="text-xs text-gray-500 text-center">
                  +{agentReports.length - 5} more reports
                </p>
              )}
            </div>
          </details>
        );
      })}
    </div>
  );
}

function formatTimestamp(timestamp: string): string {
  try {
    return format(parseISO(timestamp), 'HH:mm:ss');
  } catch {
    return timestamp;
  }
}
