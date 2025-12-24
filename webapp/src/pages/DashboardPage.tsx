import React, { useEffect, useState } from 'react';
import { Users, Calendar, TrendingUp, AlertCircle } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { apiService } from '../services/api';
import { Team, User, Schedule } from '../types';

const DashboardPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [todaySchedules, setTodaySchedules] = useState<Schedule[]>([]);

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

        // Get today's schedule
        const today = new Date().toISOString().split('T')[0];
        const dailySchedule = await apiService.getDailySchedule(today);
        setTodaySchedules(dailySchedule.duties);
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
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">Welcome to Duty Bot Admin Panel</p>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert type="error" message={error} />
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Users className="text-blue-600" size={24} />
            </div>
            <div>
              <p className="text-gray-600 text-sm">Total Users</p>
              <p className="text-2xl font-bold text-gray-900">{users.length}</p>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <Calendar className="text-green-600" size={24} />
            </div>
            <div>
              <p className="text-gray-600 text-sm">Teams</p>
              <p className="text-2xl font-bold text-gray-900">{teams.length}</p>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <TrendingUp className="text-purple-600" size={24} />
            </div>
            <div>
              <p className="text-gray-600 text-sm">Today's Duties</p>
              <p className="text-2xl font-bold text-gray-900">{todaySchedules.length}</p>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 bg-orange-100 rounded-lg">
              <AlertCircle className="text-orange-600" size={24} />
            </div>
            <div>
              <p className="text-gray-600 text-sm">Admins</p>
              <p className="text-2xl font-bold text-gray-900">{users.filter(u => u.is_admin).length}</p>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Today's Duties */}
      <Card className="mb-8">
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">Today's Duties</h2>
        </CardHeader>
        <CardBody>
          {todaySchedules.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">User</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Team</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {todaySchedules.map((schedule) => (
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
            <p className="text-gray-500 text-center py-8">No duties scheduled for today</p>
          )}
        </CardBody>
      </Card>

      {/* Teams Overview */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">Teams</h2>
        </CardHeader>
        <CardBody>
          {teams.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {teams.map((team) => (
                <div key={team.id} className="p-4 border border-gray-200 rounded-lg hover:border-blue-400 transition-colors">
                  <h3 className="font-semibold text-gray-900 mb-2">{team.name}</h3>
                  <p className="text-sm text-gray-600 mb-3">{team.description}</p>
                  <p className="text-sm text-gray-500">
                    <strong>{team.members?.length || 0}</strong> members
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No teams created yet</p>
          )}
        </CardBody>
      </Card>
    </div>
  );
};

export default DashboardPage;
