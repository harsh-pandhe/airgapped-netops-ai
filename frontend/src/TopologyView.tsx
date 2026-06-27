import { useCallback, useEffect, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

// ─── Types ───────────────────────────────────────────────────────────────────
interface Node { id: string; name: string; x?: number; y?: number; }
interface Link { source: string; target: string; }
interface GraphData { nodes: Node[]; links: Link[]; }
interface NodeTelemetry {
  anomaly: boolean;
  explanation: string;
  timestamp: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  metric?: string;
}
type TelemetryMap = Record<string, NodeTelemetry>;

// ─── Constants ───────────────────────────────────────────────────────────────
const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#facc15',
};
const API_BASE = 'http://127.0.0.1:8000/api';
const POLL_INTERVAL_MS = 3000;

// ─── Helpers ─────────────────────────────────────────────────────────────────
function getNodeColor(node: Node, telemetry: TelemetryMap): string {
  const t = telemetry[node.id];
  if (!t?.anomaly) return '#22c55e';
  return SEVERITY_COLORS[t.severity ?? 'high'] ?? '#ef4444';
}

function getSeverityLabel(severity?: string): string {
  return severity ? severity.toUpperCase() : 'ANOMALY';
}

function getSeverityBorderColor(severity?: string): string {
  return SEVERITY_COLORS[severity ?? 'high'] ?? '#ef4444';
}

// ─── Component ───────────────────────────────────────────────────────────────
const TopologyView = () => {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [telemetry, setTelemetry] = useState<TelemetryMap>({});
  const [loadingTopo, setLoadingTopo] = useState(true);
  const [topoError, setTopoError] = useState<string | null>(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState<string | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<Set<string>>(new Set());
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/topology`)
      .then(res => res.json())
      .then(data => {
        setGraphData({
          nodes: data.nodes.map((n: any) => ({ id: n.id, name: n.label ?? n.id })),
          links: data.edges.map((e: any) => ({ source: e.source, target: e.target })),
        });
        setLoadingTopo(false);
      })
      .catch(err => { setTopoError(`Error: ${err.message}`); setLoadingTopo(false); });
  }, []);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/predict-all`);
        if (!res.ok) return;
        const data: TelemetryMap = await res.json();
        setTelemetry(data);
        
        // Safety: Clear selection if anomaly is gone
        setSelectedAnomaly(prev => (prev && data[prev]?.anomaly) ? prev : null);
      } catch {}
    };
    poll();
    const id = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  const sendFeedback = useCallback(async (timestamp: string, nodeId: string, isCorrect: boolean) => {
    const key = `${nodeId}:${timestamp}`;
    if (feedbackSent.has(key) || feedbackLoading) return;
    setFeedbackLoading(true);
    try {
      await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timestamp, nodeId, isCorrect }),
      });
      setFeedbackSent(prev => new Set(prev).add(key));
    } finally { setFeedbackLoading(false); }
  }, [feedbackSent, feedbackLoading]);

  const anomalyNodes = Object.keys(telemetry).filter(k => telemetry[k].anomaly);
  const hasAnomalies = anomalyNodes.length > 0;
  const activeAnomaly = selectedAnomaly ? telemetry[selectedAnomaly] : null;

  return (
    <div className="relative h-full w-full bg-slate-900 rounded-xl overflow-hidden border border-slate-700/50 flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700/60 bg-slate-900/80">
        <span className="text-xs font-mono text-slate-400 uppercase">SENTINEL</span>
        {hasAnomalies && <span className="text-xs text-red-400 animate-pulse">{anomalyNodes.length} Anomalies</span>}
      </div>

      <div ref={containerRef} className="flex-1 relative">
        {!loadingTopo && !topoError && (
          <ForceGraph2D
            graphData={graphData}
            width={dimensions.width} height={dimensions.height}
            backgroundColor="transparent"
            nodeColor={(node: any) => getNodeColor(node, telemetry)}
            onNodeClick={(node: any) => { if (telemetry[node.id]?.anomaly) setSelectedAnomaly(node.id); }}
          />
        )}
      </div>

      {hasAnomalies && (
        <div className="absolute top-12 right-4 w-72 flex flex-col gap-2 z-20">
          <div className="flex flex-wrap gap-1 bg-slate-800/80 p-2 rounded-lg border border-slate-700/50">
            {anomalyNodes.map(nodeId => (
              <button key={nodeId} onClick={() => setSelectedAnomaly(nodeId)} 
                className={`px-2 py-0.5 rounded text-xs font-mono ${selectedAnomaly === nodeId ? 'bg-red-600 text-white' : 'bg-slate-700 text-slate-300'}`}>
                {nodeId}
              </button>
            ))}
          </div>

          {activeAnomaly && selectedAnomaly && (
            <div className="bg-slate-800/90 rounded-lg p-3 border-l-4" style={{ borderLeftColor: getSeverityBorderColor(activeAnomaly.severity) }}>
              <p className="text-xs font-bold mb-1" style={{ color: getSeverityBorderColor(activeAnomaly.severity) }}>
                ⚠ {getSeverityLabel(activeAnomaly.severity)}
              </p>
              <p className="text-xs text-slate-200 mb-2">{activeAnomaly.explanation}</p>
              <div className="flex gap-2">
                <button onClick={() => sendFeedback(activeAnomaly.timestamp, selectedAnomaly, true)} className="flex-1 bg-green-800 text-xs py-1 rounded">Correct</button>
                <button onClick={() => sendFeedback(activeAnomaly.timestamp, selectedAnomaly, false)} className="flex-1 bg-red-900 text-xs py-1 rounded">Incorrect</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TopologyView;