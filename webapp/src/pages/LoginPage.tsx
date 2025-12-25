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

  const handleProgrammaticLogin = () => {
    if (!window.Telegram?.Login) {
      setError("Telegram script not loaded yet. Please wait a moment.");
      return;
    }

    const botId = parseInt(import.meta.env.VITE_TELEGRAM_BOT_ID || '8527825927');
    console.log('🔵 [LoginPage] Triggering Method B (Programmatic API) with bot_id:', botId);
    window.Telegram.Login.auth(
      { bot_id: botId, request_access: true },
      (user: any) => {
        if (user) {
          console.log('✅ [LoginPage] Method B Authorization success:', user);
          handleTelegramAuth(user);
        } else {
          console.log('❌ [LoginPage] Method B Authorization cancelled or failed');
        }
      }
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center px-4">
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
          {/* Telegram Login */}
          <div>
            <Button
              onClick={handleProgrammaticLogin}
              className="w-full bg-[#54a9eb] hover:bg-[#4397d7] text-white py-3 h-auto"
              disabled={loading}
            >
              <div className="flex flex-col items-center">
                {loading ? (
                  <Loader className="animate-spin" size={24} />
                ) : (
                  <>
                    <span className="text-lg font-bold">✈️ Login with Telegram</span>
                    <span className="text-xs opacity-80">Fast & Secure</span>
                  </>
                )}
              </div>
            </Button>
            {/* Hidden logic component */}
            {botUsername && (
              <TelegramLoginWidget
                botUsername={botUsername}
                onAuth={handleTelegramAuth}
              />
            )}
          </div>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500 font-medium uppercase tracking-wider text-xs">Alternative</span>
            </div>
          </div>

          {/* Slack Login */}
          <Button
            onClick={handleSlackLogin}
            disabled={loading}
            className="w-full bg-[#4A154B] hover:bg-[#3b113c] text-white py-3 h-auto"
          >
            <div className="flex flex-col items-center">
              {loading ? (
                <Loader className="animate-spin" size={24} />
              ) : (
                <>
                  <span className="text-lg font-bold">⚡ Login with Slack</span>
                  <span className="text-xs opacity-80">Workplace Auth</span>
                </>
              )}
            </div>
          </Button>
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
