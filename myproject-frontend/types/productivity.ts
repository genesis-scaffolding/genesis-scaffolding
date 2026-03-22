export type Status = 'backlog' | 'todo' | 'in_progress' | 'completed' | 'canceled';
// Define the "Heat" order (Higher number = "Hotter" / Top of list)
export const STATUS_WEIGHTS: Record<Status, number> = {
  in_progress: 5,
  todo: 4,
  backlog: 3,
  completed: 2,
  canceled: 1,
};

export type JournalType = 'daily' | 'weekly' | 'monthly' | 'yearly' | 'project' | 'general';

export interface Project {
  id: number;
  name: string;
  description?: string;
  start_date?: string; // Floating Date: "YYYY-MM-DD"
  deadline?: string;   // Floating Date: "YYYY-MM-DD"
  status: Status;
}

export interface Task {
  id: number;
  title: string;
  description?: string;

  // Absolute Point in Time: "2024-10-25T14:30:00Z"
  hard_deadline?: string;

  // Floating Planning Date: "YYYY-MM-DD"
  assigned_date?: string;

  // Absolute Appointment Time: "2024-10-25T09:00:00Z"
  scheduled_start?: string;

  duration_minutes?: number;
  status: Status;

  // Metadata: Always ISO Strings
  created_at: string;
  completed_at?: string;

  project_ids: number[];
}

export interface JournalEntry {
  id: number;
  entry_type: JournalType;
  reference_date: string; // Floating Date: "YYYY-MM-DD"
  title?: string;
  content: string;
  project_id?: number;
  created_at: string;
  updated_at: string;
}
