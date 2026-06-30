// src/components/SHAPChart.tsx — Track 14
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip } from "recharts";
import type { FeatureImpact } from "../types";

interface Props {
  impacts: FeatureImpact[] | null;
  anomaly: boolean;
  compact?: boolean;
}

export default function SHAPChart({ impacts, anomaly, compact = false }: Props) {
  if (!anomaly) {
    return (
      <div className="text-xs text-green-400 italic py-2">Node operating normally</div>
    );
  }

  if (!impacts || impacts.length === 0) {
    return (
      <div className="text-xs text-gray-500 italic py-2">
        SHAP explanation unavailable for this prediction (score-based fallback used)
      </div>
    );
  }

  const data = (compact ? impacts.slice(0, 3) : impacts).map((i) => ({
    name: i.feature,
    impact: i.impact,
    value: i.value,
    unit: i.unit,
    label: `${i.value}${i.unit}`,
  }));

  return (
    <div>
      <h4 className={`text-xs font-semibold mb-2 ${anomaly ? "text-red-400" : "text-gray-400"}`}>
        Why was this flagged?
      </h4>
      <div style={{ height: compact ? 90 : 160 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 10, right: 30, top: 0, bottom: 0 }}>
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="name"
              width={compact ? 70 : 90}
              tick={{ fill: "#94a3b8", fontSize: compact ? 10 : 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", fontSize: 11 }}
              formatter={(value: any, _name: any, props: any) => [
                `${Number(value).toFixed(4)} (${props.payload.label})`,
                "impact",
              ]}
            />
            <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
              {data.map((entry, idx) => (
                <Cell key={idx} fill={entry.impact > 0 ? "#ef4444" : "#22c55e"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}