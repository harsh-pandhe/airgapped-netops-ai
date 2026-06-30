// src/components/StatusBadge.tsx
import { CheckCircle, AlertTriangle, Loader2 } from "lucide-react";
import type { NodeStatus } from "../types";

interface Props {
  status: NodeStatus;
  size?: number;
}

export default function StatusBadge({ status, size = 16 }: Props) {
  const colorClass =
    status === "healthy" ? "text-green-400" :
    status === "warning" ? "text-yellow-400" :
    status === "critical" ? "text-red-500 animate-pulse" :
    status === "failed" ? "text-red-600" :
    "text-gray-400";

  return (
    <span className={colorClass}>
      {status === "healthy" && <CheckCircle size={size} />}
      {(status === "critical" || status === "warning" || status === "failed") && (
        <AlertTriangle size={size} className={status === "critical" ? "animate-pulse" : ""} />
      )}
      {status === "loading" && <Loader2 size={size} className="animate-spin" />}
    </span>
  );
}