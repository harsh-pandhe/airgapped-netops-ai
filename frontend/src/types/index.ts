// src/types/index.ts — Shared TypeScript interfaces

export type NodeStatus = "healthy" | "warning" | "critical" | "failed" | "loading";

export interface FeatureImpact {
  feature: string;
  impact: number;
  value: number;
  unit: string;
}

export interface LiveStateValues {
  cpu: number;
  memory: number;
  temperature: number;
  latency: number;
  packet_loss: number;
}

export interface TelemetryResult {
  timestamp: string;
  anomaly: boolean;
  anomaly_score: number;
  explanation: string;
  feature_impacts: FeatureImpact[] | null;
}

export interface NetworkNode {
  id: string;
  label: string;
  ip: string;
  cpu: number;
  memory: number;
  temperature: number;
  latency: number;
  packet_loss: number;
  status: NodeStatus;
  anomaly: boolean;
  anomaly_score: number;
  explanation: string;
  feature_impacts: FeatureImpact[] | null;
  timestamp: string;
  cpu_history: number[];
}

export interface TopologyNode {
  id: string;
  label?: string;
  ip?: string;
}

export interface TopologyEdge {
  source: string;
  target: string;
}

export interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export interface HardwareMetrics {
  cpu_percent: number;
  ram_percent: number;
  gpu_percent: number;
  gpu_mem_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  disk_percent: number;
}

export interface MetricsData {
  avg_inference_ms: number;
  avg_retrieval_ms: number;
  total_tokens: number;
  mitigation_success_rate: number;
  avg_reranker_score: number;
  anomaly_rate_pct: number;
  false_positive_rate_pct: number;
  shap_fallback_count: number;
  last_retrain: string | null;
  hardware: HardwareMetrics;
}

export interface MetricHistoryPoint {
  ts: number;
  value_ms: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: string;
  domains: string[];
}

export interface AuthUser {
  username: string;
  role: string;
  domains: string[];
}

export interface FeedbackPayload {
  timestamp: string;
  nodeId: string;
  isCorrect: boolean;
}

export interface DevicePayload {
  node_id: string;
  label: string;
  ip: string;
}

export interface ConnectionPayload {
  source: string;
  target: string;
}

export interface ScenarioInfo {
  name: string;
  description: string;
  duration_seconds: number;
  nodes_affected: string[];
}

export interface ScenarioInjectResult {
  scenario: string;
  description: string;
  duration_seconds: number;
  duration_ticks: number;
  nodes_affected: string[];
}

export interface NodeHistoryEntry {
  timestamp?: string;
  cpu_usage?: number;
  memory_usage?: number;
  temperature?: number;
  latency?: number;
  packet_loss?: number;
}