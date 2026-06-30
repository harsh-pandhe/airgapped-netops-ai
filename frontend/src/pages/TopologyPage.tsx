// src/pages/TopologyPage.tsx — Track 11
import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { Plus, Trash2, Link as LinkIcon, Unlink } from "lucide-react";
import { api } from "../api/client";
import type { NetworkNode, TopologyData } from "../types";

interface GraphNode { id: string; name: string; x?: number; y?: number; fx?: number; fy?: number; }
interface GraphLink { source: string; target: string; }
interface GraphData { nodes: GraphNode[]; links: GraphLink[]; }

const LAYOUT_KEY = "sentinel_node_positions";

function nodeColor(node: GraphNode, telemetry: Record<string, NetworkNode>): string {
  const t = telemetry[node.id];
  if (!t) return "#64748b";
  return t.anomaly ? "#ef4444" : "#22c55e";
}

interface Props {
  telemetry: Record<string, NetworkNode>;
}

export default function TopologyPage({ telemetry }: Props) {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState<string | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<Set<string>>(new Set());
  const [showCRUD, setShowCRUD] = useState(false);
  const [crudForm, setCrudForm] = useState({ node_id: "", label: "", ip: "", src: "", tgt: "" });
  const [loadingTopo, setLoadingTopo] = useState(true);
  const [topoError, setTopoError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const positionsRef = useRef<Record<string, { x: number; y: number }>>({});

  useEffect(() => {
    try {
      const saved = localStorage.getItem(LAYOUT_KEY);
      if (saved) positionsRef.current = JSON.parse(saved);
    } catch {}
  }, []);

  const saveLayout = useCallback(() => {
    try { localStorage.setItem(LAYOUT_KEY, JSON.stringify(positionsRef.current)); } catch {}
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const loadTopology = useCallback(async () => {
    try {
      const data: TopologyData = await api.getTopology();
      const saved = positionsRef.current;
      setGraphData({
        nodes: data.nodes.map((n) => ({
          id: n.id,
          name: n.label ?? n.id,
          ...(saved[n.id] ? { fx: saved[n.id].x, fy: saved[n.id].y } : {}),
        })),
        links: data.edges.map((e) => ({ source: e.source, target: e.target })),
      });
      setLoadingTopo(false);
      setTopoError(null);
    } catch (err: any) {
      setTopoError(err.message || "Failed to load topology");
      setLoadingTopo(false);
    }
  }, []);

  useEffect(() => { loadTopology(); }, [loadTopology]);

  useEffect(() => {
    setSelectedAnomaly((prev) => (prev && telemetry[prev]?.anomaly) ? prev : null);
  }, [telemetry]);

  const sendFeedback = useCallback(async (nodeId: string, isCorrect: boolean) => {
    const t = telemetry[nodeId];
    if (!t) return;
    const key = `${nodeId}:${t.timestamp}`;
    if (feedbackSent.has(key)) return;
    await api.sendFeedback({ timestamp: t.timestamp, nodeId, isCorrect });
    setFeedbackSent((prev) => new Set(prev).add(key));
  }, [telemetry, feedbackSent]);

  const onNodeDragEnd = useCallback((node: GraphNode) => {
    if (node.x !== undefined && node.y !== undefined) {
      positionsRef.current[node.id] = { x: node.x, y: node.y };
      (node as any).fx = node.x;
      (node as any).fy = node.y;
      saveLayout();
    }
  }, [saveLayout]);

  const handleAddDevice = async () => {
    const { node_id, label, ip } = crudForm;
    if (!node_id || !label || !ip) return;
    await api.addDevice({ node_id, label, ip });
    await loadTopology();
  };

  const handleRemoveDevice = async () => {
    if (!crudForm.node_id) return;
    await api.removeDevice(crudForm.node_id);
    await loadTopology();
  };

  const handleAddConnection = async () => {
    const { src, tgt } = crudForm;
    if (!src || !tgt) return;
    await api.addConnection({ source: src, target: tgt });
    await loadTopology();
  };

  const handleRemoveConnection = async () => {
    const { src, tgt } = crudForm;
    if (!src || !tgt) return;
    await api.removeConnection({ source: src, target: tgt });
    await loadTopology();
  };

  const anomalyNodes = Object.values(telemetry).filter((n) => n.anomaly).map((n) => n.id);
  const activeAnomaly = selectedAnomaly ? telemetry[selectedAnomaly] : null;

  return (
    <div className="relative h-full w-full bg-slate-900 rounded-xl overflow-hidden border border-slate-700/50 flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700/60 bg-slate-900/80">
        <span className="text-xs font-mono text-slate-400 uppercase">SENTINEL</span>
        <div className="flex items-center gap-3">
          {anomalyNodes.length > 0 && (
            <span className="text-xs text-red-400 animate-pulse">{anomalyNodes.length} Anomalies</span>
          )}
          <button
            onClick={() => setShowCRUD((v) => !v)}
            className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded flex items-center gap-1"
          >
            <Plus size={12} /> Manage
          </button>
        </div>
      </div>

      {showCRUD && (
        <div className="bg-slate-800 border-b border-slate-700 p-4 grid grid-cols-2 gap-4 text-xs">
          <div className="space-y-2">
            <p className="text-slate-400 font-semibold uppercase">Node</p>
            <input placeholder="Node ID (e.g. RTR-003)" value={crudForm.node_id}
              onChange={(e) => setCrudForm((f) => ({ ...f, node_id: e.target.value }))}
              className="w-full bg-slate-900 border border-slate-600 rounded px-2 py-1 text-white" />
            <input placeholder="Label" value={crudForm.label}
              onChange={(e) => setCrudForm((f) => ({ ...f, label: e.target.value }))}
              className="w-full bg-slate-900 border border-slate-600 rounded px-2 py-1 text-white" />
            <input placeholder="IP Address" value={crudForm.ip}
              onChange={(e) => setCrudForm((f) => ({ ...f, ip: e.target.value }))}
              className="w-full bg-slate-900 border border-slate-600 rounded px-2 py-1 text-white" />
            <div className="flex gap-2">
              <button onClick={handleAddDevice} className="flex-1 bg-cyan-800 hover:bg-cyan-700 rounded py-1 flex items-center justify-center gap-1"><Plus size={12} /> Add</button>
              <button onClick={handleRemoveDevice} className="flex-1 bg-red-900 hover:bg-red-800 rounded py-1 flex items-center justify-center gap-1"><Trash2 size={12} /> Remove</button>
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-slate-400 font-semibold uppercase">Connection</p>
            <input placeholder="Source Node ID" value={crudForm.src}
              onChange={(e) => setCrudForm((f) => ({ ...f, src: e.target.value }))}
              className="w-full bg-slate-900 border border-slate-600 rounded px-2 py-1 text-white" />
            <input placeholder="Target Node ID" value={crudForm.tgt}
              onChange={(e) => setCrudForm((f) => ({ ...f, tgt: e.target.value }))}
              className="w-full bg-slate-900 border border-slate-600 rounded px-2 py-1 text-white" />
            <div className="flex gap-2">
              <button onClick={handleAddConnection} className="flex-1 bg-cyan-800 hover:bg-cyan-700 rounded py-1 flex items-center justify-center gap-1"><LinkIcon size={12} /> Link</button>
              <button onClick={handleRemoveConnection} className="flex-1 bg-red-900 hover:bg-red-800 rounded py-1 flex items-center justify-center gap-1"><Unlink size={12} /> Unlink</button>
            </div>
          </div>
        </div>
      )}

      <div ref={containerRef} className="flex-1 relative">
        {hoveredNode && (
          <div className="absolute top-3 left-3 z-30 bg-slate-800/90 border border-slate-600 rounded-lg p-3 text-xs pointer-events-none max-w-xs">
            <p className="font-bold text-white mb-1">{hoveredNode.id}</p>
            <p className="text-slate-400">{hoveredNode.name}</p>
            {telemetry[hoveredNode.id] && (
              <>
                <p className="text-slate-300 mt-1">
                  CPU: {telemetry[hoveredNode.id].cpu.toFixed(1)}% |
                  Latency: {telemetry[hoveredNode.id].latency.toFixed(0)}ms
                </p>
                <p className={`mt-1 font-semibold ${telemetry[hoveredNode.id].anomaly ? "text-red-400" : "text-green-400"}`}>
                  {telemetry[hoveredNode.id].anomaly ? "⚠ ANOMALY" : "✓ NORMAL"}
                </p>
                <p className="text-slate-300 mt-0.5">{telemetry[hoveredNode.id].explanation}</p>
              </>
            )}
          </div>
        )}

        {!loadingTopo && !topoError && (
          <ForceGraph2D
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            backgroundColor="transparent"
            nodeColor={(node: any) => nodeColor(node, telemetry)}
            linkColor={() => "#64748b"}
            linkWidth={1.5}
            onNodeDragEnd={onNodeDragEnd}
            onNodeHover={(node: any) => setHoveredNode(node ?? null)}
            nodeCanvasObjectMode={() => "after"}
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              const t = telemetry[node.id];
              if (t?.anomaly) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI);
                ctx.strokeStyle = "#ef444488";
                ctx.lineWidth = 2 / globalScale;
                ctx.stroke();
              }
              ctx.font = `${12 / globalScale}px monospace`;
              ctx.fillStyle = "#e2e8f0";
              ctx.textAlign = "center";
              ctx.fillText(node.name, node.x, node.y + 16 / globalScale);
            }}
            onNodeClick={(node: any) => {
              if (telemetry[node.id]?.anomaly) setSelectedAnomaly(node.id);
            }}
          />
        )}
        {topoError && <p className="text-red-400 p-4">{topoError}</p>}
      </div>

      {anomalyNodes.length > 0 && (
        <div className="absolute top-12 right-4 w-72 flex flex-col gap-2 z-20">
          <div className="flex flex-wrap gap-1 bg-slate-800/80 p-2 rounded-lg border border-slate-700/50">
            {anomalyNodes.map((nid) => (
              <button key={nid} onClick={() => setSelectedAnomaly(nid)}
                className={`px-2 py-0.5 rounded text-xs font-mono ${selectedAnomaly === nid ? "bg-red-600 text-white" : "bg-slate-700 text-slate-300"}`}>
                {nid}
              </button>
            ))}
          </div>

          {activeAnomaly && selectedAnomaly && (
            <div className="bg-slate-800/90 rounded-lg p-3 border-l-4 border-red-500">
              <p className="text-xs font-bold mb-1 text-red-400">⚠ ANOMALY</p>
              <p className="text-xs text-slate-200 mb-2">{activeAnomaly.explanation}</p>
              {!feedbackSent.has(`${selectedAnomaly}:${activeAnomaly.timestamp}`) ? (
                <div className="flex gap-2">
                  <button onClick={() => sendFeedback(selectedAnomaly, true)} className="flex-1 bg-green-800 text-xs py-1 rounded">Correct</button>
                  <button onClick={() => sendFeedback(selectedAnomaly, false)} className="flex-1 bg-red-900 text-xs py-1 rounded">Incorrect</button>
                </div>
              ) : (
                <p className="text-xs text-green-400">✓ Feedback sent</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}