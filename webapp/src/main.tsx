import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Load Telegram Login Widget script once at app level
// This prevents re-initialization issues with React remounting
const telegramScript = document.createElement('script');
telegramScript.src = 'https://telegram.org/js/telegram-widget.js?22';
telegramScript.async = true;
document.head.appendChild(telegramScript);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
