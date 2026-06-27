import { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, Database, Zap, Cpu, HardDrive } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export default function ObservabilityTab() {
  const [metrics, setMetrics] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await axios.get("http://127.0.0.1:8000/api/metrics");
        const data = res.data;
        setMetrics(data);
        
        // Add new data point to history, keep last 20
        setHistory(prev => [...prev.slice(-19), { 
            time: new Date().toLocaleTimeString(), 
            cpu: data.hardware.cpu_percent, 
            ram: data.hardware.ram_percent 
        }]);
      } catch (e) { console.error("Metrics fetch failed", e); }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 3000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics) return <div className="text-gray-400 p-8">Loading system telemetry...</div>;

  return (
    <div className="p-8 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-900 p-6 rounded-xl border border-gray-700 flex items-center gap-4">
          <Zap className="text-cyan-400" size={32} />
          <div>
            <h3 className="text-gray-400 text-sm">Avg Inference</h3>
            <p className="text-2xl font-bold">{metrics.avg_inference_ms} ms</p>
          </div>
        </div>
        <div className="bg-gray-900 p-6 rounded-xl border border-gray-700 flex items-center gap-4">
          <Database className="text-emerald-400" size={32} />
          <div>
            <h3 className="text-gray-400 text-sm">Avg Retrieval</h3>
            <p className="text-2xl font-bold">{metrics.avg_retrieval_ms} ms</p>
          </div>
        </div>
        <div className="bg-gray-900 p-6 rounded-xl border border-gray-700 flex items-center gap-4">
          <Activity className="text-purple-400" size={32} />
          <div>
            <h3 className="text-gray-400 text-sm">Total Tokens</h3>
            <p className="text-2xl font-bold">{metrics.total_tokens}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-900 p-6 rounded-xl border border-gray-700 h-64">
          <h3 className="text-gray-400 text-sm mb-4 flex items-center gap-2"><Cpu size={16}/> CPU Utilization (%)</h3>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" hide />
              <YAxis stroke="#9ca3af" />
              <Tooltip contentStyle={{ backgroundColor: '#111827' }} />
              <Line type="monotone" dataKey="cpu" stroke="#22d3ee" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-gray-900 p-6 rounded-xl border border-gray-700 h-64">
          <h3 className="text-gray-400 text-sm mb-4 flex items-center gap-2"><HardDrive size={16}/> RAM Utilization (%)</h3>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" hide />
              <YAxis stroke="#9ca3af" />
              <Tooltip contentStyle={{ backgroundColor: '#111827' }} />
              <Line type="monotone" dataKey="ram" stroke="#34d399" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}