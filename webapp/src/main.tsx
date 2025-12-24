import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Load Telegram Login Widget script once at app level
// This prevents re-initialization issues with React remounting
const loadTelegramScript = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    // Check if already loaded and properly initialized
    if ((window as any).Telegram?.Login?.render) {
      console.log('📍 [Main] Telegram script already loaded and ready');
      resolve();
      return;
    }

    const telegramScript = document.createElement('script');
    telegramScript.src = 'https://telegram.org/js/telegram-widget.js';
    telegramScript.async = true;

    telegramScript.onload = () => {
      console.log('✅ [Main] Telegram script file loaded successfully');

      // Wait for the Telegram library to fully initialize
      // The library might take some time to set up its globals
      let attempts = 0;
      const maxAttempts = 100; // ~2 seconds timeout

      const checkTelegramReady = () => {
        attempts++;

        if ((window as any).Telegram?.Login?.render) {
          console.log('✅ [Main] Telegram.Login is fully ready and available');
          resolve();
        } else if (attempts < maxAttempts) {
          // Telegram not ready yet, wait a bit and try again
          setTimeout(checkTelegramReady, 20);
        } else {
          console.error('❌ [Main] Timeout waiting for Telegram.Login to be ready');
          // Still resolve to let app render - widget will try to initialize later
          resolve();
        }
      };

      checkTelegramReady();
    };

    telegramScript.onerror = (error) => {
      console.error('❌ [Main] Failed to load Telegram script:', error);
      // Don't reject - let app render anyway, component will handle missing Telegram
      resolve();
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
