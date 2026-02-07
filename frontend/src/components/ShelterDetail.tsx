'use client';

import {
  X,
  Users,
  MapPin,
  Phone,
  Clock,
  Package,
  Zap,
  Stethoscope,
  Dog,
  Accessibility,
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import type { Shelter } from '@/types';
import clsx from 'clsx';

interface ShelterDetailProps {
  shelter: Shelter;
  onClose: () => void;
  onPlanDelivery?: (shelter: Shelter) => void;
}

export function ShelterDetail({
  shelter,
  onClose,
  onPlanDelivery,
}: ShelterDetailProps) {
  const occupancyPercent = Math.round(
    (shelter.current_occupancy / shelter.capacity) * 100
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400';
      case 'full':
        return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400';
      case 'closed':
        return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="absolute bottom-4 left-4 w-96 bg-white dark:bg-gray-800 rounded-lg shadow-xl z-20 overflow-hidden">
      {/* Header */}
      <div className="bg-primary-600 text-white px-4 py-3 flex items-start justify-between">
        <div>
          <h3 className="font-bold text-lg">{shelter.name}</h3>
          <span
            className={clsx(
              'inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium capitalize',
              getStatusColor(shelter.status)
            )}
          >
            {shelter.status}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-primary-500 rounded transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Location */}
        {shelter.address && (
          <div className="flex items-start gap-2">
            <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {shelter.address}
            </span>
          </div>
        )}

        {/* Contact */}
        {shelter.contact_phone && (
          <div className="flex items-center gap-2">
            <Phone className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {shelter.contact_name && `${shelter.contact_name}: `}
              {shelter.contact_phone}
            </span>
          </div>
        )}

        {/* Opened time */}
        {shelter.opened_at && (
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Opened:{' '}
              {(() => {
                try {
                  return format(parseISO(shelter.opened_at), 'MMM d, HH:mm');
                } catch {
                  return shelter.opened_at;
                }
              })()}
            </span>
          </div>
        )}

        {/* Occupancy */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Occupancy
            </span>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {shelter.current_occupancy} / {shelter.capacity} ({occupancyPercent}%)
            </span>
          </div>
          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={clsx(
                'h-full rounded-full transition-all',
                occupancyPercent >= 90
                  ? 'bg-danger-500'
                  : occupancyPercent >= 70
                  ? 'bg-warning-500'
                  : 'bg-success-500'
              )}
              style={{ width: `${Math.min(100, occupancyPercent)}%` }}
            />
          </div>
        </div>

        {/* Facilities */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Facilities
          </h4>
          <div className="flex flex-wrap gap-2">
            {shelter.has_generator && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                <Zap className="w-3 h-3 text-yellow-500" />
                Generator
              </span>
            )}
            {shelter.has_medical && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                <Stethoscope className="w-3 h-3 text-red-500" />
                Medical
              </span>
            )}
            {shelter.accepts_pets && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                <Dog className="w-3 h-3 text-brown-500" />
                Pets OK
              </span>
            )}
            {shelter.wheelchair_accessible && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                <Accessibility className="w-3 h-3 text-blue-500" />
                Accessible
              </span>
            )}
          </div>
        </div>

        {/* Needs */}
        {shelter.needs.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Supply Needs
            </h4>
            <div className="flex flex-wrap gap-2">
              {shelter.needs.map((need) => (
                <span
                  key={need}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-400 rounded text-xs"
                >
                  <Package className="w-3 h-3" />
                  {need}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => onPlanDelivery?.(shelter)}
            className="w-full py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg
                     font-medium text-sm transition-colors disabled:opacity-50"
            disabled={shelter.status === 'closed'}
          >
            Plan Delivery to This Shelter
          </button>
          {/* TODO: Implement delivery planning flow */}
        </div>
      </div>
    </div>
  );
}
