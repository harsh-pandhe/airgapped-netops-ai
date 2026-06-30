// src/hooks/useWebSocket.ts — Track 13: WS telemetry stream with reconnect
import { useState, useEffect, useRef, useCallback } from "react";
import type { NetworkNode, TelemetryResult, LiveStateValues } from "../types";

const WS_URL = "ws://127.0.0.1:8000/ws/telemetry";
const MAX_BACKOFF_MS = 30000;
const SPARKLINE_LEN = 30;

type WsPayload = Record<string, LiveStateValues & TelemetryResult>;

export function useTelemetryStream() {
  const [nodes, setNodes] = useState<Record<string, NetworkNode>>({});
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(500);
  const historyRef = useRef<Record<string, number[]>>({});
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
        backoffRef.current = 500; // reset backoff on success
      };

      ws.onmessage = (event) => {
        try {
          const payload: WsPayload = JSON.parse(event.data);
          const updated: Record<string, NetworkNode> = {};

          for (const [nodeId, data] of Object.entries(payload)) {
            const cpu = data.cpu;
            const hist = historyRef.current[nodeId] || [];
            const newHist = [...hist, cpu].slice(-SPARKLINE_LEN);
            historyRef.current[nodeId] = newHist;

            updated[nodeId] = {
              id: nodeId,
              label: nodeId,
              ip: "",
              cpu: data.cpu,
              memory: data.memory,
              temperature: data.temperature,
              latency: data.latency,
              packet_loss: data.packet_loss,
              status: data.anomaly ? "critical" : "healthy",
              anomaly: data.anomaly,
              anomaly_score: data.anomaly_score,
              explanation: data.explanation,
              feature_impacts: data.feature_impacts,
              timestamp: data.timestamp,
              cpu_history: newHist,
            };
          }
          setNodes(updated);
        } catch {
          // ignore malformed frame
        }
      };

      ws.onerror = () => {
        setError("WebSocket connection error");
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        if (!mountedRef.current) return;
        // exponential backoff reconnect
        timeoutRef.current = setTimeout(() => {
          backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
          connect();
        }, backoffRef.current);
      };
    } catch {
      setError("Failed to create WebSocket");
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { nodes, connected, error };
}