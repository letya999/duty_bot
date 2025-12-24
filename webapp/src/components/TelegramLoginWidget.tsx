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

  // Set up the global callback handler once at component level (persists across re-renders)
  // Note: Using 'TelegramAuthCallback' instead of 'onTelegramAuth' to avoid Telegram widget parsing issues
  useEffect(() => {
    console.log('📍 [TelegramWidget] Setting up global TelegramAuthCallback handler');

    // @ts-ignore
    window.TelegramAuthCallback = (user: any) => {
      console.log('✅ [TelegramWidget] TelegramAuthCallback CALLED');
      console.log('✅ [TelegramWidget] User data received:', user);
      console.log('✅ [TelegramWidget] User ID:', user?.id);
      console.log('✅ [TelegramWidget] User hash:', user?.hash);
      console.log('✅ [TelegramWidget] Auth date:', user?.auth_date);
      console.log('✅ [TelegramWidget] All keys in user object:', Object.keys(user || {}));
      callbackRef.current(user);
    };

    // Only clean up if component is unmounting, not on re-renders
    return () => {
      console.log('📍 [TelegramWidget] Component unmounting, keeping global handler intact');
    };
  }, []); // Empty deps - setup only once

  // Render the widget when props change, but don't reload telegram script
  useEffect(() => {
    if (!containerRef.current || !botUsername) return;

    console.log('📍 [TelegramWidget] Creating widget container with attributes');
    console.log('  - Bot username:', botUsername);
    console.log('  - Button size:', buttonSize);
    console.log('  - Corner radius:', cornerRadius);

    // Create a script element but don't load the telegram.org/js/telegram-widget.js script
    // (it's already loaded globally at app level)
    // Instead, create an element that the telegram script will process
    const script = document.createElement('script');
    script.setAttribute('data-telegram-login', botUsername);
    script.setAttribute('data-size', buttonSize);
    script.setAttribute('data-radius', cornerRadius.toString());
    script.setAttribute('data-request-access', requestAccess === 'notify' ? 'write' : 'write');
    script.setAttribute('data-userpic', usePic.toString());
    script.setAttribute('data-onauth', 'TelegramAuthCallback'); // Use different name to avoid parsing issues

    // Clear and add the script element
    containerRef.current.innerHTML = '';
    containerRef.current.appendChild(script);

    // Trigger Telegram widget rendering on the newly added element
    // @ts-ignore
    if (window.Telegram && window.Telegram.Login && window.Telegram.Login.render) {
      setTimeout(() => {
        // @ts-ignore
        window.Telegram.Login.render(script);
        console.log('✅ [TelegramWidget] Widget rendered via Telegram.Login.render()');
      }, 0);
    } else {
      console.log('⚠️ [TelegramWidget] Telegram.Login.render not available yet');
    }

    return () => {
      console.log('📍 [TelegramWidget] Widget prop changed, cleaning up old widget');
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [botUsername, buttonSize, cornerRadius, requestAccess, usePic]);

  return (
    <div className="flex justify-center min-h-[40px]" ref={containerRef} />
  );
};

export default TelegramLoginWidget;
