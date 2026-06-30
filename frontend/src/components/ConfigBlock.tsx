// src/components/ConfigBlock.tsx — Track 15
import { useState } from "react";
import { Copy, Check, ChevronDown, ChevronUp, Terminal } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";

interface Props {
  os: "cisco-ios" | "junos";
  code: string;
  applyLine?: string;
}

export default function ConfigBlock({ os, code, applyLine }: Props) {
  const [copied, setCopied] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard unavailable — silently ignore
    }
  };

  const osBadge = os === "cisco-ios"
    ? { label: "Cisco IOS", color: "bg-blue-600" }
    : { label: "JunOS", color: "bg-green-600" };

  return (
    <div className="mt-2 rounded-lg border border-slate-700 overflow-hidden bg-[#1e1e1e]">
      <div className="flex items-center justify-between px-3 py-2 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-slate-400" />
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${osBadge.color} text-white`}>
            {osBadge.label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-xs text-slate-300 hover:text-white bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded transition-colors"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            {copied ? "Copied!" : "Copy"}
          </button>
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="text-slate-400 hover:text-white"
          >
            {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>
      </div>

      {!collapsed && (
        <>
          <SyntaxHighlighter
            language={os === "cisco-ios" ? "ini" : "nginx"}
            style={atomOneDark}
            customStyle={{ margin: 0, fontSize: "12px", padding: "12px" }}
          >
            {code}
          </SyntaxHighlighter>
          {applyLine && (
            <div className="px-3 py-2 bg-amber-950/40 border-t border-amber-900/50 text-xs text-amber-300 font-mono">
              {applyLine}
            </div>
          )}
        </>
      )}
    </div>
  );
}