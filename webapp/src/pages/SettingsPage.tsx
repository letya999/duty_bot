import React, { useEffect, useState } from 'react';
import { Shield, ShieldOff, Calendar, Copy, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { PageLayout, PageHeader } from '../components/ui/PageLayout';
import { apiService } from '../services/api';
import { User, Team } from '../types';

const SettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loadingAction, setLoadingAction] = useState<number | null>(null);

  // Google Calendar state
  const [googleCalStatus, setGoogleCalStatus] = useState<any>(null);
  const [googleCalLoading, setGoogleCalLoading] = useState(false);
  const [googleCalUploading, setGoogleCalUploading] = useState(false);
  const [showGoogleCalInstructions, setShowGoogleCalInstructions] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState<number | null>(null);
  const [googleCalSyncing, setGoogleCalSyncing] = useState(false);
  const [selectedTeamIds, setSelectedTeamIds] = useState<string[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const usersData = await apiService.getAllUsers();
      setUsers(usersData);

      const teamsData = await apiService.getTeams();
      setTeams(teamsData);

      const userData = localStorage.getItem('user');
      if (userData) {
        setCurrentUser(JSON.parse(userData));
      }

      // Load Google Calendar status
      await loadGoogleCalendarStatus();
    } catch (err) {
      setError(t('settings.save_error'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadGoogleCalendarStatus = async () => {
    try {
      setGoogleCalLoading(true);
      const status = await apiService.getGoogleCalendarStatus();
      setGoogleCalStatus(status);
    } catch (err) {
      console.error('Failed to load Google Calendar status', err);
    } finally {
      setGoogleCalLoading(false);
    }
  };

  const handlePromote = async (userId: number) => {
    try {
      setLoadingAction(userId);
      const updatedUser = await apiService.promoteUser(userId);
      setUsers(users.map(u => u.id === userId ? updatedUser : u));
      setSuccess(`${updatedUser.first_name} ${t('settings.make_admin')}`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(t('settings.save_error'));
      console.error(err);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleDemote = async (userId: number) => {
    try {
      setLoadingAction(userId);
      const updatedUser = await apiService.demoteUser(userId);
      setUsers(users.map(u => u.id === userId ? updatedUser : u));
      setSuccess(`${updatedUser.first_name} ${t('settings.remove_admin')}`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(t('settings.save_error'));
      console.error(err);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGoogleCalendarFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setGoogleCalUploading(true);
      const content = await file.text();
      const serviceAccountKey = JSON.parse(content);
      // Convert selected IDs to numbers. If array empty, pass empty array (or handle backend interpretation)
      // Backend: If team_ids provided, use them. If None, Global?
      // Let's assume empty list = Global/All Teams? Or maybe specific "All" option needed.
      // Current UX: "All Teams" was an option. With multi-select, empty -> Global is reasonable OR strict "None".
      // Let's interpret empty -> Global for now, strictly following previous logic "All Teams (Global)".
      // But wait, user might want to select multiple.

      const teamIds = selectedTeamIds.map(id => parseInt(id));
      await apiService.setupGoogleCalendar(serviceAccountKey, teamIds.length > 0 ? teamIds : undefined);
      setSuccess(t('settings.google_calendar.setup_success'));
      await loadGoogleCalendarStatus();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err?.response?.data?.message || t('settings.google_calendar.setup_error'));
      console.error(err);
    } finally {
      setGoogleCalUploading(false);
    }
  };

  const handleGoogleCalendarDisconnect = async (integrationId: number) => {
    if (!window.confirm(t('settings.google_calendar.disconnect_confirm'))) return;

    try {
      await apiService.disconnectGoogleCalendar(integrationId);
      setSuccess(t('settings.google_calendar.disconnect_success'));
      await loadGoogleCalendarStatus();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(t('settings.save_error'));
      console.error(err);
    }
  };

  const handleCopyCalendarUrl = (url: string, id: number) => {
    if (url) {
      navigator.clipboard.writeText(url);
      setCopiedUrl(id);
      setTimeout(() => setCopiedUrl(null), 2000);
    }
  };

  const handleGoogleCalendarSync = async () => {
    try {
      setGoogleCalSyncing(true);
      const result = await apiService.syncGoogleCalendar();
      setSuccess(`${t('settings.google_calendar.sync_success')} (${result.synced_count} ${t('schedules.title').toLowerCase()})`);
      await loadGoogleCalendarStatus();
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      setError(t('settings.google_calendar.sync_error'));
      console.error(err);
    } finally {
      setGoogleCalSyncing(false);
    }
  };


  if (!currentUser?.is_admin) {
    return (
      <div className="p-8">
        <Alert
          type="error"
          message="You do not have permission to access settings. Only admins can manage settings."
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const admins = users.filter(u => u.is_admin);
  const nonAdmins = users.filter(u => !u.is_admin);

  return (
    <PageLayout>
      <PageHeader
        title={t('settings.title')}
        subtitle={t('settings.subtitle')}
      />

      {/* Success Alert */}
      {success && (
        <Alert type="success" message={success} onClose={() => setSuccess(null)} />
      )}

      {/* Error Alert */}
      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}


      {/* Admin Management */}
      <Card className="mb-8">
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Shield size={20} className="text-purple-600" />
            {t('settings.admin_management')}
          </h2>
        </CardHeader>
        <CardBody>
          {/* Current Admins */}
          <div className="mb-8">
            <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
              {t('settings.current_admins')} ({admins.length})
            </h3>
            {admins.length > 0 ? (
              <div className="space-y-2">
                {admins.map(admin => (
                  <div
                    key={admin.id}
                    className="flex items-center justify-between p-4 bg-purple-50 border border-purple-200 rounded-lg"
                  >
                    <div>
                      <p className="font-semibold text-gray-900">
                        {admin.display_name || `${admin.first_name} ${admin.last_name || ''}`}
                      </p>
                      <p className="text-sm text-gray-600">@{admin.username || admin.telegram_username}</p>
                    </div>
                    {admin.id !== currentUser?.id && (
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDemote(admin.id)}
                        disabled={loadingAction === admin.id}
                      >
                        <ShieldOff size={16} />
                        {t('settings.remove_admin')}
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No admins found</p>
            )}
          </div>

          {/* Users to Promote */}
          {nonAdmins.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
                {t('settings.promote_title')} ({nonAdmins.length})
              </h3>
              <div className="space-y-2">
                {nonAdmins.map(user => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                  >
                    <div>
                      <p className="font-semibold text-gray-900">
                        {user.display_name || `${user.first_name} ${user.last_name || ''}`}
                      </p>
                      <p className="text-sm text-gray-600">@{user.username || user.telegram_username}</p>
                    </div>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handlePromote(user.id)}
                      disabled={loadingAction === user.id}
                    >
                      <Shield size={16} />
                      {t('settings.make_admin')}
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Google Calendar Integration */}
      <Card className="mb-8">
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900">{t('settings.google_calendar.title')}</h2>
          </div>
          {googleCalLoading && <LoadingSpinner size="sm" />}
        </CardHeader>
        <CardBody>
          {googleCalStatus && googleCalStatus.integrations && googleCalStatus.integrations.length > 0 ? (
            <div className="space-y-8">
              {googleCalStatus.integrations.map((integration: any) => (
                <div key={integration.id} className="border border-gray-200 rounded-lg p-6 bg-gray-50">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-bold text-lg text-gray-800 flex items-center gap-2">
                        {integration.team_name || "All Teams"}
                        {integration.is_active && <span className="text-green-600 text-xs bg-green-100 px-2 py-0.5 rounded-full">Active</span>}
                      </h3>
                      <p className="text-sm text-gray-500">Service Email: {integration.service_account_email}</p>
                    </div>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleGoogleCalendarDisconnect(integration.id)}
                    >
                      {t('settings.google_calendar.disconnect')}
                    </Button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        {t('settings.google_calendar.public_url')}
                      </label>
                      <div className="flex gap-2">
                        <Input
                          readOnly
                          value={integration.public_calendar_url}
                          className="flex-1 bg-white text-gray-600"
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          className="border border-gray-300 bg-white"
                          onClick={() => handleCopyCalendarUrl(integration.public_calendar_url, integration.id)}
                        >
                          {copiedUrl === integration.id ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                        </Button>
                      </div>
                    </div>

                    {integration.last_sync_at && (
                      <div className="text-sm text-gray-600">
                        <strong>{t('settings.google_calendar.last_sync')}:</strong> {new Date(integration.last_sync_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              <div className="flex gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleGoogleCalendarSync}
                  disabled={googleCalSyncing}
                >
                  {googleCalSyncing ? t('settings.google_calendar.syncing') : t('settings.google_calendar.sync_now')}
                </Button>
              </div>
            </div>
          ) : (
            <Alert
              type="info"
              message={t('settings.google_calendar.not_connected')}
            />
          )}

          {/* Add New Calendar Section */}
          <div className="mt-8 border-t border-gray-200 pt-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              {googleCalStatus && googleCalStatus.integrations && googleCalStatus.integrations.length > 0
                ? "Add Another Calendar"
                : "Setup Google Calendar"}
            </h3>

            <div className="space-y-4">
              <button
                onClick={() => setShowGoogleCalInstructions(!showGoogleCalInstructions)}
                className="text-blue-600 hover:text-blue-800 font-semibold text-sm flex items-center gap-2"
              >
                {showGoogleCalInstructions ? '▼' : '▶'} 📘 {t('settings.google_calendar.setup_instructions')}
              </button>

              {showGoogleCalInstructions && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-2 text-sm text-gray-700">
                  <ol className="list-decimal list-inside space-y-2">
                    <li>{t('settings.google_calendar.step_1')} <a href="https://console.cloud.google.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{t('settings.google_calendar.step_1_link')}</a></li>
                    <li>{t('settings.google_calendar.step_2')}</li>
                    <li>{t('settings.google_calendar.step_3')}</li>
                    <li>{t('settings.google_calendar.step_4')}
                      <ul className="list-disc list-inside ml-4 mt-1">
                        <li>{t('settings.google_calendar.step_4_1')}</li>
                        <li>{t('settings.google_calendar.step_4_2')}</li>
                      </ul>
                    </li>
                    <li>{t('settings.google_calendar.step_5')}
                      <ul className="list-disc list-inside ml-4 mt-1">
                        <li>{t('settings.google_calendar.step_5_1')}</li>
                        <li>{t('settings.google_calendar.step_5_2')}</li>
                        <li>{t('settings.google_calendar.step_5_3')}</li>
                        <li>{t('settings.google_calendar.step_5_4')}</li>
                      </ul>
                    </li>
                    <li>{t('settings.google_calendar.step_6')}</li>
                  </ol>
                </div>
              )}

              {/* Team Selection */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Select Teams
                </label>
                <div className="border border-gray-300 rounded-lg p-2 max-h-48 overflow-y-auto bg-white">
                  <div className="flex items-center p-2 hover:bg-gray-50 rounded">
                    <input
                      type="checkbox"
                      className="mr-2"
                      checked={selectedTeamIds.length === 0}
                      onChange={() => setSelectedTeamIds([])}
                    />
                    <span className="text-sm text-gray-700 font-medium">All Teams (Global)</span>
                  </div>
                  {teams.map(team => (
                    <div key={team.id} className="flex items-center p-2 hover:bg-gray-50 rounded">
                      <input
                        type="checkbox"
                        className="mr-2"
                        checked={selectedTeamIds.includes(String(team.id))}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedTeamIds([...selectedTeamIds, String(team.id)]);
                          } else {
                            setSelectedTeamIds(selectedTeamIds.filter(id => id !== String(team.id)));
                          }
                        }}
                      />
                      <span className="text-sm text-gray-700">{team.display_name}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Select teams for this calendar. Select "All Teams" (or uncheck specific teams) to make it global.
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  {t('settings.google_calendar.upload_label')}
                </label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:bg-gray-50 transition-colors">
                  <input
                    type="file"
                    accept=".json"
                    onChange={handleGoogleCalendarFileUpload}
                    disabled={googleCalUploading}
                    className="hidden"
                    id="google-key-upload"
                  />
                  <label
                    htmlFor="google-key-upload"
                    className="cursor-pointer block w-full h-full"
                  >
                    <p className="text-sm text-gray-600 mb-2">
                      {t('settings.google_calendar.upload_hint')}
                    </p>
                    <p className="text-xs text-gray-500">
                      {t('settings.google_calendar.json_only')}
                    </p>
                    {googleCalUploading && (
                      <div className="mt-2 flex justify-center">
                        <LoadingSpinner size="sm" />
                      </div>
                    )}
                  </label>
                </div>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Workspace Settings */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">{t('settings.workspace_settings')}</h2>
        </CardHeader>
        <CardBody>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              💡 <strong>{t('settings.note')}:</strong> {t('settings.note_details')}
            </p>
          </div>
        </CardBody>
      </Card>
    </PageLayout>
  );
};

export default SettingsPage;
