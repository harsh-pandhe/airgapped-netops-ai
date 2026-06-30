// src/components/TabBar.tsx
export type Tab = "chat" | "topology" | "observability";

interface Props {
  active: Tab;
  onChange: (tab: Tab) => void;
  alertCount?: number;
}

const LABELS: Record<Tab, string> = {
  chat: "Terminal Chat",
  topology: "Live Topology Map",
  observability: "Observability",
};

export default function TabBar({ active, onChange, alertCount = 0 }: Props) {
  return (
    <div className="flex gap-2 p-1 bg-slate-800 rounded-lg w-fit border border-slate-700 mx-6 mt-4">
      {(Object.keys(LABELS) as Tab[]).map((tab) => (
        <button
          key={tab}
          onClick={() => onChange(tab)}
          className={`relative px-4 py-2 rounded-md text-sm font-semibold transition-colors
            ${active === tab ? "bg-cyan-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
        >
          {LABELS[tab]}
          {tab === "topology" && alertCount > 0 && (
            <span className="absolute -top-1.5 -right-1.5 bg-red-600 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
              {alertCount > 9 ? "9+" : alertCount}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}