// src/api/client.ts — Typed API client. Single source of truth for all backend calls.

import type {
  LiveStateValues, TelemetryResult, TopologyData, MetricsData,
  MetricHistoryPoint, AuthResponse, AuthUser, FeedbackPayload,
  DevicePayload, ConnectionPayload, ScenarioInfo, ScenarioInjectResult,
  NodeHistoryEntry,
} from "../types";

const API_BASE = "http://127.0.0.1:8000/api";
const TOKEN_KEY = "sentinel_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    throw new ApiError(401, "Session expired. Please log in again.");
  }
  if (!res.ok) {
    let detail = `API ${path} → ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // ── Auth ─────────────────────────────────────────────────────────────────
  login: async (username: string, password: string): Promise<AuthResponse> => {
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail || "Login failed");
    }
    return res.json();
  },

  me: () => request<AuthUser>("/auth/me"),

  // ── Telemetry ────────────────────────────────────────────────────────────
  getLiveState: () => request<Record<string, LiveStateValues>>("/live-state"),
  predictAll: () => request<Record<string, TelemetryResult>>("/predict-all"),

  // ── Node history (Track 8) ──────────────────────────────────────────────
  getNodeHistory: (nodeId: string, limit = 20) =>
    request<{ node_id: string; history: NodeHistoryEntry[] }>(
      `/node/${nodeId}/history?limit=${limit}`
    ),

  // ── Chat ─────────────────────────────────────────────────────────────────
  chat: (message: string) =>
    request<{ reply: string }>("/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  // ── Topology ─────────────────────────────────────────────────────────────
  getTopology: () => request<TopologyData>("/topology"),

  addDevice: (payload: DevicePayload) =>
    request<{ status: string }>("/topology/device", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  removeDevice: (nodeId: string) =>
    request<{ status: string }>(`/topology/device/${nodeId}`, { method: "DELETE" }),

  addConnection: (payload: ConnectionPayload) =>
    request<{ status: string }>("/topology/connection", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  removeConnection: (payload: ConnectionPayload) =>
    request<{ status: string }>("/topology/connection", {
      method: "DELETE",
      body: JSON.stringify(payload),
    }),

  // ── Feedback + Retrain ───────────────────────────────────────────────────
  sendFeedback: (payload: FeedbackPayload) =>
    request<{ status: string }>("/feedback", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  retrain: () => request<{ status: string }>("/retrain", { method: "POST" }),

  // ── Metrics (Track 10) ──────────────────────────────────────────────────
  getMetrics: () => request<MetricsData>("/metrics"),

  getMetricsHistory: (metric: "inference" | "retrieval", limit = 50) =>
    request<{ metric: string; data: MetricHistoryPoint[] }>(
      `/metrics/history?metric=${metric}&limit=${limit}`
    ),

  // ── XAI (Track 14) ──────────────────────────────────────────────────────
  getXaiHistory: (nodeId?: string, limit = 20) =>
    request<{ data: any[] }>(
      `/xai/history${nodeId ? `?node_id=${nodeId}&limit=${limit}` : `?limit=${limit}`}`
    ),

  // ── Demo (Track 16) ──────────────────────────────────────────────────────
  getScenarios: () => request<{ scenarios: ScenarioInfo[] }>("/demo/scenarios"),

  injectScenario: (scenario: string) =>
    request<ScenarioInjectResult>(`/demo/inject?scenario=${scenario}`, { method: "POST" }),

  resetDemo: () => request<{ status: string }>("/demo/reset", { method: "POST" }),

  // ── Audit (Track 5) ──────────────────────────────────────────────────────
  getAudit: (limit = 100, eventType?: string) =>
    request<{ entries: any[] }>(
      `/audit?limit=${limit}${eventType ? `&event_type=${eventType}` : ""}`
    ),
};

export { ApiError };