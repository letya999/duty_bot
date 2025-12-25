import React, { useEffect, useState } from 'react';
import { Download, BarChart3 } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { apiService } from '../services/api';
import { User, Schedule } from '../types';

const ReportsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [format, setFormat] = useState<'csv' | 'html' | 'json'>('csv');

  useEffect(() => {
    loadData();
  }, [startDate, endDate]);

  const loadData = async () => {
    try {
      setLoading(true);
      const allUsers = await apiService.getAllUsers();
      setUsers(allUsers);

      // Load schedules for the default date range
      const schedulesData = await apiService.getSchedulesByDateRange(startDate, endDate);
      setSchedules(schedulesData);
    } catch (err) {
      console.error('Failed to load reports', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = () => {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
      format: format,
    });
    window.location.href = `/web/reports/generate?${params.toString()}`;
  };

  const calculateStats = () => {
    const userStats = new Map<number, number>();
    schedules.forEach(s => {
      userStats.set(s.user_id, (userStats.get(s.user_id) || 0) + 1);
    });

    return Array.from(userStats.entries())
      .map(([userId, count]) => ({
        user: users.find(u => u.id === userId),
        count,
      }))
      .filter(s => s.user)
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  };

  const stats = calculateStats();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Reports & Analytics</h1>
        <p className="text-gray-600 mt-2">Generate and export duty reports</p>
      </div>

      {/* Report Generator */}
      <Card className="mb-8">
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Download size={20} />
            Generate Report
          </h2>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Format
              </label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value as 'csv' | 'html' | 'json')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="csv">CSV</option>
                <option value="html">HTML</option>
                <option value="json">JSON</option>
              </select>
            </div>

            <div className="flex items-end">
              <Button
                variant="primary"
                onClick={handleGenerateReport}
                className="w-full"
              >
                <Download size={18} />
                Generate Report
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardBody className="text-center">
            <p className="text-gray-600 text-sm mb-2">Total Users</p>
            <p className="text-3xl font-bold text-gray-900">{users.length}</p>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="text-center">
            <p className="text-gray-600 text-sm mb-2">Total Duties</p>
            <p className="text-3xl font-bold text-gray-900">{schedules.length}</p>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="text-center">
            <p className="text-gray-600 text-sm mb-2">Avg Duties per User</p>
            <p className="text-3xl font-bold text-gray-900">
              {users.length > 0 ? (schedules.length / users.length).toFixed(1) : 0}
            </p>
          </CardBody>
        </Card>
      </div>

      {/* Top Users */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <BarChart3 size={20} />
            Top Users by Duty Count
          </h2>
        </CardHeader>
        <CardBody>
          {stats.length > 0 ? (
            <div className="space-y-4">
              {stats.map((stat, idx) => (
                <div key={stat.user?.id}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium text-gray-900">
                      {idx + 1}. {stat.user?.display_name || `${stat.user?.first_name} ${stat.user?.last_name || ''}`}
                    </p>
                    <span className="text-sm font-semibold text-blue-600">
                      {stat.count} duties
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{
                        width: `${(stat.count / stats[0].count) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No duty data available</p>
          )}
        </CardBody>
      </Card>
    </div>
  );
};

export default ReportsPage;
