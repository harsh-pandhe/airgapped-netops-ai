// src/hooks/useMetrics.ts
import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { MetricsData } from "../types";

const POLL_MS = 5000;

export function useMetrics() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      const data = await api.getMetrics();
      setMetrics(data);
      setError(null);
    } catch {
      setError("Unable to load metrics");
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    const id = setInterval(fetchMetrics, POLL_MS);
    return () => clearInterval(id);
  }, [fetchMetrics]);

  return { metrics, error, refetch: fetchMetrics };
}