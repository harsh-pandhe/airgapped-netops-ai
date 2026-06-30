// src/hooks/useNodeHistory.ts — Track 8
import { useState, useCallback } from "react";
import { api } from "../api/client";
import type { NodeHistoryEntry } from "../types";

export function useNodeHistory() {
  const [history, setHistory] = useState<NodeHistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchHistory = useCallback(async (nodeId: string, limit = 20) => {
    setLoading(true);
    try {
      const res = await api.getNodeHistory(nodeId, limit);
      setHistory(res.history);
    } catch {
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { history, loading, fetchHistory };
}