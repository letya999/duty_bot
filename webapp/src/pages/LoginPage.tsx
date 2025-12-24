import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Loader } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Alert } from '../components/ui/Alert';
import TelegramLoginWidget from '../components/TelegramLoginWidget';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [botUsername, setBotUsername] = useState<string>('');

  // Get bot username from environment or config
  useEffect(() => {
    const username = import.meta.env.VITE_TELEGRAM_BOT_USERNAME || 'test_duty_999_bot';
    console.log('Current Bot Username (from env):', username);
    setBotUsername(username);
  }, []);

  const handleTelegramAuth = async (data: any) => {
    try {
      setLoading(true);
      setError(null);

      // Send auth data to backend
      const response = await fetch('/web/auth/telegram-widget-callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Authentication failed');
      }

      const result = await response.json();

      // Store session token and user data
      localStorage.setItem('session_token', result.session_token);
      localStorage.setItem('user', JSON.stringify(result.user));

      // Redirect to dashboard
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      setLoading(false);
    }
  };

  const handleSlackLogin = () => {
    setLoading(true);
    // Redirect to Slack login endpoint
    window.location.href = '/web/auth/slack-login';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-lg shadow-2xl p-8">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900">🎯</h1>
          <h2 className="text-2xl font-bold text-gray-900 mt-4">Duty Bot</h2>
          <p className="text-gray-600 mt-2">Admin Panel</p>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert
            type="error"
            message={error}
            onClose={() => setError(null)}
          />
        )}

        {/* Login Options */}
        <div className="space-y-6 mt-8">
          {/* Telegram Login Widget */}
          <div>
            <p className="text-center text-sm text-gray-600 mb-3">Login with Telegram</p>
            {botUsername && (
              <TelegramLoginWidget
                botUsername={botUsername}
                onAuth={handleTelegramAuth}
                buttonSize="large"
                usePic={true}
              />
            )}
          </div>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-600">or</span>
            </div>
          </div>

          {/* Slack Login */}
          <div>
            <button
              onClick={handleSlackLogin}
              disabled={loading}
              className="w-full bg-blue-400 hover:bg-blue-500 disabled:bg-blue-300 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader className="animate-spin" size={20} />
                  Redirecting...
                </>
              ) : (
                <>
                  ⚡ Login with Slack
                </>
              )}
            </button>
          </div>
        </div>

        {/* Info Section */}
        <div className="mt-8 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-600">
            <strong>Note:</strong> You will be redirected to authenticate with your chosen platform.
            Make sure you have the necessary credentials configured by your administrator.
          </p>
        </div>

        {/* Footer */}
        <div className="mt-8 pt-6 border-t border-gray-200 text-center text-sm text-gray-500">
          <p>Need help? Contact your workspace administrator.</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
