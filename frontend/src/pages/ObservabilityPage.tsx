// src/pages/ObservabilityPage.tsx — Track 10
import { useState, useEffect } from "react";
import { Activity, Database, Zap, Cpu, HardDrive, RefreshCw, Clock, Target, ShieldAlert } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { api } from "../api/client";
import { useMetrics } from "../hooks/useMetrics";
import type { MetricHistoryPoint } from "../types";

function fmtTime(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString();
}

export default function ObservabilityPage() {
  const { metrics, error } = useMetrics();
  const [inferenceHistory, setInferenceHistory] = useState<MetricHistoryPoint[]>([]);
  const [retrievalHistory, setRetrievalHistory] = useState<MetricHistoryPoint[]>([]);
  const [retraining, setRetraining] = useState(false);
  const [retrainMsg, setRetrainMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const [inf, ret] = await Promise.all([
          api.getMetricsHistory("inference", 50),
          api.getMetricsHistory("retrieval", 50),
        ]);
        setInferenceHistory(inf.data);
        setRetrievalHistory(ret.data);
      } catch {}
    };
    fetchHistory();
    const id = setInterval(fetchHistory, 10000);
    return () => clearInterval(id);
  }, []);

  const triggerRetrain = async () => {
    setRetraining(true);
    setRetrainMsg(null);
    try {
      const res = await api.retrain();
      setRetrainMsg(`${new Date().toLocaleTimeString()} — ${res.status}`);
    } catch {
      setRetrainMsg("Retrain failed");
    } finally {
      setRetraining(false);
    }
  };

  if (error) {
    return <div className="text-red-400 p-8 text-sm">{error}</div>;
  }
  if (!metrics) {
    return <div className="text-gray-400 p-8">Loading system telemetry...</div>;
  }

  const mergedLatency = inferenceHistory.map((inf, i) => ({
    time: fmtTime(inf.ts),
    inference_ms: inf.value_ms,
    retrieval_ms: retrievalHistory[i]?.value_ms ?? null,
  }));

  return (
    <div className="p-6 space-y-6">
      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card icon={<Zap className="text-cyan-400" size={26} />} label="Avg Inference" value={`${metrics.avg_inference_ms} ms`} />
        <Card icon={<Database className="text-emerald-400" size={26} />} label="Avg Retrieval" value={`${metrics.avg_retrieval_ms} ms`} />
        <Card icon={<Activity className="text-purple-400" size={26} />} label="Total Tokens" value={metrics.total_tokens.toLocaleString()} />
        <Card icon={<Clock className="text-orange-400" size={26} />} label="Last Retrain" value={metrics.last_retrain ? new Date(metrics.last_retrain).toLocaleString() : "Never"} small />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card icon={<Target className="text-blue-400" size={26} />} label="Anomaly Rate" value={`${metrics.anomaly_rate_pct}%`} />
        <Card icon={<ShieldAlert className="text-amber-400" size={26} />} label="False Positive Rate" value={`${metrics.false_positive_rate_pct}%`} />
        <Card icon={<Activity className="text-green-400" size={26} />} label="Mitigation Success" value={`${metrics.mitigation_success_rate}%`} />
        <Card icon={<Database className="text-pink-400" size={26} />} label="Avg Reranker Score" value={metrics.avg_reranker_score.toFixed(3)} />
      </div>

      {metrics.shap_fallback_count > 0 && (
        <div className="bg-amber-950/30 border border-amber-800 rounded-lg p-3 text-xs text-amber-300">
          ⚠ SHAP fallback triggered {metrics.shap_fallback_count} time(s) — score-based explanations used instead of TreeExplainer.
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={triggerRetrain}
          disabled={retraining}
          className="flex items-center gap-2 bg-cyan-800 hover:bg-cyan-700 disabled:opacity-50 text-sm px-4 py-2 rounded-lg transition-colors"
        >
          <RefreshCw size={14} className={retraining ? "animate-spin" : ""} />
          {retraining ? "Retraining..." : "Trigger Retrain"}
        </button>
        <span className="text-xs text-gray-500">Auto-retrain runs every 24h</span>
        {retrainMsg && <span className="text-xs text-cyan-400">{retrainMsg}</span>}
      </div>

      {/* Latency time-series */}
      <ChartCard title="Inference vs Retrieval Latency (ms, last 50 calls)">
        <LineChart data={mergedLatency}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="time" hide />
          <YAxis stroke="#9ca3af" />
          <Tooltip contentStyle={{ backgroundColor: "#111827" }} />
          <Line type="monotone" dataKey="inference_ms" name="Inference" stroke="#a78bfa" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="retrieval_ms" name="Retrieval" stroke="#fb923c" strokeWidth={2} dot={false} connectNulls />
        </LineChart>
      </ChartCard>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ChartCard title={<><Cpu size={14} /> CPU Utilization (%)</>}>
          <LineChart data={[]}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis hide />
            <YAxis stroke="#9ca3af" domain={[0, 100]} />
          </LineChart>
        </ChartCard>
        <ChartCard title={<><HardDrive size={14} /> Hardware Snapshot</>}>
          <div className="flex flex-col gap-2 text-xs text-gray-300 justify-center h-full px-2">
            <Stat label="CPU" value={`${metrics.hardware.cpu_percent}%`} />
            <Stat label="RAM" value={`${metrics.hardware.ram_percent}%`} />
            <Stat label="GPU" value={`${metrics.hardware.gpu_percent}%`} />
            <Stat label="VRAM" value={`${metrics.hardware.gpu_mem_percent}%`} />
            <Stat label="Disk" value={`${metrics.hardware.disk_used_gb.toFixed(1)} / ${metrics.hardware.disk_total_gb.toFixed(0)} GB`} />
          </div>
        </ChartCard>
      </div>
    </div>
  );
}

function Card({ icon, label, value, small }: { icon: React.ReactNode; label: string; value: string; small?: boolean }) {
  return (
    <div className="bg-gray-900 p-4 rounded-xl border border-gray-700 flex items-center gap-3">
      {icon}
      <div className="min-w-0">
        <p className="text-gray-400 text-[11px]">{label}</p>
        <p className={`font-bold truncate ${small ? "text-xs" : "text-lg"}`}>{value}</p>
      </div>
    </div>
  );
}

function ChartCard({ title, children }: { title: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 p-5 rounded-xl border border-gray-700 h-56">
      <h3 className="text-gray-400 text-xs mb-3 flex items-center gap-2">{title}</h3>
      <ResponsiveContainer width="100%" height="85%">
        {children as React.ReactElement}
      </ResponsiveContainer>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-gray-800 pb-1">
      <span className="text-gray-500">{label}</span>
      <span className="text-white font-semibold">{value}</span>
    </div>
  );
}