export interface ChatSession {
  id: number;
  agent_id: string;
  title: string;
  is_running: boolean;
  created_at: string;
  updated_at: string;
}

export interface ToolCall {
  name: string;
  args: Record<string, any>;
  status: 'running' | 'completed';
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  reasoning_content?: string;
  tool_calls?: ToolCall[];
  name?: string; // Present when role is 'tool'
}


export interface Agent {
  id: string;
  name: string;
  description: string;
  system_prompt?: string; // Added to support fetching full details for editing
  interactive: boolean;
  read_only: boolean;
  allowed_tools: string[];
  allowed_agents: string[];
  model_name?: string | null;
  is_default?: boolean;
}

export interface AgentCreate {
  name: string;
  description: string;
  system_prompt: string;
  interactive: boolean;
  allowed_tools: string[];
  allowed_agents: string[];
  model_name?: string | null;
}

export interface AgentUpdate {
  description: string;
  system_prompt: string;
  interactive: boolean;
  allowed_tools: string[];
  allowed_agents: string[];
  model_name?: string | null;
  is_default?: boolean;
}

export interface TokenUsage {
  history_tokens: number;
  clipboard_tokens: number;
  total_tokens: number;
  max_tokens: number;
  percent: number;
}
