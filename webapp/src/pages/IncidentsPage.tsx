import React, { useEffect, useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { Icons } from '../components/ui/Icons';
import { apiService } from '../services/api';

interface Incident {
  id: number;
  name: string;
  status: 'active' | 'resolved';
  start_time: string;
  end_time: string | null;
  created_at: string;
  updated_at: string;
}

interface Metrics {
  mtr: number;
  daysWithoutIncidents: number;
  totalIncidents: number;
  averageIncidentDuration: number;
  period: string;
  startTime: string;
  endTime: string;
}

const IncidentsPage: React.FC = () => {
  const { t } = useTranslation();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [incidentName, setIncidentName] = useState('');
  const [activeIncidents, setActiveIncidents] = useState<Incident[]>([]);
  const [period, setPeriod] = useState<'week' | 'month' | 'quarter' | 'year'>('week');
  const [updateTimestamp, setUpdateTimestamp] = useState(0);

  useEffect(() => {
    loadData();
    // Polling every 30 seconds instead of 5 (6x reduction in API calls)
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [period]);

  useEffect(() => {
    // Only update duration display every second if there are active incidents
    // Using a single timer for all incidents instead of one timer per incident
    if (activeIncidents.length === 0) return;

    const timer = setInterval(() => {
      setUpdateTimestamp(Date.now());
    }, 1000);

    return () => clearInterval(timer);
  }, [activeIncidents.length > 0]);

  const loadData = async () => {
    try {
      setLoading(true);
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      const workspaceId = user.workspace_id;

      if (!workspaceId) {
        console.warn('No workspace ID found in user session');
        setLoading(false);
        return;
      }

      const [incidentsData, metricsData, activeData] = await Promise.all([
        apiService.getIncidents(workspaceId),
        apiService.getMetrics(workspaceId, period),
        apiService.getActiveIncidents(workspaceId),
      ]);

      setIncidents(incidentsData);
      setMetrics(metricsData);
      setActiveIncidents(activeData);
    } catch (err) {
      setError(t('incidents.errors.load_failed'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateIncident = async () => {
    if (!incidentName.trim()) {
      setError(t('incidents.errors.name_required'));
      return;
    }

    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      const workspaceId = user.workspace_id;

      if (!workspaceId) {
        setError(t('incidents.errors.no_workspace'));
        return;
      }

      await apiService.createIncident(workspaceId, incidentName);
      setIncidentName('');
      setError(null);
      await loadData();
    } catch (err) {
      setError(t('incidents.errors.create_failed'));
      console.error(err);
    }
  };


  const handleCompleteIncident = async (incidentId: number) => {
    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      const workspaceId = user.workspace_id;

      if (!workspaceId) {
        setError(t('incidents.errors.no_workspace'));
        return;
      }

      await apiService.completeIncident(workspaceId, incidentId);
      await loadData();
    } catch (err) {
      setError(t('incidents.errors.complete_failed'));
      console.error(err);
    }
  };

  const formatDuration = (startTime: string, endTime: string | null) => {
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const durationMs = end.getTime() - start.getTime();
    const hours = Math.floor(durationMs / 3600000);
    const minutes = Math.floor((durationMs % 3600000) / 60000);
    const seconds = Math.floor((durationMs % 60000) / 1000);

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  };

  const formatTime = (timeStr: string) => {
    const date = new Date(timeStr);
    return date.toLocaleString();
  };

  const formatMetricTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  if (loading && !incidents.length) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">{t('incidents.title')}</h1>

      {error && <Alert type="error" message={error} />}

      {/* Quick Start Section */}
      <Card className="mb-8">
        <CardHeader>
          <h2 className="text-xl font-semibold">{t('incidents.start_new')}</h2>
        </CardHeader>
        <CardBody>
          <div className="flex gap-4">
            <Input
              type="text"
              placeholder={t('incidents.name_placeholder')}
              value={incidentName}
              onChange={(e) => setIncidentName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleCreateIncident()}
            />
            <Button onClick={handleCreateIncident} variant="primary">
              <Icons.Plus size={20} className="mr-2" />
              {t('incidents.start_btn')}
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Metrics Section */}
      {metrics && (
        <div className="mb-8">
          <div className="flex gap-4 mb-4">
            {(['week', 'month', 'quarter', 'year'] as const).map((p) => (
              <Button
                key={p}
                onClick={() => setPeriod(p)}
                variant={period === p ? 'primary' : 'secondary'}
              >
                {t(`schedules.${p}`, { defaultValue: p.charAt(0).toUpperCase() + p.slice(1) })}
              </Button>
            ))}
          </div>

          <div className="grid grid-cols-4 gap-4">
            <Card>
              <CardBody>
                <div className="text-gray-600 text-sm mb-2">{t('incidents.mtr')}</div>
                <div className="text-2xl font-bold">{formatMetricTime(metrics.mtr)}</div>
              </CardBody>
            </Card>
            <Card>
              <CardBody>
                <div className="text-gray-600 text-sm mb-2">{t('incidents.days_without')}</div>
                <div className="text-2xl font-bold">{metrics.daysWithoutIncidents}</div>
              </CardBody>
            </Card>
            <Card>
              <CardBody>
                <div className="text-gray-600 text-sm mb-2">{t('incidents.total_incidents')}</div>
                <div className="text-2xl font-bold">{metrics.totalIncidents}</div>
              </CardBody>
            </Card>
            <Card>
              <CardBody>
                <div className="text-gray-600 text-sm mb-2">{t('incidents.avg_duration')}</div>
                <div className="text-2xl font-bold">{formatMetricTime(metrics.averageIncidentDuration)}</div>
              </CardBody>
            </Card>
          </div>
        </div>
      )}

      {/* Active Incidents */}
      {activeIncidents.length > 0 && (
        <Card className="mb-8">
          <CardHeader>
            <h2 className="text-xl font-semibold">
              {t('incidents.active_incidents')} ({activeIncidents.length})
            </h2>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              {activeIncidents.map((incident) => (
                <div key={incident.id} className="flex items-center justify-between p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div>
                    <div className="font-semibold">{incident.name}</div>
                    <div className="text-sm text-gray-600">
                      Started: {formatTime(incident.start_time)} •{' '}
                      Duration: {formatDuration(incident.start_time, incident.end_time)}
                    </div>
                  </div>
                  <Button
                    onClick={() => handleCompleteIncident(incident.id)}
                    variant="primary"
                  >
                    <Icons.Check size={20} className="mr-2" />
                    {t('incidents.complete_btn')}
                  </Button>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {/* All Incidents */}
      <Card>
        <CardHeader>
          <h2 className="text-xl font-semibold">{t('incidents.all_incidents')}</h2>
        </CardHeader>
        <CardBody>
          {incidents.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              {t('incidents.no_incidents')}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 font-semibold">{t('incidents.table.name')}</th>
                    <th className="text-left py-3 px-4 font-semibold">{t('incidents.table.status')}</th>
                    <th className="text-left py-3 px-4 font-semibold">{t('incidents.table.duration')}</th>
                    <th className="text-left py-3 px-4 font-semibold">{t('incidents.table.started')}</th>
                    <th className="text-left py-3 px-4 font-semibold">{t('incidents.table.ended')}</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((incident) => (
                    <tr key={incident.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4">{incident.name}</td>
                      <td className="py-3 px-4">
                        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${incident.status === 'active'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-green-100 text-green-800'
                          }`}>
                          {incident.status === 'active' ? t('incidents.table.active') : t('incidents.table.resolved')}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {formatDuration(incident.start_time, incident.end_time)}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {formatTime(incident.start_time)}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {incident.end_time ? formatTime(incident.end_time) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
};

export default IncidentsPage;
