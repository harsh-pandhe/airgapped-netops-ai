import { useState, useEffect } from "react";
import { Activity, Terminal } from "lucide-react";
import { getToken } from "./api/client";
import { useTelemetryStream } from "./hooks/useWebSocket";
import LoginPage from "./components/LoginPage";
import NodeCard from "./components/NodeCard";
import TabBar, { type Tab } from "./components/TabBar";
import AlertFeed from "./components/AlertFeed";
import NodeDetailDrawer from "./components/NodeDetailDrawer";
import ResourceHUD from "./components/ResourceHUD";
import DemoBar from "./components/DemoBar";
import ChatPage from "./pages/ChatPage";
import TopologyPage from "./pages/TopologyPage";
import ObservabilityPage from "./pages/ObservabilityPage";
import type { AuthUser, NetworkNode } from "./types";

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("chat");
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [prefillPrompt, setPrefillPrompt] = useState<string | null>(null);

  const { nodes, connected, error } = useTelemetryStream();

  useEffect(() => { if (getToken() && !user) setUser({ username: "session", role: "", domains: [] }); }, []);

  if (!user) return <LoginPage onLogin={setUser} />;

  const anomalyCount = Object.values(nodes).filter((n) => n.anomaly).length;

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 font-sans overflow-hidden">
      <DemoBar />
      <aside className="w-80 bg-gray-900 border-r border-gray-800 flex flex-col shadow-2xl z-10">
        <div className="p-6 border-b border-gray-800 flex items-center gap-3">
          <Activity className="text-cyan-400" size={24} />
          <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">NetOps AI</h1>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Live Nodes</h2>
          {!connected && <p className="text-xs text-amber-400">⚠ Reconnecting to telemetry stream...</p>}
          {Object.values(nodes).map((n) => <NodeCard key={n.id} node={n} onClick={setSelectedNode} />)}
        </div>
      </aside>

      <main className="flex-1 flex flex-col relative overflow-hidden">
        <header className="h-16 border-b border-gray-800 flex items-center px-6 bg-gray-900/50 backdrop-blur-md sticky top-0 z-10">
          <Terminal size={20} className="text-gray-400 mr-3" />
          <h2 className="text-lg font-medium text-gray-200">Air-Gapped Copilot</h2>
          {error && <span className="ml-4 text-xs text-red-400">{error}</span>}
        </header>

        <TabBar active={activeTab} onChange={setActiveTab} alertCount={anomalyCount} />

        <div className="flex-1 overflow-hidden flex flex-col">
          {activeTab === "chat" && <ChatPage prefillPrompt={prefillPrompt} onPrefillConsumed={() => setPrefillPrompt(null)} />}
          {activeTab === "topology" && <div className="flex-1 p-6 bg-slate-950"><TopologyPage telemetry={nodes} /></div>}
          {activeTab === "observability" && <div className="flex-1 overflow-y-auto bg-slate-950"><ObservabilityPage /></div>}
        </div>
      </main>

      <NodeDetailDrawer
        node={selectedNode}
        onClose={() => setSelectedNode(null)}
        onAskCopilot={(prompt) => { setActiveTab("chat"); setPrefillPrompt(prompt); setSelectedNode(null); }}
      />
      <AlertFeed nodes={nodes} />
      <ResourceHUD />
    </div>
  );
}