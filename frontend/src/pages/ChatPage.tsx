// src/pages/ChatPage.tsx — Track 7
import { Send, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { useChat } from "../hooks/useChat";
import ChatMessage from "../components/ChatMessage";

const QUICK_PROMPTS = [
  "What nodes are currently critical?",
  "Why is RTR-002 showing anomaly?",
  "Show BGP config for RTR-001",
  "Generate Cisco IOS commands to fix high latency",
];

interface Props {
  prefillPrompt?: string | null;
  onPrefillConsumed?: () => void;
}

export default function ChatPage({ prefillPrompt, onPrefillConsumed }: Props) {
  const { messages, loading, error, send, bottomRef } = useChat();
  const [input, setInput] = useState("");

  useEffect(() => {
    if (prefillPrompt) {
      setInput(prefillPrompt);
      onPrefillConsumed?.();
    }
  }, [prefillPrompt]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    send(input.trim());
    setInput("");
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-6 pt-3 flex gap-2 flex-wrap shrink-0">
        {QUICK_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => setInput(p)}
            className="text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-full px-3 py-1 text-gray-300 transition-colors"
          >
            {p}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-gray-950 to-gray-900">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} message={msg} />
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700 rounded-2xl px-5 py-4 shadow-xl flex items-center gap-3 text-sm text-gray-400">
              <Loader2 size={16} className="animate-spin text-cyan-400" />
              Querying local vectors and reasoning...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="mx-6 mb-2 text-xs text-red-400">{error}</div>
      )}

      <div className="p-6 bg-gray-900 border-t border-gray-800 shrink-0">
        <form onSubmit={handleSubmit} className="relative max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about node failures, or request mitigation commands..."
            className="w-full bg-gray-950 border border-gray-700 rounded-xl pl-5 pr-14 py-4 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-all"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="absolute right-2 top-2 bottom-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg px-4"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}