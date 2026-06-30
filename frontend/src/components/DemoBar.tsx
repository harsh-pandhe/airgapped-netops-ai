// src/components/DemoBar.tsx — Track 16
import { useState, useEffect, useCallback } from "react";
import { Film, RotateCcw } from "lucide-react";
import { api } from "../api/client";
import type { ScenarioInfo } from "../types";

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

const SCENARIO_LABELS: Record<string, string> = {
  ddos: "DDoS Attack",
  link_flap: "Link Flap",
  thermal_throttle: "Thermal",
  cascade: "Cascade",
};

export default function DemoBar() {
  const [visible, setVisible] = useState(false);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [active, setActive] = useState<{ name: string; remaining: number } | null>(null);

  useEffect(() => {
    if (!DEMO_MODE) return;
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key.toUpperCase() === "D") {
        setVisible((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (!DEMO_MODE || !visible) return;
    api.getScenarios().then((res) => setScenarios(res.scenarios)).catch(() => {});
  }, [visible]);

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => {
      setActive((prev) => {
        if (!prev) return null;
        const next = prev.remaining - 1;
        return next <= 0 ? null : { ...prev, remaining: next };
      });
    }, 1000);
    return () => clearInterval(id);
  }, [active?.name]);

  const inject = useCallback(async (scenario: string) => {
    try {
      const result = await api.injectScenario(scenario);
      setActive({ name: scenario, remaining: result.duration_seconds });
    } catch {}
  }, []);

  const reset = useCallback(async () => {
    try {
      await api.resetDemo();
      setActive(null);
    } catch {}
  }, []);

  if (!DEMO_MODE || !visible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-gray-900 border-b border-amber-700/50 px-4 py-2 flex items-center gap-3 shadow-lg">
      <span className="flex items-center gap-1.5 text-xs font-bold text-amber-400">
        <Film size={14} /> DEMO MODE
      </span>

      {scenarios.map((s) => (
        <button
          key={s.name}
          onClick={() => inject(s.name)}
          disabled={active?.name === s.name}
          className="text-xs bg-gray-800 hover:bg-gray-700 disabled:opacity-50 border border-gray-700 px-3 py-1.5 rounded-md text-gray-200 transition-colors"
          title={s.description}
        >
          {SCENARIO_LABELS[s.name] ?? s.name}
        </button>
      ))}

      <button
        onClick={reset}
        className="text-xs bg-red-900/60 hover:bg-red-900 border border-red-800 px-3 py-1.5 rounded-md text-red-200 flex items-center gap-1 transition-colors"
      >
        <RotateCcw size={12} /> Reset
      </button>

      {active && (
        <span className="ml-auto text-xs text-amber-300 font-mono">
          {SCENARIO_LABELS[active.name] ?? active.name} — {active.remaining}s remaining
        </span>
      )}
    </div>
  );
}