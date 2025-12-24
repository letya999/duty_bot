// User types
export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name?: string;
  is_admin: boolean;
  workspace_id: number;
  telegram_id?: number;
  slack_user_id?: string;
}

// Team types
export interface Team {
  id: number;
  name: string;
  description?: string;
  workspace_id: number;
  members: User[];
}

// Schedule types
export interface Schedule {
  id: number;
  user_id: number;
  duty_date: string;
  team_id?: number;
  notes?: string;
  user: User;
  team?: Team;
}

export interface Shift {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  members: User[];
  workspace_id: number;
}

// Daily/Month schedule views
export interface DailySchedule {
  date: string;
  duties: Schedule[];
}

export interface MonthSchedule {
  month: number;
  year: number;
  days: DailySchedule[];
}

// Auth types
export interface LoginResponse {
  success: boolean;
  session_token?: string;
  user?: User;
  message?: string;
}

export interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  login: (method: 'telegram' | 'slack') => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
  error: string | null;
}

// Admin types
export interface AdminAction {
  id: number;
  admin_user_id: number;
  action: string;
  target_user_id?: number;
  timestamp: string;
  details?: Record<string, any>;
  admin_user?: User;
  target_user?: User;
}

export interface Workspace {
  id: number;
  name: string;
  platform: 'telegram' | 'slack';
  platform_id: string;
}
