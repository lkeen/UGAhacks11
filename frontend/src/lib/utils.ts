import { type ClassValue, clsx } from 'clsx';

/**
 * Utility for conditionally joining class names together
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/**
 * Get event type display configuration
 */
export function getEventTypeConfig(eventType: string): {
  color: string;
  bgColor: string;
  label: string;
} {
  const configs: Record<string, { color: string; bgColor: string; label: string }> = {
    road_closure: {
      color: 'text-danger-600',
      bgColor: 'bg-danger-100 dark:bg-danger-900/30',
      label: 'Road Closure',
    },
    flooding: {
      color: 'text-blue-600',
      bgColor: 'bg-blue-100 dark:bg-blue-900/30',
      label: 'Flooding',
    },
    bridge_collapse: {
      color: 'text-danger-700',
      bgColor: 'bg-danger-100 dark:bg-danger-900/30',
      label: 'Bridge Collapse',
    },
    shelter_opening: {
      color: 'text-success-600',
      bgColor: 'bg-success-100 dark:bg-success-900/30',
      label: 'Shelter Opening',
    },
    shelter_closing: {
      color: 'text-warning-600',
      bgColor: 'bg-warning-100 dark:bg-warning-900/30',
      label: 'Shelter Closing',
    },
    supply_request: {
      color: 'text-purple-600',
      bgColor: 'bg-purple-100 dark:bg-purple-900/30',
      label: 'Supply Request',
    },
    power_outage: {
      color: 'text-gray-600',
      bgColor: 'bg-gray-100 dark:bg-gray-700',
      label: 'Power Outage',
    },
    infrastructure_damage: {
      color: 'text-orange-600',
      bgColor: 'bg-orange-100 dark:bg-orange-900/30',
      label: 'Infrastructure Damage',
    },
    rescue_needed: {
      color: 'text-danger-500',
      bgColor: 'bg-danger-100 dark:bg-danger-900/30',
      label: 'Rescue Needed',
    },
    road_clear: {
      color: 'text-success-500',
      bgColor: 'bg-success-100 dark:bg-success-900/30',
      label: 'Road Clear',
    },
  };

  return (
    configs[eventType] || {
      color: 'text-gray-600',
      bgColor: 'bg-gray-100 dark:bg-gray-700',
      label: eventType.replace('_', ' '),
    }
  );
}

/**
 * Get data source display configuration
 */
export function getDataSourceConfig(source: string): {
  color: string;
  label: string;
} {
  const configs: Record<string, { color: string; label: string }> = {
    satellite: { color: 'text-purple-500', label: 'Satellite' },
    twitter: { color: 'text-blue-400', label: 'Twitter' },
    reddit: { color: 'text-orange-500', label: 'Reddit' },
    facebook: { color: 'text-blue-600', label: 'Facebook' },
    fema: { color: 'text-blue-700', label: 'FEMA' },
    ncdot: { color: 'text-green-600', label: 'NCDOT' },
    usgs: { color: 'text-amber-600', label: 'USGS' },
    local_emergency: { color: 'text-red-600', label: 'Local Emergency' },
    news: { color: 'text-gray-600', label: 'News' },
  };

  return (
    configs[source] || {
      color: 'text-gray-500',
      label: source.replace('_', ' '),
    }
  );
}

/**
 * Calculate shelter urgency score (0-1) based on occupancy and needs
 */
export function calculateShelterUrgency(shelter: {
  current_occupancy: number;
  capacity: number;
  needs: string[];
}): number {
  const occupancyRatio = shelter.current_occupancy / shelter.capacity;
  const needsScore = Math.min(shelter.needs.length / 5, 1); // Cap at 5 needs

  // Weight: 60% occupancy, 40% needs
  return occupancyRatio * 0.6 + needsScore * 0.4;
}

/**
 * Get confidence level label and color
 */
export function getConfidenceConfig(confidence: number): {
  label: string;
  color: string;
  bgColor: string;
} {
  if (confidence >= 0.9) {
    return {
      label: 'Very High',
      color: 'text-success-700',
      bgColor: 'bg-success-100',
    };
  }
  if (confidence >= 0.7) {
    return {
      label: 'High',
      color: 'text-success-600',
      bgColor: 'bg-success-50',
    };
  }
  if (confidence >= 0.5) {
    return {
      label: 'Medium',
      color: 'text-warning-600',
      bgColor: 'bg-warning-50',
    };
  }
  return {
    label: 'Low',
    color: 'text-danger-600',
    bgColor: 'bg-danger-50',
  };
}
