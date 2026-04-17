'use server'

import { apiFetch } from "@/lib/api-client";
import { Agent, AgentCreate, AgentUpdate } from "@/types/chat";
import { ChatSession } from "@/types/chat";
import { revalidatePath } from "next/cache";

export async function getChatHistoryAction(sessionId: number) {
  const res = await apiFetch(`/chats/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

export async function sendChatMessageAction(sessionId: number, userInput: string, inputIndex?: number) {
  const params = new URLSearchParams();
  if (inputIndex !== undefined) {
    params.set('input_index', String(inputIndex));
  }
  const res = await apiFetch(`/chats/${sessionId}/message?${params.toString()}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_input: userInput }),
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
}

export async function getAgentsAction(): Promise<Agent[]> {
  const res = await apiFetch(`/agents/`);
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export async function createAgentAction(data: AgentCreate): Promise<Agent> {
  const res = await apiFetch(`/agents/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || "Failed to create agent");
  }

  const newAgent = await res.json();
  revalidatePath('/dashboard/agents');
  return newAgent;
}

export async function getAgentAction(agentId: string): Promise<Agent> {
  const res = await apiFetch(`/agents/${agentId}`);
  if (!res.ok) throw new Error("Failed to fetch agent details");
  return res.json();
}

export async function updateAgentAction(agentId: string, data: AgentUpdate): Promise<Agent> {
  const res = await apiFetch(`/agents/${agentId}`, {
    method: 'PATCH', // or 'PUT' depending on your FastAPI implementation
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || "Failed to update agent");
  }

  const updatedAgent = await res.json();
  revalidatePath('/dashboard/agents');
  return updatedAgent;
}

export async function deleteAgentAction(agentId: string) {
  const res = await apiFetch(`/agents/${agentId}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || "Failed to delete agent");
  }

  revalidatePath('/dashboard/agents');
  return true;
}


export async function listChatSessionsAction(): Promise<ChatSession[]> {
  const res = await apiFetch(`/chats/`);
  if (!res.ok) throw new Error("Failed to fetch chat sessions");
  return res.json();
}

// Optional: Add a delete action if you want to support cleanup
export async function deleteChatSessionAction(sessionId: number) {
  const res = await apiFetch(`/chats/${sessionId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error("Failed to delete session");
  return true;
}
