import React, { useEffect, useState } from 'react';
import { Shield, ShieldOff, AlertCircle, Calendar, Copy, Check } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { apiService } from '../services/api';
import { User } from '../types';

const SettingsPage: React.FC = () => {
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
      setError('Failed to load settings');
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
      setSuccess(`${updatedUser.first_name} is now an admin`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to promote user');
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
      setSuccess(`${updatedUser.first_name} is no longer an admin`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to demote user');
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
      setSuccess('Google Calendar connected successfully!');
      await loadGoogleCalendarStatus();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to setup Google Calendar');
      console.error(err);
    } finally {
      setGoogleCalUploading(false);
    }
  };

  const handleGoogleCalendarDisconnect = async () => {
    if (!window.confirm('Disconnect Google Calendar?')) return;

    try {
      await apiService.disconnectGoogleCalendar();
      setSuccess('Google Calendar disconnected');
      await loadGoogleCalendarStatus();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to disconnect Google Calendar');
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
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-2">Manage workspace admins and configuration</p>
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
            Admin Management
          </h2>
        </CardHeader>
        <CardBody>
          {/* Current Admins */}
          <div className="mb-8">
            <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
              Current Admins ({admins.length})
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
                        {admin.first_name} {admin.last_name || ''}
                      </p>
                      <p className="text-sm text-gray-600">@{admin.username}</p>
                    </div>
                    {admin.id !== currentUser?.id && (
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDemote(admin.id)}
                        disabled={loadingAction === admin.id}
                      >
                        <ShieldOff size={16} />
                        Remove Admin
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
                Promote to Admin ({nonAdmins.length})
              </h3>
              <div className="space-y-2">
                {nonAdmins.map(user => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                  >
                    <div>
                      <p className="font-semibold text-gray-900">
                        {user.first_name} {user.last_name || ''}
                      </p>
                      <p className="text-sm text-gray-600">@{user.username}</p>
                    </div>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handlePromote(user.id)}
                      disabled={loadingAction === user.id}
                    >
                      <Shield size={16} />
                      Make Admin
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
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Calendar size={20} className="text-blue-600" />
            Google Calendar Integration
          </h2>
        </CardHeader>
        <CardBody>
          {googleCalLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : googleCalStatus?.is_connected ? (
            <>
              <Alert
                type="success"
                message="✓ Connected to Google Calendar"
              />

              <div className="space-y-4 mt-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Public Calendar URL
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={googleCalStatus.public_calendar_url}
                      readOnly
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                    />
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={handleCopyCalendarUrl}
                    >
                      {copiedUrl ? (
                        <>
                          <Check size={16} />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy size={16} />
                          Copy
                        </>
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Share this URL with team members to subscribe to your duty schedule
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Service Account Email
                  </label>
                  <p className="text-sm text-gray-600">{googleCalStatus.service_account_email}</p>
                </div>

                {googleCalStatus.last_sync_at && (
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Last Sync
                    </label>
                    <p className="text-sm text-gray-600">
                      {new Date(googleCalStatus.last_sync_at).toLocaleString()}
                    </p>
                  </div>
                )}

                <Button
                  variant="danger"
                  size="sm"
                  onClick={handleGoogleCalendarDisconnect}
                >
                  Disconnect Google Calendar
                </Button>
              </div>
            </>
          ) : (
            <>
              <Alert
                type="info"
                message="Not connected. Connect Google Calendar to share your duty schedule with your team."
              />

              <div className="mt-6 space-y-4">
                <button
                  onClick={() => setShowGoogleCalInstructions(!showGoogleCalInstructions)}
                  className="text-blue-600 hover:text-blue-800 font-semibold text-sm flex items-center gap-2"
                >
                  {showGoogleCalInstructions ? '▼' : '▶'} 📘 Setup Instructions
                </button>

                {showGoogleCalInstructions && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-2 text-sm text-gray-700">
                    <ol className="list-decimal list-inside space-y-2">
                      <li>Go to <a href="https://console.cloud.google.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Google Cloud Console</a></li>
                      <li>Create a new project named "Duty Bot"</li>
                      <li>Enable Google Calendar API:
                        <ul className="list-disc list-inside ml-4 mt-1">
                          <li>Search for "Calendar API"</li>
                          <li>Click "Enable"</li>
                        </ul>
                      </li>
                      <li>Create Service Account:
                        <ul className="list-disc list-inside ml-4 mt-1">
                          <li>Go to "Service Accounts" in the left menu</li>
                          <li>Click "Create Service Account"</li>
                          <li>Name: "duty-bot" and complete the form</li>
                        </ul>
                      </li>
                      <li>Create JSON Key:
                        <ul className="list-disc list-inside ml-4 mt-1">
                          <li>Click on the service account you created</li>
                          <li>Go to "Keys" tab</li>
                          <li>Click "Add Key" → "Create new key"</li>
                          <li>Select "JSON" and download the file</li>
                        </ul>
                      </li>
                      <li>Upload the JSON file below</li>
                      <li>Share the Calendar URL with your team members</li>
                    </ol>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Upload Service Account Key (JSON)
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
                        Click to upload or drag and drop
                      </p>
                      <p className="text-xs text-gray-500">
                        JSON files only
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
          <h2 className="text-lg font-semibold text-gray-900">Workspace Settings</h2>
        </CardHeader>
        <CardBody>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              💡 <strong>Note:</strong> Additional workspace settings (work hours, auto-rotation, holidays)
              are configured through the web admin panel at <code className="bg-white px-2 py-1 rounded">/web/settings</code>
            </p>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};

export default SettingsPage;
