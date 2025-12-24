import React, { useEffect, useRef } from 'react';

interface TelegramLoginWidgetProps {
  botUsername: string;
  onAuth: (data: any) => void;
  buttonSize?: 'large' | 'medium' | 'small';
  cornerRadius?: number;
  requestAccess?: 'notify' | boolean;
  usePic?: boolean;
  mode?: 'widget' | 'callback';
}

declare global {
  interface Window {
    TelegramAuthCallback: (user: any) => void;
    Telegram: any;
  }
}

export const TelegramLoginWidget: React.FC<TelegramLoginWidgetProps> = ({
  botUsername,
  onAuth,
}: TelegramLoginWidgetProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const callbackRef = useRef(onAuth);

  // Update callback ref without causing widget recreation
  useEffect(() => {
    callbackRef.current = onAuth;
  }, [onAuth]);

  // Set up the global callback handler and load the Telegram script
  useEffect(() => {
    console.log('📍 [TelegramWidget] Initializing Telegram Auth API handler');

    // Register global callback
    window.TelegramAuthCallback = (user: any) => {
      console.log('✅ [TelegramWidget] TelegramAuthCallback received data');
      callbackRef.current(user);
    };

    // Load Telegram widget script if not already present
    if (!document.querySelector('script[src*="telegram-widget.js"]')) {
      const script = document.createElement('script');
      script.src = 'https://telegram.org/js/telegram-widget.js?22';
      script.async = true;
      document.head.appendChild(script);
      console.log('📍 [TelegramWidget] Telegram script added to document head');
    }

    return () => {
      // Cleanup if necessary
    };
  }, []);

  // This component no longer renders anything visible, it just manages the logic/script
  return null;
};

export default TelegramLoginWidget;
