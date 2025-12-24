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

  useEffect(() => {
    if (!containerRef.current) return;

    // Store the callback in window so Telegram can call it
    window.onTelegramAuth = (user: any) => {
      onAuth(user);
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

    // Clear container and append script
    containerRef.current.innerHTML = '';
    containerRef.current.appendChild(script);

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
      // @ts-ignore
      delete window.onTelegramAuth;
    };
  }, [botUsername, buttonSize, cornerRadius, requestAccess, usePic, onAuth]);

  return (
    <div className="flex justify-center min-h-[40px]" ref={containerRef} />
  );
};

export default TelegramLoginWidget;
