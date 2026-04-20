export interface User {
  id: string;
  username: string;
  email?: string;
  full_name?: string;
  created_at?: string;
  updated_at?: string;
  is_active?: boolean;
  is_superuser?: boolean;
}
