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

  // Update user information
  updateUser: async (userId: number, data: { display_name?: string; first_name?: string; last_name?: string }): Promise<User> => {
    const response = await api.put(`/users/${userId}`, data);
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

  // Assign multiple duties for date range
  assignBulkDuties: async (userIds: number[], startDate: string, endDate: string, teamId?: number): Promise<any> => {
    const response = await api.post('/schedule/assign-bulk', {
      user_ids: userIds,
      start_date: startDate,
      end_date: endDate,
      team_id: teamId,
    });
    return response.data;
  },

  // Edit duty assignment
  editDuty: async (scheduleId: number, userId: number, dutyDate: string, teamId?: number): Promise<any> => {
    const response = await api.put(`/schedule/${scheduleId}`, {
      user_id: userId,
      duty_date: dutyDate,
      team_id: teamId,
    });
    return response.data;
  },

  // Get teams with details
  getTeamsWithDetails: async (): Promise<Team[]> => {
    const response = await api.get('/teams/details');
    return response.data;
  },

  // Create team
  createTeam: async (data: { name: string; display_name: string; has_shifts?: boolean; team_lead_id?: number }): Promise<any> => {
    const response = await api.post('/teams', data);
    return response.data;
  },

  // Update team
  updateTeam: async (teamId: number, data: any): Promise<any> => {
    const response = await api.put(`/teams/${teamId}`, data);
    return response.data;
  },

  // Delete team
  deleteTeam: async (teamId: number): Promise<any> => {
    const response = await api.delete(`/teams/${teamId}`);
    return response.data;
  },

  // Add team member
  addTeamMember: async (teamId: number, userId: number): Promise<any> => {
    const response = await api.post(`/teams/${teamId}/members`, { user_id: userId });
    return response.data;
  },

  // Remove team member
  removeTeamMember: async (teamId: number, userId: number): Promise<any> => {
    const response = await api.delete(`/teams/${teamId}/members/${userId}`);
    return response.data;
  },

  // Import team member by handle
  importTeamMember: async (teamId: number, handle: string): Promise<any> => {
    const response = await api.post(`/teams/${teamId}/members/import`, { handle });
    return response.data;
  },

  // Move team member
  moveTeamMember: async (userId: number, fromTeamId: number, toTeamId: number): Promise<any> => {
    const response = await api.post('/teams/members/move', {
      user_id: userId,
      from_team_id: fromTeamId,
      to_team_id: toTeamId
    });
    return response.data;
  },

  // Get escalations
  getEscalations: async (teamId?: number): Promise<any> => {
    const response = await api.get('/escalations', {
      params: { team_id: teamId },
    });
    return response.data;
  },

  // Create escalation
  createEscalation: async (data: { team_id?: number; cto_id: number }): Promise<any> => {
    const response = await api.post('/escalations', data);
    return response.data;
  },

  // Delete escalation
  deleteEscalation: async (escalationId: number): Promise<any> => {
    const response = await api.delete(`/escalations/${escalationId}`);
    return response.data;
  },

  // Move duty to different date
  moveDuty: async (scheduleId: number, newDate: string): Promise<any> => {
    const response = await api.patch(`/schedule/${scheduleId}/move`, { new_date: newDate });
    return response.data;
  },

  // Replace person in duty
  replaceDutyUser: async (scheduleId: number, newUserId: number): Promise<any> => {
    const response = await api.patch(`/schedule/${scheduleId}/replace`, { user_id: newUserId });
    return response.data;
  },


  // Incidents
  createIncident: async (workspaceId: number, name: string): Promise<any> => {
    const response = await api.post(`/workspaces/${workspaceId}/incidents`, { name });
    return response.data;
  },

  getIncidents: async (workspaceId: number, status?: string): Promise<any> => {
    const response = await api.get(`/workspaces/${workspaceId}/incidents`, {
      params: { status },
    });
    return response.data;
  },

  getIncident: async (workspaceId: number, incidentId: number): Promise<any> => {
    const response = await api.get(`/workspaces/${workspaceId}/incidents/${incidentId}`);
    return response.data;
  },

  completeIncident: async (workspaceId: number, incidentId: number): Promise<any> => {
    const response = await api.patch(`/workspaces/${workspaceId}/incidents/${incidentId}/complete`);
    return response.data;
  },

  deleteIncident: async (workspaceId: number, incidentId: number): Promise<any> => {
    const response = await api.delete(`/workspaces/${workspaceId}/incidents/${incidentId}`);
    return response.data;
  },

  getActiveIncidents: async (workspaceId: number): Promise<any> => {
    const response = await api.get(`/workspaces/${workspaceId}/incidents`, {
      params: { status: 'active' },
    });
    return response.data;
  },

  getMetrics: async (workspaceId: number, period: string = 'week'): Promise<any> => {
    const response = await api.get(`/workspaces/${workspaceId}/incidents/metrics/summary`, {
      params: { period },
    });
    return response.data;
  },

  // Google Calendar Integration
  getGoogleCalendarStatus: async (): Promise<any> => {
    const response = await api.get('/settings/google-calendar/status');
    return response.data;
  },

  setupGoogleCalendar: async (serviceAccountKey: Record<string, any>): Promise<any> => {
    const response = await api.post('/settings/google-calendar/setup', {
      service_account_key: serviceAccountKey,
    });
    return response.data;
  },

  disconnectGoogleCalendar: async (): Promise<any> => {
    const response = await api.delete('/settings/google-calendar');
    return response.data;
  },

  getGoogleCalendarUrl: async (): Promise<any> => {
    const response = await api.get('/settings/google-calendar/url');
    return response.data;
  },
};
