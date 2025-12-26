import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, BarChart3 } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { apiService } from '../services/api';
import { User, Schedule } from '../types';

interface ReportFilter {
  startDate: string;
  endDate: string;
  format: 'csv' | 'html' | 'json';
}

interface UserStat {
  user: User | undefined;
  count: number;
}

interface ReportStats {
  totalUsers: number;
  totalDuties: number;
  avgDutiesPerUser: number;
  topUsers: UserStat[];
}

const ReportsPage: React.FC = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [filter, setFilter] = useState<ReportFilter>(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return {
      startDate: d.toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0],
      format: 'csv',
    };
  });

  useEffect(() => {
    loadData();
  }, [filter.startDate, filter.endDate]);

  const loadData = async () => {
    try {
      setLoading(true);
      const allUsers = await apiService.getAllUsers();
      setUsers(allUsers);

      const schedulesData = await apiService.getSchedulesByDateRange(filter.startDate, filter.endDate);
      setSchedules(schedulesData);
    } catch (err) {
      console.error('Failed to load reports', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = () => {
    const params = new URLSearchParams({
      start_date: filter.startDate,
      end_date: filter.endDate,
      format: filter.format,
    });
    window.location.href = `/api/reports/generate?${params.toString()}`;
  };

  const calculateStats = (): ReportStats => {
    const userStatsMap = new Map<number, number>();
    schedules.forEach(s => {
      userStatsMap.set(s.user_id, (userStatsMap.get(s.user_id) || 0) + 1);
    });

    const topUsers = Array.from(userStatsMap.entries())
      .map(([userId, count]) => ({
        user: users.find(u => u.id === userId),
        count,
      }))
      .filter(s => s.user)
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    const totalUsers = users.length;
    const totalDuties = schedules.length;
    const avgDutiesPerUser = totalUsers > 0 ? totalDuties / totalUsers : 0;

    return {
      totalUsers,
      totalDuties,
      avgDutiesPerUser,
      topUsers,
    };
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
        <h1 className="text-3xl font-bold text-gray-900">{t('reports.title')}</h1>
        <p className="text-gray-600 mt-2">{t('reports.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="md:col-span-1">
          <CardHeader>
            <h2 className="text-xl font-semibold">{t('reports.generate_title')}</h2>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('reports.start_date')}</label>
                <Input
                  type="date"
                  value={filter.startDate}
                  onChange={(e) => setFilter({ ...filter, startDate: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('reports.end_date')}</label>
                <Input
                  type="date"
                  value={filter.endDate}
                  onChange={(e) => setFilter({ ...filter, endDate: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('reports.format')}</label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  value={filter.format}
                  onChange={(e) => setFilter({ ...filter, format: e.target.value as any })}
                >
                  <option value="csv">CSV</option>
                  <option value="html">HTML</option>
                  <option value="json">JSON</option>
                </select>
              </div>
              <Button
                variant="primary"
                className="w-full"
                onClick={handleGenerateReport}
              >
                <Download size={18} className="mr-2" />
                {t('reports.generate_btn')}
              </Button>
            </div>
          </CardBody>
        </Card>

        {/* Stats Summary */}
        <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardBody className="flex flex-col items-center justify-center py-8">
              <p className="text-sm text-gray-600 mb-1">{t('reports.stats.total_users')}</p>
              <p className="text-3xl font-bold text-gray-900">{stats.totalUsers}</p>
            </CardBody>
          </Card>
          <Card>
            <CardBody className="flex flex-col items-center justify-center py-8">
              <p className="text-sm text-gray-600 mb-1">{t('reports.stats.total_duties')}</p>
              <p className="text-3xl font-bold text-gray-900">{stats.totalDuties}</p>
            </CardBody>
          </Card>
          <Card>
            <CardBody className="flex flex-col items-center justify-center py-8">
              <p className="text-sm text-gray-600 mb-1">{t('reports.stats.avg_per_user')}</p>
              <p className="text-3xl font-bold text-gray-900">{stats.avgDutiesPerUser.toFixed(1)}</p>
            </CardBody>
          </Card>
        </div>
      </div>

      {/* Top Users */}
      <Card>
        <CardHeader>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <BarChart3 size={20} className="text-blue-600" />
            {t('reports.top_users')}
          </h2>
        </CardHeader>
        <CardBody>
          {stats.topUsers.length === 0 ? (
            <p className="text-gray-500 text-center py-8">{t('reports.no_data')}</p>
          ) : (
            <div className="space-y-4">
              {stats.topUsers.map((stat, idx) => (
                <div key={stat.user?.id}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium text-gray-900">
                      {idx + 1}. {stat.user?.display_name || `${stat.user?.first_name} ${stat.user?.last_name || ''}`}
                    </p>
                    <div className="flex items-center gap-4">
                      <span className="text-sm font-medium text-gray-500">
                        {stat.count} {t('reports.duties_count')}
                      </span>
                      <div className="w-32 h-2 bg-gray-100 rounded-full overflow-hidden hidden sm:block">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{
                            width: `${(stat.count / stats.topUsers[0].count) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
};

export default ReportsPage;
