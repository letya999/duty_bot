export interface User {
  id: number;
  telegram_id: number;
  first_name: string;
  last_name?: string;
  username?: string;
}

export interface Team {
  id: number;
  name: string;
  team_lead_id: number;
  workspace_id: number;
}

export interface Schedule {
  id: number;
  team_id: number;
  user_id: number;
  date: string; // YYYY-MM-DD format
  notes?: string;
}

export interface Shift {
  id: number;
  team_id: number;
  start_date: string; // YYYY-MM-DD format
  end_date: string;
  user_ids: number[];
}

export interface DailySchedule {
  date: string;
  users: User[];
  notes?: string;
}

export interface MonthSchedule {
  year: number;
  month: number;
  days: {
    date: string;
    users: User[];
    notes?: string;
  }[];
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: {
    query_id?: string;
    user?: {
      id: number;
      is_bot: boolean;
      first_name: string;
      last_name?: string;
      username?: string;
      language_code?: string;
    };
    auth_date: number;
    hash: string;
  };
  ready: () => void;
  expand: () => void;
  close: () => void;
  sendData: (data: string) => void;
  onEvent: (eventType: string, callback: (data: any) => void) => void;
  offEvent: (eventType: string, callback: (data: any) => void) => void;
  showAlert: (message: string, callback?: () => void) => void;
  showConfirm: (message: string, callback?: (confirmed: boolean) => void) => void;
  colorScheme: 'light' | 'dark';
  themeParams: {
    bg_color: string;
    text_color: string;
    hint_color: string;
    link_color: string;
    button_color: string;
    button_text_color: string;
    secondary_bg_color?: string;
    section_bg_color?: string;
  };
  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isActive: boolean;
    isProgressVisible: boolean;
    setText: (text: string) => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    showProgress: () => void;
    hideProgress: () => void;
  };
  BackButton: {
    isVisible: boolean;
    show: () => void;
    hide: () => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
  };
}

export declare global {
  interface Window {
    Telegram: {
      WebApp: TelegramWebApp;
    };
  }
}
