// src/components/ChatMessage.tsx — Track 7 + 15
import { Terminal } from "lucide-react";
import CitationBlock from "./CitationBlock";
import ConfigBlock from "./ConfigBlock";
import type { ChatMessage as ChatMessageType } from "../types";

interface Props {
  message: ChatMessageType;
}

const CONFIG_BLOCK_RE = /```(cisco-ios|junos)\n([\s\S]*?)```/g;
const CITATION_RE = /(\[.*? Config \(Chunk \d+\)\])/g;
const APPLY_LINE_RE = /⚠ Apply on:.*$/m;

function renderContent(text: string) {
  // Step 1: split out config blocks first
  const segments: Array<{ type: "text" | "config"; content: string; os?: "cisco-ios" | "junos" }> = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  CONFIG_BLOCK_RE.lastIndex = 0;
  while ((match = CONFIG_BLOCK_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", content: text.slice(lastIndex, match.index) });
    }
    segments.push({ type: "config", content: match[2].trim(), os: match[1] as "cisco-ios" | "junos" });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    segments.push({ type: "text", content: text.slice(lastIndex) });
  }

  // Step 2: within text segments, parse citations
  return segments.map((seg, idx) => {
    if (seg.type === "config") {
      const applyMatch = seg.content.match(APPLY_LINE_RE);
      return (
        <ConfigBlock
          key={idx}
          os={seg.os!}
          code={seg.content}
          applyLine={applyMatch ? applyMatch[0] : undefined}
        />
      );
    }

    const parts = seg.content.split(CITATION_RE);
    return (
      <span key={idx}>
        {parts.map((part, i) => {
          if (part.match(/\[.*? Config \(Chunk \d+\)\]/)) {
            const label = part.replace(/[[\]]/g, "");
            return <CitationBlock key={i} label={label} />;
          }
          return <span key={i}>{part}</span>;
        })}
      </span>
    );
  });
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-5 py-4 ${
          isUser
            ? "bg-blue-600 text-white shadow-blue-900/20 shadow-lg"
            : "bg-gray-800 text-gray-200 border border-gray-700 shadow-xl"
        }`}
      >
        {!isUser && (
          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-700/50 text-xs font-medium text-cyan-400 uppercase tracking-wide">
            <Terminal size={12} /> NetOps Assistant
          </div>
        )}
        <div className="whitespace-pre-wrap leading-relaxed text-sm">
          {renderContent(message.content)}
        </div>
      </div>
    </div>
  );
}