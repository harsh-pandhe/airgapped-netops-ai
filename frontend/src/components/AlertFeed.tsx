// src/components/AlertFeed.tsx — Track 8
import { AlertTriangle, X, ThumbsDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { NetworkNode } from "../types";

interface Alert {
  id: string;
  nodeId: string;
  message: string;
  topDriver: string;
  timestamp: string;
  ts: number;
}

interface Props {
  nodes: Record<string, NetworkNode>;
}

export default function AlertFeed({ nodes }: Props) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [dismissing, setDismissing] = useState<Set<string>>(new Set());
  const seenRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const newAlerts: Alert[] = [];
    for (const node of Object.values(nodes)) {
      if (!node.anomaly) continue;
      const key = `${node.id}:${node.timestamp}`;
      if (seenRef.current.has(key)) continue;
      seenRef.current.add(key);

      const topDriver = node.feature_impacts?.[0]
        ? `${node.feature_impacts[0].feature} (${node.feature_impacts[0].value}${node.feature_impacts[0].unit})`
        : "unknown driver";

      newAlerts.push({
        id: key,
        nodeId: node.id,
        message: node.explanation || "Anomaly detected",
        topDriver,
        timestamp: node.timestamp,
        ts: Date.now(),
      });
    }
    if (newAlerts.length > 0) {
      setAlerts((prev) => [...newAlerts, ...prev].slice(0, 20));
    }
  }, [nodes]);

  const dismiss = (id: string) =>
    setAlerts((prev) => prev.filter((a) => a.id !== id));

  const markFalsePositive = async (alert: Alert) => {
    setDismissing((prev) => new Set(prev).add(alert.id));
    try {
      await api.sendFeedback({
        timestamp: alert.timestamp,
        nodeId: alert.nodeId,
        isCorrect: false,
      });
      dismiss(alert.id);
    } catch {
      setDismissing((prev) => {
        const next = new Set(prev);
        next.delete(alert.id);
        return next;
      });
    }
  };

  if (alerts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-40 flex flex-col gap-2 w-80 max-h-[60vh] overflow-y-auto">
      {alerts.slice(0, 6).map((alert) => (
        <div
          key={alert.id}
          className="bg-red-950 border border-red-700 rounded-lg p-3 shadow-xl flex items-start gap-2"
        >
          <AlertTriangle size={16} className="text-red-400 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-red-300">{alert.nodeId}</p>
            <p className="text-xs text-gray-300">{alert.message}</p>
            <p className="text-[10px] text-gray-500 mt-0.5">Driver: {alert.topDriver}</p>
            <button
              onClick={() => markFalsePositive(alert)}
              disabled={dismissing.has(alert.id)}
              className="mt-2 flex items-center gap-1 text-[10px] bg-red-900/50 hover:bg-red-900 disabled:opacity-50 px-2 py-1 rounded text-red-200"
            >
              <ThumbsDown size={10} /> Mark as False Positive
            </button>
          </div>
          <button onClick={() => dismiss(alert.id)} className="text-gray-500 hover:text-gray-300 shrink-0">
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}