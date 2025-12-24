import axios from 'axios';
import { MonthSchedule, DailySchedule, Team, User } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/miniapp';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add Telegram init data to all requests
api.interceptors.request.use((config) => {
  const initData = window.Telegram?.WebApp?.initData;
  if (initData) {
    config.headers['X-Telegram-Init-Data'] = initData;
  }
  return config;
});

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
  assignDuty: async (teamId: number, userId: number, date: string): Promise<any> => {
    const response = await api.post('/schedule/assign', {
      team_id: teamId,
      user_id: userId,
      date,
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
};
