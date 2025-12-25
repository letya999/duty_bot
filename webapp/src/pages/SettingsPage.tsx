import React, { useEffect, useState } from 'react';
import { Shield, ShieldOff, Globe } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { apiService } from '../services/api';
import { User } from '../types';

const SettingsPage: React.FC = () => {
  const { t, i18n } = useTranslation();
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
      setError(t('settings.save_error'));
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

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
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

      {/* Language Settings */}
      <Card className="mb-8">
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Globe size={20} className="text-blue-600" />
            {t('settings.language')}
          </h2>
        </CardHeader>
        <CardBody>
          <div className="flex gap-4">
            <Button
              variant={i18n.language === 'en' ? 'primary' : 'secondary'}
              onClick={() => changeLanguage('en')}
              className="flex-1"
            >
              English
            </Button>
            <Button
              variant={i18n.language === 'ru' ? 'primary' : 'secondary'}
              onClick={() => changeLanguage('ru')}
              className="flex-1"
            >
              Русский
            </Button>
          </div>
        </CardBody>
      </Card>

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
