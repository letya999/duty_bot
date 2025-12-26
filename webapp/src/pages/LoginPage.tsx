import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Loader, HelpCircle } from 'lucide-react';
import { Alert } from '../components/ui/Alert';
import TelegramLoginWidget from '../components/TelegramLoginWidget';

// Import logos
import telegramLogo from '../assets/telegram-logo.png';
import slackLogo from '../assets/slack-logo.png';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [botUsername, setBotUsername] = useState<string>('');

  // Get bot username from environment or config
  useEffect(() => {
    const username = import.meta.env.VITE_TELEGRAM_BOT_USERNAME || 'test_duty_999_bot';
    setBotUsername(username);
  }, []);

  const handleTelegramAuth = useCallback(async (data: any) => {
    try {
      setLoading(true);
      setError(null);

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
      localStorage.setItem('session_token', result.session_token);
      localStorage.setItem('user', JSON.stringify(result.user));
      navigate('/');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(errorMessage);
      setLoading(false);
    }
  }, [navigate]);

  const handleSlackLogin = () => {
    setLoading(true);
    window.location.href = '/web/auth/slack-login';
  };

  const handleProgrammaticLogin = () => {
    if (!window.Telegram?.Login) {
      setError("Telegram script not loaded yet. Please wait a moment.");
      return;
    }

    const botId = parseInt(import.meta.env.VITE_TELEGRAM_BOT_ID || '8527825927');
    window.Telegram.Login.auth(
      { bot_id: botId, request_access: true },
      (user: any) => {
        if (user) {
          handleTelegramAuth(user);
        }
      }
    );
  };

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center px-4 bg-[#0f172a]">
      {/* Background Decorative Elements */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-emerald-500/20 rounded-full blur-[120px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 rounded-full blur-[120px]" />
      <div className="absolute top-[20%] right-[10%] w-[20%] h-[20%] bg-purple-500/10 rounded-full blur-[100px]" />

      <div className="w-full max-w-md relative z-10 transition-all duration-500 ease-in-out animate-fade-in-up">
        {/* Glassmorphism Card */}
        <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.3)] p-10 overflow-hidden">

          {/* Logo Section */}
          <div className="text-center mb-10 animate-fade-in-down delay-100">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-tr from-emerald-400 to-teal-600 rounded-2xl shadow-lg mb-4 transform hover:rotate-12 transition-transform duration-300">
              <span className="text-3xl">🎯</span>
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Duty Bot</h1>
            <p className="text-emerald-400 font-medium tracking-wide uppercase text-xs mt-1">Workspace Admin</p>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-6 animate-fade-in-down">
              <Alert
                type="error"
                message={error}
                onClose={() => setError(null)}
              />
            </div>
          )}

          {/* Login Options */}
          <div className="space-y-4 animate-fade-in-up delay-200">
            {/* Telegram Login */}
            <button
              onClick={handleProgrammaticLogin}
              disabled={loading}
              className="group relative w-full flex items-center justify-between bg-white text-slate-900 px-6 py-4 rounded-2xl font-semibold transition-all duration-300 hover:bg-slate-50 hover:shadow-xl hover:-translate-y-0.5 disabled:opacity-70 disabled:hover:translate-y-0"
            >
              <div className="flex items-center">
                <img src={telegramLogo} alt="Telegram" className="w-8 h-8 mr-4 group-hover:scale-110 transition-transform" />
                <div className="text-left">
                  <p className="leading-tight">Continue with Telegram</p>
                  <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">Fast & Secure</p>
                </div>
              </div>
              {loading ? (
                <Loader className="animate-spin text-emerald-500" size={20} />
              ) : (
                <div className="w-2 h-2 rounded-full bg-emerald-500 group-hover:animate-ping" />
              )}
            </button>

            {/* Divider */}
            <div className="flex items-center py-4">
              <div className="flex-grow border-t border-white/10" />
              <span className="px-4 text-[10px] font-bold text-white/40 uppercase tracking-[0.2em]">OR</span>
              <div className="flex-grow border-t border-white/10" />
            </div>

            {/* Slack Login */}
            <button
              onClick={handleSlackLogin}
              disabled={loading}
              className="group relative w-full flex items-center justify-between bg-white/5 border border-white/10 text-white px-6 py-4 rounded-2xl font-semibold transition-all duration-300 hover:bg-white/10 hover:shadow-xl hover:-translate-y-0.5 disabled:opacity-70 disabled:hover:translate-y-0"
            >
              <div className="flex items-center">
                <img src={slackLogo} alt="Slack" className="w-8 h-8 mr-4 group-hover:scale-110 transition-transform object-contain" />
                <div className="text-left">
                  <p className="leading-tight">Continue with Slack</p>
                  <p className="text-[10px] text-white/40 font-medium uppercase tracking-wider">Workplace Auth</p>
                </div>
              </div>
              <div className="w-2 h-2 rounded-full bg-purple-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          </div>

          {/* Hidden Telegram Widget */}
          {botUsername && (
            <div className="hidden">
              <TelegramLoginWidget
                botUsername={botUsername}
                onAuth={handleTelegramAuth}
              />
            </div>
          )}

          {/* Footer Info */}
          <div className="mt-10 flex items-start gap-4 p-4 bg-white/5 rounded-2xl border border-white/5 animate-fade-in-up delay-300">
            <HelpCircle className="text-emerald-400 shrink-0" size={18} />
            <p className="text-xs text-white/60 leading-relaxed">
              You will be redirected to authenticate with your chosen platform.
              Contact your administrator if you need access.
            </p>
          </div>
        </div>

        {/* Bottom Credits */}
        <p className="mt-8 text-center text-white/30 text-[10px] font-medium tracking-widest uppercase animate-fade-in delay-300">
          &copy; 2024 Duty Bot System &bull; All Rights Reserved
        </p>
      </div>
    </div>
  );
};

export default LoginPage;

