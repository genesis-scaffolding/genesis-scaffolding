export type MemorySource = "agent_tool" | "dream_workflow" | "user_manual";

export type MemoryType = "event" | "topic";

export interface EventLog {
  id: number;
  subject: string | null;
  event_time: string; // ISO datetime
  content: string;
  tags: string[];
  importance: number;
  source: MemorySource;
  related_memory_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface TopicalMemory {
  id: number;
  subject: string | null;
  content: string;
  tags: string[];
  importance: number;
  source: MemorySource;
  superseded_by_id: number | null;
  supersedes_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface MemoryListResponse {
  events: EventLog[];
  topics: TopicalMemory[];
}

export interface TagCountResponse {
  tag_counts: Record<string, number>;
}

export interface MemoryRevisionChain {
  current: TopicalMemory;
  chain: TopicalMemory[];
}
