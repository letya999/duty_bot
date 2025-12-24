import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Load Telegram Login Widget script once at app level
// This prevents re-initialization issues with React remounting
const loadTelegramScript = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    if ((window as any).Telegram?.Login) {
      console.log('📍 [Main] Telegram script already loaded');
      resolve();
      return;
    }

    const telegramScript = document.createElement('script');
    telegramScript.src = 'https://telegram.org/js/telegram-widget.js?22';
    telegramScript.async = true;

    telegramScript.onload = () => {
      console.log('✅ [Main] Telegram script loaded successfully');
      resolve();
    };

    telegramScript.onerror = (error) => {
      console.error('❌ [Main] Failed to load Telegram script:', error);
      reject(new Error('Failed to load Telegram widget script'));
    };

    document.head.appendChild(telegramScript);
    console.log('📍 [Main] Loading Telegram widget script...');
  });
};

// Load Telegram script before rendering React app
loadTelegramScript().then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}).catch((error) => {
  console.error('❌ [Main] Failed to initialize app:', error);
  // Render anyway, app can work without Telegram widget
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
});
