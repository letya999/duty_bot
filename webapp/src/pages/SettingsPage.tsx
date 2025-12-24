import React, { useEffect, useState } from 'react';
import { Shield, ShieldOff, AlertCircle } from 'lucide-react';
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
    } catch (err) {
      setError('Failed to load settings');
      console.error(err);
    } finally {
      setLoading(false);
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
