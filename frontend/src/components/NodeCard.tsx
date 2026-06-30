// src/components/NodeCard.tsx — Track 7 + 13
import { Server } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import StatusBadge from "./StatusBadge";
import type { NetworkNode } from "../types";

interface Props {
  node: NetworkNode;
  onClick?: (node: NetworkNode) => void;
}

function sparklineColor(cpu: number): string {
  if (cpu >= 85) return "#ef4444";
  if (cpu >= 70) return "#eab308";
  return "#22c55e";
}

export default function NodeCard({ node, onClick }: Props) {
  const sparkData = node.cpu_history.map((v, i) => ({ i, cpu: v }));
  const color = sparklineColor(node.cpu);

  return (
    <div
      className="bg-gray-800/50 rounded-xl p-4 border border-gray-700 hover:border-cyan-700 transition-colors cursor-pointer"
      onClick={() => onClick?.(node)}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <Server size={16} className="text-gray-400" />
          <span className="font-semibold text-sm">{node.id}</span>
        </div>
        <StatusBadge status={node.status} />
      </div>

      <div className="text-xs text-gray-400 mb-3">{node.label}</div>

      {sparkData.length > 1 && (
        <div className="h-10 mb-3 -mx-1">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={`spark-${node.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={node.anomaly ? 0.5 : 0.2} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="cpu"
                stroke={color}
                strokeWidth={1.5}
                fill={`url(#spark-${node.id})`}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-gray-900 rounded p-2">
          <span className="text-gray-500 block mb-1">CPU</span>
          <span className={`font-medium ${node.cpu > 80 ? "text-red-400" : "text-green-400"}`}>
            {node.cpu.toFixed(1)}%
          </span>
        </div>
        <div className="bg-gray-900 rounded p-2">
          <span className="text-gray-500 block mb-1">Latency</span>
          <span className={`font-medium ${node.latency > 100 ? "text-red-400" : "text-green-400"}`}>
            {node.latency.toFixed(0)}ms
          </span>
        </div>
      </div>
    </div>
  );
}