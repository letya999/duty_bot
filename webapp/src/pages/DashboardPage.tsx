import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Icons } from '../components/ui/Icons';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { apiService } from '../services/api';
import { Team, User, Schedule } from '../types';

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [upcomingSchedules, setUpcomingSchedules] = useState<Schedule[]>([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [teamsData, usersData] = await Promise.all([
          apiService.getTeams(),
          apiService.getAllUsers(),
        ]);

        setTeams(teamsData);
        setUsers(usersData);

        // Get upcoming schedules (next 7 days)
        const today = new Date();
        const nextWeek = new Date(today);
        nextWeek.setDate(today.getDate() + 7);

        const startDate = today.toISOString().split('T')[0];
        const endDate = nextWeek.toISOString().split('T')[0];

        const schedules = await apiService.getSchedulesByDateRange(startDate, endDate);
        setUpcomingSchedules(schedules);
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{t('dashboard.title')}</h1>
        <p className="text-gray-600 mt-2">{t('dashboard.welcome')}</p>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert type="error" message={error} />
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 bg-info-light rounded-lg">
              <Icons.Users className="text-info" size={24} />
            </div>
            <div>
              <p className="text-text-muted text-sm">{t('dashboard.stats.total_users')}</p>
              <p className="text-2xl font-bold text-gray-900">{users.length}</p>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 bg-success-light rounded-lg">
              <Icons.Calendar className="text-success" size={24} />
            </div>
            <div>
              <p className="text-text-muted text-sm">{t('dashboard.stats.teams')}</p>
              <p className="text-2xl font-bold text-gray-900">{teams.length}</p>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 bg-primary/10 rounded-lg">
              <Icons.TrendingUp className="text-primary" size={24} />
            </div>
            <div>
              <p className="text-text-muted text-sm">{t('dashboard.stats.upcoming_duties')}</p>
              <p className="text-2xl font-bold text-gray-900">{upcomingSchedules.length}</p>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 bg-warning-light rounded-lg">
              <Icons.AlertCircle className="text-warning" size={24} />
            </div>
            <div>
              <p className="text-text-muted text-sm">{t('dashboard.stats.admins')}</p>
              <p className="text-2xl font-bold text-gray-900">{users.filter(u => u.is_admin).length}</p>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Upcoming Duties */}
      <Card className="mb-8">
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">{t('dashboard.upcoming.title')}</h2>
        </CardHeader>
        <CardBody>
          {upcomingSchedules.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">{t('dashboard.upcoming.user')}</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">{t('dashboard.upcoming.team')}</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">{t('dashboard.upcoming.date')}</th>
                  </tr>
                </thead>
                <tbody>
                  {upcomingSchedules.map((schedule) => (
                    <tr key={schedule.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-900">{schedule.user.first_name} {schedule.user.last_name || ''}</td>
                      <td className="py-3 px-4 text-gray-600">{schedule.team?.name || 'N/A'}</td>
                      <td className="py-3 px-4 text-gray-600">{schedule.duty_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">{t('dashboard.upcoming.no_duties')}</p>
          )}
        </CardBody>
      </Card>

      {/* Teams Overview */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">{t('dashboard.teams.title')}</h2>
        </CardHeader>
        <CardBody>
          {teams.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {teams.map((team) => (
                <div key={team.id} className="p-4 border border-gray-200 rounded-lg hover:border-blue-400 transition-colors">
                  <h3 className="font-semibold text-gray-900 mb-2">{team.name}</h3>
                  <p className="text-sm text-gray-600 mb-3">{team.description}</p>
                  <p className="text-sm text-gray-500">
                    <strong>{team.members?.length || 0}</strong> {t('dashboard.teams.members')}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">{t('dashboard.teams.no_teams')}</p>
          )}
        </CardBody>
      </Card>
    </div>
  );
};

export default DashboardPage;
