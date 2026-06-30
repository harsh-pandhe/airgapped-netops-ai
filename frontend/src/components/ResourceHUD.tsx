// src/components/ResourceHUD.tsx — Track 16
import { useState, useEffect } from "react";
import { Cpu, MonitorSmartphone, ChevronRight } from "lucide-react";
import { api } from "../api/client";
import type { HardwareMetrics } from "../types";

const COLLAPSE_KEY = "sentinel_hud_collapsed";
const POLL_MS = 5000;

function barColor(pct: number): string {
  if (pct >= 80) return "bg-red-500";
  if (pct >= 60) return "bg-yellow-500";
  return "bg-green-500";
}

function Bar({ label, pct }: { label: string; pct: number }) {
  return (
    <div className="flex items-center gap-2 text-[10px]">
      <span className="w-9 text-gray-400">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-800 rounded overflow-hidden">
        <div className={`h-full ${barColor(pct)}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="w-9 text-right text-gray-300">{pct.toFixed(0)}%</span>
    </div>
  );
}

export default function ResourceHUD() {
  const [hw, setHw] = useState<HardwareMetrics | null>(null);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(COLLAPSE_KEY) === "true"
  );

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await api.getMetrics();
        setHw(data.hardware);
      } catch {}
    };
    fetch();
    const id = setInterval(fetch, POLL_MS);
    return () => clearInterval(id);
  }, []);

  const toggle = () => {
    setCollapsed((c) => {
      localStorage.setItem(COLLAPSE_KEY, String(!c));
      return !c;
    });
  };

  if (!hw) return null;

  if (collapsed) {
    return (
      <button
        onClick={toggle}
        className="fixed bottom-4 left-4 z-30 bg-gray-900/90 border border-gray-700 rounded-full p-2.5 hover:border-cyan-600 transition-colors"
        title="Show system resources"
      >
        <MonitorSmartphone size={16} className="text-cyan-400" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 left-4 z-30 bg-gray-900/90 border border-gray-700 rounded-lg p-3 w-44 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-semibold text-gray-300 flex items-center gap-1">
          <Cpu size={11} /> System
        </span>
        <button onClick={toggle} className="text-gray-500 hover:text-gray-300">
          <ChevronRight size={12} />
        </button>
      </div>
      <div className="space-y-1.5">
        <Bar label="CPU" pct={hw.cpu_percent} />
        <Bar label="RAM" pct={hw.ram_percent} />
        {hw.gpu_percent > 0 && <Bar label="GPU" pct={hw.gpu_percent} />}
        {hw.gpu_mem_percent > 0 && <Bar label="VRAM" pct={hw.gpu_mem_percent} />}
        <Bar label="Disk" pct={hw.disk_percent} />
      </div>
      {hw.disk_total_gb > 0 && (
        <p className="text-[9px] text-gray-500 mt-1.5 text-right">
          {hw.disk_used_gb.toFixed(1)}GB / {hw.disk_total_gb.toFixed(0)}GB
        </p>
      )}
    </div>
  );
}