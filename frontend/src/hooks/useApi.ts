'use client';

import { useState, useEffect, useCallback } from 'react';

/**
 * Generic hook for API data fetching with loading and error states
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList = []
) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, isLoading, error, refetch };
}

/**
 * Hook for polling data at regular intervals
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number = 5000,
  enabled: boolean = true
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!enabled) return;

    let isActive = true;

    const poll = async () => {
      try {
        const result = await fetcher();
        if (isActive) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (isActive) {
          setError(err instanceof Error ? err : new Error(String(err)));
        }
      }
    };

    // Initial fetch
    poll();

    // Set up interval
    const interval = setInterval(poll, intervalMs);

    return () => {
      isActive = false;
      clearInterval(interval);
    };
  }, [fetcher, intervalMs, enabled]);

  return { data, error };
}

/**
 * Hook for debouncing a value
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}
