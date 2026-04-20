'use server';

import { Agent } from '@/types/chat';
import { apiFetch } from '@/lib/api-client';

export async function getDefaultAgentAction(): Promise<Agent> {
  const res = await apiFetch(`/agents/`);
  if (!res.ok) throw new Error('Failed to fetch agents');

  const agents: Agent[] = await res.json();
  if (agents.length === 0) throw new Error('No agents configured');

  // Filter agents marked as default, sort by id ascending, take first
  const defaultAgents = agents
    .filter(a => a.is_default === true)
    .sort((a, b) => a.id.localeCompare(b.id));

  if (defaultAgents.length > 0) return defaultAgents[0];

  // Fallback: return first agent by id
  const fallback = [...agents].sort((a, b) => a.id.localeCompare(b.id))[0];
  return fallback;
}
