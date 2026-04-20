'use server';

import { ChatSession, ChatMessage, TokenUsage } from '@/types/chat';
import { getDefaultAgentAction } from './agents';
import { apiFetch } from '@/lib/api-client';

interface QuickChatData {
  session: ChatSession;
  messages: ChatMessage[];
  context_tokens?: TokenUsage;
}

export async function openQuickChatAction(): Promise<QuickChatData> {
  // 1. Resolve default agent
  const defaultAgent = await getDefaultAgentAction();

  // 2. Fetch all sessions (ordered by updated_at desc)
  const sessionsRes = await apiFetch('/chats/');
  if (!sessionsRes.ok) throw new Error('Failed to fetch chat sessions');
  const sessions: ChatSession[] = await sessionsRes.json();

  // 3. Find most recent session for this agent
  const recentSession = sessions.find(s => s.agent_id === defaultAgent.id);

  // 4. If found and updated within 1 hour, reuse it
  if (recentSession) {
    // Parse as UTC — backend stores datetime.now(UTC) but isoformat() strips the Z suffix
    const updatedAt = new Date(recentSession.updated_at + 'Z');
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    if (updatedAt >= oneHourAgo) {
      // Fetch full chat history for this session
      const historyRes = await apiFetch(`/chats/${recentSession.id}`);
      if (!historyRes.ok) throw new Error('Failed to fetch chat history');
      const history = await historyRes.json();
      return {
        session: history.session,
        messages: history.messages.map((m: any) => m.payload),
        context_tokens: history.context_tokens,
      };
    }
  }

  // 5. Create new session
  const createRes = await apiFetch('/chats/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent_id: defaultAgent.id,
      title: 'Quick Chat',
    }),
  });
  if (!createRes.ok) throw new Error('Failed to create chat session');
  const newSession: ChatSession = await createRes.json();

  return {
    session: newSession,
    messages: [],
  };
}
