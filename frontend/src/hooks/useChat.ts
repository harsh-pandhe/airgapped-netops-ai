// src/hooks/useChat.ts
import { useState, useRef, useCallback } from "react";
import { api, ApiError } from "../api/client";
import type { ChatMessage } from "../types";

const INITIAL: ChatMessage[] = [
  {
    role: "assistant",
    content: "Air-Gapped NetOps Copilot initialized. How can I assist you with your network infrastructure today?",
  },
];

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const send = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setError(null);
    try {
      const res = await api.chat(text);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Unable to reach Copilot Backend.";
      setError(msg);
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${msg}` }]);
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }, [loading]);

  const sendWithPrefill = useCallback((text: string) => {
    send(text);
  }, [send]);

  return { messages, loading, error, send, sendWithPrefill, bottomRef };
}