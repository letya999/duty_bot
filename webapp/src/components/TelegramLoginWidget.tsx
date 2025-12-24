import React, { useEffect, useRef } from 'react';

interface TelegramLoginWidgetProps {
  botUsername: string;
  onAuth: (data: any) => void;
  buttonSize?: 'large' | 'medium' | 'small';
  cornerRadius?: number;
  requestAccess?: 'notify' | boolean;
  usePic?: boolean;
}

declare global {
  interface Window {
    onTelegramAuth: (user: any) => void;
  }
}

export const TelegramLoginWidget: React.FC<TelegramLoginWidgetProps> = ({
  botUsername,
  onAuth,
  buttonSize = 'large',
  cornerRadius = 15,
  requestAccess = 'notify',
  usePic = true,
}: TelegramLoginWidgetProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const callbackRef = React.useRef(onAuth);

  // Update callback ref without causing widget recreation
  React.useEffect(() => {
    callbackRef.current = onAuth;
  }, [onAuth]);

  useEffect(() => {
    if (!containerRef.current) return;

    console.log('📍 [TelegramWidget] Creating Telegram widget script');
    console.log('📍 [TelegramWidget] Bot username:', botUsername);
    console.log('📍 [TelegramWidget] Button size:', buttonSize);
    console.log('📍 [TelegramWidget] Container ref:', containerRef.current);

    // Store the callback in window so Telegram can call it
    // Use ref to avoid recreating the widget when callback changes
    window.onTelegramAuth = (user: any) => {
      console.log('✅ [TelegramWidget] onTelegramAuth callback CALLED');
      console.log('✅ [TelegramWidget] User data received:', user);
      console.log('✅ [TelegramWidget] User ID:', user?.id);
      console.log('✅ [TelegramWidget] User hash:', user?.hash);
      console.log('✅ [TelegramWidget] Auth date:', user?.auth_date);
      console.log('✅ [TelegramWidget] All keys in user object:', Object.keys(user || {}));
      callbackRef.current(user);
    };

    // Create script element
    const script = document.createElement('script');
    script.src = `https://telegram.org/js/telegram-widget.js?22`;
    script.async = true;
    script.setAttribute('data-telegram-login', botUsername);
    script.setAttribute('data-size', buttonSize);
    script.setAttribute('data-radius', cornerRadius.toString());
    script.setAttribute('data-request-access', requestAccess === 'notify' ? 'write' : 'write');
    script.setAttribute('data-userpic', usePic.toString());
    script.setAttribute('data-onauth', 'onTelegramAuth'); // name only, not call

    console.log('📍 [TelegramWidget] Script element created with attributes:');
    console.log('  - data-telegram-login:', botUsername);
    console.log('  - data-size:', buttonSize);
    console.log('  - data-onauth: onTelegramAuth');

    // Add script load handlers
    script.onload = () => {
      console.log('✅ [TelegramWidget] Script loaded successfully');
    };

    script.onerror = (error: any) => {
      console.error('❌ [TelegramWidget] Script failed to load:', error);
      console.error('❌ [TelegramWidget] Script error details:', {
        message: error?.message,
        type: error?.type,
        filename: error?.filename,
        lineno: error?.lineno,
        colno: error?.colno,
      });
    };

    // Clear container and append script
    containerRef.current.innerHTML = '';
    containerRef.current.appendChild(script);
    console.log('📍 [TelegramWidget] Script appended to container');

    return () => {
      console.log('📍 [TelegramWidget] Cleaning up widget (component unmounted)');
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
      // @ts-ignore
      delete window.onTelegramAuth;
    };
  }, [botUsername, buttonSize, cornerRadius, requestAccess, usePic]);

  return (
    <div className="flex justify-center min-h-[40px]" ref={containerRef} />
  );
};

export default TelegramLoginWidget;
