import React, { useEffect, useState } from 'react';
import { Shield, ShieldOff, AlertCircle, Calendar, Copy, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { apiService } from '../services/api';
import { User } from '../types';

const SettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loadingAction, setLoadingAction] = useState<number | null>(null);

  // Google Calendar state
  const [googleCalStatus, setGoogleCalStatus] = useState<any>(null);
  const [googleCalLoading, setGoogleCalLoading] = useState(false);
  const [googleCalUploading, setGoogleCalUploading] = useState(false);
  const [showGoogleCalInstructions, setShowGoogleCalInstructions] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [googleCalSyncing, setGoogleCalSyncing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const usersData = await apiService.getAllUsers();
      setUsers(usersData);

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

      const result = await apiService.setupGoogleCalendar(serviceAccountKey);
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

  const handleGoogleCalendarDisconnect = async () => {
    if (!window.confirm(t('settings.google_calendar.disconnect_confirm'))) return;

    try {
      await apiService.disconnectGoogleCalendar();
      setSuccess(t('settings.google_calendar.disconnect_success'));
      await loadGoogleCalendarStatus();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(t('settings.save_error'));
      console.error(err);
    }
  };

  const handleCopyCalendarUrl = () => {
    if (googleCalStatus?.public_calendar_url) {
      navigator.clipboard.writeText(googleCalStatus.public_calendar_url);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
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
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{t('settings.title')}</h1>
        <p className="text-gray-600 mt-2">{t('settings.subtitle')}</p>
      </div>

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
          {googleCalStatus && googleCalStatus.is_active ? (
            <>
              <Alert
                type="success"
                message={t('settings.google_calendar.connected')}
              />

              <div className="mt-6 space-y-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    {t('settings.google_calendar.public_url')}
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      readOnly
                      value={googleCalStatus.public_calendar_url}
                      className="flex-1 bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-600 outline-none"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      className="border border-gray-300"
                      onClick={handleCopyCalendarUrl}
                    >
                      {copiedUrl ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                    </Button>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    {t('settings.google_calendar.public_url_hint')}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    {t('settings.google_calendar.service_email')}
                  </label>
                  <p className="text-sm font-mono text-gray-600 bg-gray-50 p-2 rounded border border-gray-200">
                    {googleCalStatus.service_account_email}
                  </p>
                </div>

                {googleCalStatus.last_sync_at && (
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      {t('settings.google_calendar.last_sync')}
                    </label>
                    <p className="text-sm text-gray-600">
                      {new Date(googleCalStatus.last_sync_at).toLocaleString()}
                    </p>
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleGoogleCalendarSync}
                    disabled={googleCalSyncing}
                  >
                    {googleCalSyncing ? t('settings.google_calendar.syncing') : t('settings.google_calendar.sync_now')}
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={handleGoogleCalendarDisconnect}
                  >
                    {t('settings.google_calendar.disconnect')}
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <>
              <Alert
                type="info"
                message={t('settings.google_calendar.not_connected')}
              />

              <div className="mt-6 space-y-4">
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

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    {t('settings.google_calendar.upload_label')}
                  </label>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
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
                      className="cursor-pointer"
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
            </>
          )}
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
    </div>
  );
};

export default SettingsPage;
