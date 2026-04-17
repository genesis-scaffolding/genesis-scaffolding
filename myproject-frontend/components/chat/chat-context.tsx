'use client'

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { ChatMessage, ChatSession, TokenUsage } from '@/types/chat';
import { getChatHistoryAction, sendChatMessageAction } from '@/app/actions/chat';

interface ChatContextType {
  session: ChatSession;
  messages: ChatMessage[];
  sendMessage: (input: string, inputIndex?: number) => Promise<void>;
  isRunning: boolean;
  tokenUsage: TokenUsage | null
  clipboardMd: string | null;
}

const ChatContext = createContext<ChatContextType | null>(null);

export const ChatProvider = ({
  session: initialSession,
  initialMessages,
  initialTokenUsage,
  children
}: {
  session: ChatSession;
  initialMessages: ChatMessage[];
  initialTokenUsage?: {
    history_tokens: number
    clipboard_tokens: number
    total_tokens: number
    max_tokens: number
    percent: number
  };
  children: React.ReactNode;
}) => {
  const [session, setSession] = useState(initialSession);

  const [historicalMessages, setHistoricalMessages] = useState<ChatMessage[]>(initialMessages);

  const activeRunRef = useRef<ChatMessage[]>([]);
  const [displayActiveMessages, setDisplayActiveMessages] = useState<ChatMessage[]>([]);

  const [isRunning, setIsRunning] = useState(initialSession.is_running);

  const [tokenUsage, setTokenUsage] = useState(initialTokenUsage ?? null)

  const [clipboardMd, setClipboardMd] = useState<string | null>(null);

  // --- 10fps Display Debouncer ---
  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      setDisplayActiveMessages(
        activeRunRef.current
          .filter(Boolean)
          .map(msg => ({
            ...msg,
            tool_calls: Array.isArray(msg.tool_calls) ? [...msg.tool_calls] : undefined
          }))
      );
    }, 100);

    return () => clearInterval(interval);
  }, [isRunning]);

  const refreshHistory = useCallback(async () => {
    console.log("🔄 [ChatContext] Refreshing history from DB...");
    try {
      const data = await getChatHistoryAction(session.id);
      setHistoricalMessages(data.messages.map((m: any) => m.payload));
      if (data.context_tokens) setTokenUsage(data.context_tokens);
      activeRunRef.current = [];
      setDisplayActiveMessages([]);
    } catch (err) {
      console.error("❌ [ChatContext] History refresh failed", err);
    }
  }, [session.id]);

  // --- Ephemeral SSE Connection ---
  useEffect(() => {
    if (!isRunning) return;

    console.group(`📡 [SSE] Connecting to session ${session.id}`);

    const eventSource = new EventSource(`/api/chats/${session.id}/stream`);

    eventSource.onopen = () => console.log("✅ [SSE] Connection established");

    eventSource.addEventListener('catchup', (e) => {
      const data = JSON.parse(e.data);
      console.log("📥 [SSE] Catchup received", data.interim_messages);
      activeRunRef.current = data.interim_messages;
    });

    eventSource.addEventListener('content', (e) => {
      const { data, index } = JSON.parse(e.data);
      if (!activeRunRef.current[index]) {
        activeRunRef.current[index] = { role: 'assistant', content: '' };
      }
      activeRunRef.current[index].content += data;
    });

    eventSource.addEventListener('reasoning', (e) => {
      const { data, index } = JSON.parse(e.data);
      if (!activeRunRef.current[index]) {
        activeRunRef.current[index] = { role: 'assistant', content: '', reasoning_content: '' };
      }
      activeRunRef.current[index].reasoning_content =
        (activeRunRef.current[index].reasoning_content || "") + data;
    });

    eventSource.addEventListener('tool_start', (e) => {
      const { data, index } = JSON.parse(e.data);
      console.log("🛠️ [SSE] Tool Start", data.name);

      if (!activeRunRef.current[index]) {
        activeRunRef.current[index] = { role: 'assistant', content: '', tool_calls: [] };
      }
      if (!activeRunRef.current[index].tool_calls) {
        activeRunRef.current[index].tool_calls = [];
      }

      activeRunRef.current[index].tool_calls!.push({ ...data, status: 'running' });
    });

    eventSource.addEventListener('tool_result', (e) => {
      const { data, index } = JSON.parse(e.data);
      console.log("✅ [SSE] Tool Result", data.name);

      for (let i = activeRunRef.current.length - 1; i >= 0; i--) {
        const msg = activeRunRef.current[i];
        if (msg && msg.role === 'assistant' && Array.isArray(msg.tool_calls)) {
          const tc = msg.tool_calls.find(t => t.name === data.name && t.status === 'running');
          if (tc) { tc.status = 'completed'; break; }
        }
      }

      activeRunRef.current[index] = data;
    });

    eventSource.addEventListener('token_usage', (e) => {
      const parsed = JSON.parse(e.data);
      setTokenUsage(parsed.data ?? parsed);
    });

    eventSource.addEventListener('clipboard', (e) => {
      const parsed = JSON.parse(e.data);
      setClipboardMd(parsed.data?.clipboard_md ?? null);
    });

    eventSource.onerror = () => {
      console.log("🔚 [SSE] Connection closed or errored");
      eventSource.close();
      console.groupEnd();
      setIsRunning(false);
      refreshHistory();
    };

    return () => { eventSource.close(); console.groupEnd(); }
  }, [isRunning, session.id, refreshHistory]);

  const sendMessage = async (input: string, inputIndex?: number) => {
    if (isRunning) return;

    console.group(`🚀 [Message Flow] User Prompt: ${input.substring(0, 20)}...`);

    // When editing (inputIndex is negative), optimistically truncate historicalMessages
    if (inputIndex !== undefined && inputIndex < 0) {
      console.log("debug", "Attempting to truncate historicalMessages")
      console.log("debug", "inputIndex: ", inputIndex)
      const userIndices: number[] = [];
      historicalMessages.forEach((msg, i) => {
        if (msg.role === 'user') userIndices.push(i);
      });
      console.log("debug", "userIndices", userIndices)
      const targetIdx = userIndices[userIndices.length + inputIndex]; // inputIndex is negative, indexing into userIndices
      console.log("debug", "Index of the user message being edited", targetIdx)
      const truncated = historicalMessages.slice(0, targetIdx);
      console.log("debug", "Truncated history", truncated)
      setHistoricalMessages(truncated);
      activeRunRef.current = [{ role: 'user', content: input }];
      setDisplayActiveMessages([...activeRunRef.current]);
    } else {
      // Default behavior: append new message
      activeRunRef.current = [{ role: 'user', content: input }];
      setDisplayActiveMessages([...activeRunRef.current]);
    }
    console.log("1. Optimistic UI updated");

    try {
      console.log("2. Sending POST request...");
      await sendChatMessageAction(session.id, input, inputIndex);
      console.log("3. POST successful, run created on backend");
      setIsRunning(true);
    } catch (error) {
      console.error("❌ [Message Flow] Failed at step 2", error);
      setIsRunning(false);
      // Rollback: restore full history from server
      refreshHistory();
      console.groupEnd();
    }
  };

  const allMessages = [...historicalMessages, ...displayActiveMessages];

  return (
    <ChatContext.Provider value={{ session, messages: allMessages, sendMessage, isRunning, tokenUsage, clipboardMd }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) throw new Error("useChat must be used within ChatProvider");
  return context;
};
