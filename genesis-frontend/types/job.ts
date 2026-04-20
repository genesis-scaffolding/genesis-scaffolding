export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface WorkflowJob {
  id: number;
  workflow_id: string;
  status: JobStatus;
  inputs: Record<string, any>;
  result: Record<string, string> | null;
  step_status: Record<string, string> | null;
  error_message: string | null;
  workspace_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedJobs {
  jobs: WorkflowJob[];
  total: number;
  limit: number;
  offset: number;
}

export interface JobFile {
  name: string;
  path: string;
  size: number;
}
