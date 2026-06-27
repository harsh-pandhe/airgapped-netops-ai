import TopologyView from './TopologyView';
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Activity, Server, AlertTriangle, CheckCircle, Send, Terminal, Loader2 } from 'lucide-react';
import ObservabilityTab from './ObservabilityTab';


const API_BASE = "http://127.0.0.1:8000/api";

type NodeStatus = 'healthy' | 'warning' | 'critical' | 'failed' | 'loading';

interface NetworkNode {
  id: string;
  name: string;
  type: string;
  ip: string;
  cpu: number;
  memory: number;
  temp: number;
  latency: number;
  loss: number;
  status: NodeStatus; 
}

const initialNodes: NetworkNode[] = [
  { id: 'RTR-001', name: 'RTR-001 (Core)', type: 'Cisco ASR', ip: '192.168.1.1', cpu: 45, memory: 60, temp: 42, latency: 15, loss: 0.1, status: 'loading' },
  { id: 'RTR-002', name: 'RTR-002 (Edge)', type: 'Juniper MX', ip: '192.168.1.2', cpu: 95, memory: 88, temp: 75, latency: 150, loss: 5.5, status: 'loading' },
  { id: 'SW-001', name: 'SW-001 (Data)', type: 'Cisco Nexus', ip: '192.168.2.1', cpu: 20, memory: 30, temp: 35, latency: 5, loss: 0.0, status: 'loading' },
  { id: 'FW-001', name: 'FW-001 (Perimeter)', type: 'Palo Alto', ip: '192.168.3.1', cpu: 85, memory: 85, temp: 60, latency: 50, loss: 2.0, status: 'loading' },
];

const renderMessageWithCitations = (text: string) => {
    if (!text) return null;
    const parts = text.split(/(\[.*? Config \(Chunk \d+\)\])/g);
    
    return parts.map((part, index) => {
        if (part.match(/\[.*? Config \(Chunk \d+\)\]/)) {
            const cleanTitle = part.replace(/[\[\]]/g, ''); 
            return (
                <details key={index} className="mt-2 p-2 bg-slate-800 rounded border border-slate-700 text-sm block w-full">
                    <summary className="cursor-pointer text-cyan-400 hover:text-cyan-300 font-mono font-semibold">
                        Source: {cleanTitle}
                    </summary>
                    <div className="mt-2 p-3 bg-black text-slate-300 font-mono text-xs overflow-x-auto rounded border border-slate-600">
                        View retrieved context snippet...
                    </div>
                </details>
            );
        }
        return <span key={index}>{part}</span>;
    });
};

export default function App() {
  const [nodes, setNodes] = useState<NetworkNode[]>(initialNodes);
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant', content: string }[]>([
    { role: 'assistant', content: 'Air-Gapped NetOps Copilot initialized. How can I assist you with your network infrastructure today?' }
  ]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<'chat' | 'topology' | 'observability'>('chat');

  useEffect(() => {
    const fetchPredictions = async () => {
      try {
        const updatedNodes = await Promise.all(nodes.map(async (node) => {
          try {
            const res = await axios.post(`${API_BASE}/predict`, {
              cpu_usage: node.cpu,
              memory_usage: node.memory,
              temperature: node.temp,
              latency: node.latency,
              packet_loss: node.loss
            });
            return { ...node, status: res.data.prediction as NodeStatus };
          } catch (e) {
            return { ...node, status: 'warning' as NodeStatus };
          }
        }));
        setNodes(updatedNodes);
      } catch (e) {
        console.error("Polling error:", e);
      }
    };

    fetchPredictions();
    const intervalId = setInterval(fetchPredictions, 3000);
    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isChatLoading) return;
    const userMessage = chatInput.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setChatInput('');
    setIsChatLoading(true);

    try {
      const res = await axios.post(`${API_BASE}/chat`, { message: userMessage });
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.reply }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Unable to reach Copilot Backend.' }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const getStatusColor = (status: NodeStatus) => {
    switch (status) {
      case 'healthy': return 'text-green-400';
      case 'warning': return 'text-yellow-400';
      case 'critical': return 'text-red-500 animate-pulse';
      case 'failed': return 'text-red-600';
      default: return 'text-gray-400';
    }
  };

  const getStatusIcon = (status: NodeStatus) => {
    switch (status) {
      case 'healthy': return <CheckCircle size={18} />;
      case 'warning': return <AlertTriangle size={18} />;
      case 'critical': return <AlertTriangle size={18} className="animate-pulse" />;
      case 'failed': return <AlertTriangle size={18} />;
      default: return <Loader2 size={18} className="animate-spin" />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 font-sans overflow-hidden">
      <aside className="w-80 bg-gray-900 border-r border-gray-800 flex flex-col shadow-2xl z-10">
        <div className="p-6 border-b border-gray-800 flex items-center gap-3">
          <Activity className="text-cyan-400" size={24} />
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            NetOps AI
          </h1>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Live Nodes</h2>
          {nodes.map(node => (
            <div key={node.id} className="bg-gray-800/50 rounded-xl p-4 border border-gray-700 hover:border-gray-600 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <Server size={16} className="text-gray-400" />
                  <span className="font-semibold text-sm">{node.id}</span>
                </div>
                <div className={`flex items-center gap-1 ${getStatusColor(node.status)}`}>
                  {getStatusIcon(node.status)}
                </div>
              </div>
              <div className="text-xs text-gray-400 mb-3">{node.type} | {node.ip}</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-gray-900 rounded p-2">
                  <span className="text-gray-500 block mb-1">CPU</span>
                  <span className={`font-medium ${node.cpu > 80 ? 'text-red-400' : 'text-green-400'}`}>{node.cpu}%</span>
                </div>
                <div className="bg-gray-900 rounded p-2">
                  <span className="text-gray-500 block mb-1">Latency</span>
                  <span className={`font-medium ${node.latency > 100 ? 'text-red-400' : 'text-green-400'}`}>{node.latency}ms</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </aside>
      <main className="flex-1 flex flex-col relative">
        <header className="h-16 border-b border-gray-800 flex items-center px-6 bg-gray-900/50 backdrop-blur-md sticky top-0 z-10">
          <Terminal size={20} className="text-gray-400 mr-3" />
          <h2 className="text-lg font-medium text-gray-200">Air-Gapped Copilot</h2>
        </header>
        <div className="flex gap-2 mb-4 p-1 bg-slate-800 rounded-lg w-fit border border-slate-700 mx-6 mt-4">
          <button onClick={() => setActiveTab('chat')} className={`px-4 py-2 rounded-md text-sm font-semibold transition-colors ${activeTab === 'chat' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}>Terminal Chat</button>
          <button onClick={() => setActiveTab('topology')} className={`px-4 py-2 rounded-md text-sm font-semibold transition-colors ${activeTab === 'topology' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}>Live Topology Map</button>
          <button onClick={() => setActiveTab('observability')} className={`px-4 py-2 rounded-md text-sm font-semibold transition-colors ${activeTab === 'observability' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}>Observability</button>
        </div>
        {activeTab === 'chat' ? (
          <>
            <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-gray-950 to-gray-900">
               {messages.map((msg, idx) =>  (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[75%] rounded-2xl px-5 py-4 ${msg.role === 'user' ? 'bg-blue-600 text-white shadow-blue-900/20 shadow-lg' : 'bg-gray-800 text-gray-200 border border-gray-700 shadow-xl'}`}>
                    {msg.role === 'assistant' && <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-700/50 text-xs font-medium text-cyan-400 uppercase tracking-wide"><Terminal size={12} />NetOps Assistant</div>}
                    <div className="whitespace-pre-wrap leading-relaxed text-sm">{renderMessageWithCitations(msg.content)}</div>
                  </div>
                </div>
              ))}
              {isChatLoading && <div className="flex justify-start"><div className="bg-gray-800 border border-gray-700 rounded-2xl px-5 py-4 shadow-xl flex items-center gap-3 text-sm text-gray-400"><Loader2 size={16} className="animate-spin text-cyan-400" />Querying local vectors and reasoning...</div></div>}
              <div ref={messagesEndRef} />
            </div>
            <div className="p-6 bg-gray-900 border-t border-gray-800">
              <form onSubmit={handleSendMessage} className="relative max-w-4xl mx-auto">
                <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)} placeholder="Ask about node failures..." className="w-full bg-gray-950 border border-gray-700 rounded-xl pl-5 pr-14 py-4 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-all" />
                <button type="submit" disabled={isChatLoading || !chatInput.trim()} className="absolute right-2 top-2 bottom-2 bg-blue-600 rounded-lg px-4"><Send size={18} /></button>
              </form>
            </div>
          </>
        ) : activeTab === 'topology' ? (
          <div className="flex-1 p-6 bg-slate-950 flex flex-col items-center justify-center"><TopologyView /></div>
        ) : (
          <div className="flex-1 p-6 bg-slate-950 overflow-y-auto">
            <ObservabilityTab />
          </div>
        )}
      </main>
    </div>
  );
}