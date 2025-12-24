import React, { useState, useEffect, useCallback } from 'react';
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

  const handleTelegramAuth = useCallback(async (data: any) => {
    try {
      console.log('🔵 [LoginPage] handleTelegramAuth called');
      console.log('🔵 [LoginPage] Data received from widget:', data);
      console.log('🔵 [LoginPage] Data type:', typeof data);
      console.log('🔵 [LoginPage] Data keys:', Object.keys(data || {}));
      console.log('🔵 [LoginPage] Has id?', !!data?.id);
      console.log('🔵 [LoginPage] Has hash?', !!data?.hash);
      console.log('🔵 [LoginPage] Has auth_date?', !!data?.auth_date);

      setLoading(true);
      setError(null);

      // Log before fetch
      const requestUrl = '/web/auth/telegram-widget-callback';
      const requestBody = JSON.stringify(data);
      console.log('🔵 [LoginPage] About to fetch:', requestUrl);
      console.log('🔵 [LoginPage] Request method: POST');
      console.log('🔵 [LoginPage] Request headers: { Content-Type: application/json }');
      console.log('🔵 [LoginPage] Request body:', requestBody);

      // Send auth data to backend
      const response = await fetch(requestUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: requestBody,
      });

      console.log('✅ [LoginPage] Fetch completed');
      console.log('✅ [LoginPage] Response status:', response.status);
      console.log('✅ [LoginPage] Response statusText:', response.statusText);
      console.log('✅ [LoginPage] Response OK?', response.ok);
      console.log('✅ [LoginPage] Response headers:');
      response.headers.forEach((value, key) => {
        console.log(`  ${key}: ${value}`);
      });

      if (!response.ok) {
        console.error('❌ [LoginPage] Response not OK, parsing error data');
        const errorData = await response.json();
        console.error('❌ [LoginPage] Error response:', errorData);
        throw new Error(errorData.detail || 'Authentication failed');
      }

      const result = await response.json();
      console.log('✅ [LoginPage] Response body parsed:', result);
      console.log('✅ [LoginPage] Session token:', result.session_token ? '✓ Present' : '✗ Missing');
      console.log('✅ [LoginPage] User data:', result.user);

      // Store session token and user data
      localStorage.setItem('session_token', result.session_token);
      localStorage.setItem('user', JSON.stringify(result.user));
      console.log('✅ [LoginPage] Stored session_token and user in localStorage');

      // Redirect to dashboard
      console.log('✅ [LoginPage] Auth success! Redirecting to dashboard...');
      navigate('/');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      console.error('❌ [LoginPage] Error in handleTelegramAuth:', errorMessage);
      console.error('❌ [LoginPage] Full error:', err);
      setError(errorMessage);
      setLoading(false);
    }
  }, [navigate]);

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
