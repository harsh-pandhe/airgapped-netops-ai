// src/components/NodeDetailDrawer.tsx — Track 8
import { useEffect, useState } from "react";
import { X, AlertTriangle, CheckCircle, MessageSquare } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from "recharts";
import { api } from "../api/client";
import SHAPChart from "./SHAPChart";
import type { NetworkNode, TopologyData } from "../types";

interface Props {
  node: NetworkNode | null;
  onClose: () => void;
  onAskCopilot: (prompt: string) => void;
}

export default function NodeDetailDrawer({ node, onClose, onAskCopilot }: Props) {
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [neighbors, setNeighbors] = useState<string[]>([]);

  useEffect(() => {
    setFeedbackSent(false);
    if (!node) return;
    api.getTopology().then((data: TopologyData) => {
      const ns = data.edges
        .filter((e) => e.source === node.id || e.target === node.id)
        .map((e) => (e.source === node.id ? e.target : e.source));
      setNeighbors(ns);
    }).catch(() => setNeighbors([]));
  }, [node?.id]);

  if (!node) return null;

  const sendFeedback = async (isCorrect: boolean) => {
    if (feedbackSent || feedbackLoading) return;
    setFeedbackLoading(true);
    try {
      await api.sendFeedback({ timestamp: node.timestamp, nodeId: node.id, isCorrect });
      setFeedbackSent(true);
    } finally {
      setFeedbackLoading(false);
    }
  };

  const metricsData = [
    { name: "CPU", value: node.cpu, warn: node.cpu > 80 },
    { name: "Memory", value: node.memory, warn: node.memory > 85 },
    { name: "Temp", value: node.temperature, warn: node.temperature > 75 },
    { name: "Latency", value: node.latency, warn: node.latency > 100 },
    { name: "Loss", value: node.packet_loss, warn: node.packet_loss > 2 },
  ];

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-gray-900 border-l border-gray-700 shadow-2xl z-50 flex flex-col overflow-y-auto">
      <div className="flex items-center justify-between p-5 border-b border-gray-800">
        <div>
          <h2 className="font-bold text-lg">{node.id}</h2>
          <span className="text-xs text-gray-400">{node.label}</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onAskCopilot(`What is wrong with ${node.id}?`)}
            className="text-xs bg-cyan-800 hover:bg-cyan-700 px-3 py-1.5 rounded flex items-center gap-1"
          >
            <MessageSquare size={12} /> Ask Copilot
          </button>
          <button onClick={onClose} className="text-gray-500 hover:text-white">
            <X size={20} />
          </button>
        </div>
      </div>

      <div className={`mx-5 mt-4 p-3 rounded-lg flex items-center gap-2 text-sm font-semibold
        ${node.anomaly ? "bg-red-900/40 border border-red-700 text-red-300" : "bg-green-900/40 border border-green-700 text-green-300"}`}>
        {node.anomaly ? <AlertTriangle size={16} /> : <CheckCircle size={16} />}
        {node.anomaly ? "CRITICAL ANOMALY" : "NORMAL"}
        <span className="ml-auto text-xs font-normal opacity-70">
          score: {node.anomaly_score?.toFixed(3) ?? "—"}
        </span>
      </div>

      {/* Live metrics bar chart */}
      <div className="px-5 pt-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Live Metrics</h3>
        <div style={{ height: 120 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={metricsData}>
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", fontSize: 11 }} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {metricsData.map((d, i) => (
                  <Cell key={i} fill={d.warn ? "#ef4444" : "#22c55e"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SHAP */}
      <div className="px-5 pt-4">
        <SHAPChart impacts={node.feature_impacts} anomaly={node.anomaly} />
      </div>

      {/* Topology neighbors */}
      <div className="px-5 pt-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Topology Neighbors</h3>
        {neighbors.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {neighbors.map((n) => (
              <span key={n} className="text-xs bg-gray-800 border border-gray-700 px-2 py-1 rounded font-mono">
                {n}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-500">No connected nodes</p>
        )}
      </div>

      {/* Feedback */}
      {node.anomaly && (
        <div className="px-5 py-5 mt-auto">
          <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Model Feedback</h3>
          {feedbackSent ? (
            <p className="text-xs text-green-400">✓ Feedback recorded</p>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={() => sendFeedback(true)}
                disabled={feedbackLoading}
                className="flex-1 bg-green-800 hover:bg-green-700 text-xs py-2 rounded disabled:opacity-50"
              >
                Correct ✓
              </button>
              <button
                onClick={() => sendFeedback(false)}
                disabled={feedbackLoading}
                className="flex-1 bg-red-900 hover:bg-red-800 text-xs py-2 rounded disabled:opacity-50"
              >
                Incorrect ✗
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}