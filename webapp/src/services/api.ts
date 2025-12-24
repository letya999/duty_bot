import axios from 'axios';
import { MonthSchedule, DailySchedule, Team, User, Schedule, AdminAction } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/admin';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add session token to all requests
api.interceptors.request.use((config) => {
  const sessionToken = localStorage.getItem('session_token');
  if (sessionToken) {
    config.headers['Authorization'] = `Bearer ${sessionToken}`;
  }
  return config;
});

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('session_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const apiService = {
  // Get current user info
  getUserInfo: async (): Promise<User> => {
    const response = await api.get('/user/info');
    return response.data;
  },

  // Get month schedule
  getMonthSchedule: async (year: number, month: number): Promise<MonthSchedule> => {
    const response = await api.get('/schedule/month', {
      params: { year, month },
    });
    return response.data;
  },

  // Get daily schedule
  getDailySchedule: async (date: string): Promise<DailySchedule> => {
    const response = await api.get(`/schedule/day/${date}`);
    return response.data;
  },

  // Get all teams
  getTeams: async (): Promise<Team[]> => {
    const response = await api.get('/teams');
    return response.data;
  },

  // Assign duty to user
  assignDuty: async (userId: number, dutyDate: string, teamId?: number): Promise<Schedule> => {
    const response = await api.post('/schedule/assign', {
      user_id: userId,
      duty_date: dutyDate,
      team_id: teamId,
    });
    return response.data;
  },

  // Remove duty
  removeDuty: async (scheduleId: number): Promise<any> => {
    const response = await api.delete(`/schedule/${scheduleId}`);
    return response.data;
  },

  // Get team members
  getTeamMembers: async (teamId: number): Promise<User[]> => {
    const response = await api.get(`/teams/${teamId}/members`);
    return response.data;
  },

  // Get all admins
  getAdmins: async (): Promise<User[]> => {
    const response = await api.get('/admins');
    return response.data.admins;
  },

  // Promote user to admin
  promoteUser: async (userId: number): Promise<User> => {
    const response = await api.post(`/users/${userId}/promote`);
    return response.data.user;
  },

  // Demote user from admin
  demoteUser: async (userId: number): Promise<User> => {
    const response = await api.post(`/users/${userId}/demote`);
    return response.data.user;
  },

  // Get all users
  getAllUsers: async (): Promise<User[]> => {
    const response = await api.get('/users');
    return response.data;
  },

  // Get admin logs
  getAdminLogs: async (limit: number = 50): Promise<AdminAction[]> => {
    const response = await api.get('/admin-logs', {
      params: { limit },
    });
    return response.data.logs || [];
  },

  // Get schedules by date range
  getSchedulesByDateRange: async (startDate: string, endDate: string): Promise<Schedule[]> => {
    const response = await api.get('/schedules/range', {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data.schedules || [];
  },

  // Get schedule statistics
  getScheduleStats: async (startDate?: string, endDate?: string): Promise<any> => {
    const response = await api.get('/stats/schedules', {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  },
};
