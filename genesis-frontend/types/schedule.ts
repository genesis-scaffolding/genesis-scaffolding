export interface WorkflowSchedule {
  id: number;
  name: string;
  workflow_id: string;
  cron_expression: string;
  timezone: string;
  inputs: Record<string, any>;
  enabled: boolean;
  last_run_at: string | null;
  user_id: number;
}

export interface CreateScheduleInput {
  name: string;
  workflow_id: string;
  cron_expression: string;
  timezone?: string;
  inputs: Record<string, any>;
  enabled?: boolean;
}

export interface UpdateScheduleInput {
  name?: string;
  cron_expression?: string;
  timezone?: string;
  inputs?: Record<string, any>;
  enabled?: boolean;
}
