import React, { useEffect } from 'react';

interface TelegramLoginWidgetProps {
  botUsername: string;
  onAuth: (data: any) => void;
  buttonSize?: 'large' | 'medium' | 'small';
  cornerRadius?: number;
  requestAccess?: 'notify' | boolean;
  usePic?: boolean;
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'telegram-login': TelegramLoginWidgetElement;
    }
  }
  interface Window {
    Telegram?: {
      Login?: {
        embedButton?: (buttonId: string, options: any) => void;
      };
    };
  }
}

interface TelegramLoginWidgetElement extends React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> {
  ['telegram-login']?: string;
  ['data-auth-url']?: string;
  ['data-size']?: string;
  ['data-onauth']?: string;
  ['data-use-pic']?: boolean;
  ['data-request-access']?: string;
  ['data-userpic']?: boolean;
  ['data-radius']?: number;
}

export const TelegramLoginWidget: React.FC<TelegramLoginWidgetProps> = ({
  botUsername,
  onAuth,
  buttonSize = 'large',
  cornerRadius = 15,
  requestAccess = 'notify',
  usePic = true,
}) => {
  useEffect(() => {
    // Store the callback in window so Telegram can call it
    (window as any).onTelegramAuth = onAuth;

    // Check if Telegram widget is loaded and ready
    const checkTelegramReady = () => {
      if ((window as any).Telegram?.Login?.embedButton) {
        // If using embedButton method (for custom button)
        const widgetElement = document.getElementById('telegram-login-widget');
        if (widgetElement) {
          (window as any).Telegram.Login.embedButton('telegram-login-widget', {
            bot_id: botUsername, // This would be bot ID, not username
            size: buttonSize,
            radius: cornerRadius,
            auth_url: '/web/auth/telegram-widget-callback',
            request_access: requestAccess,
            userpic: usePic,
          });
        }
      }
    };

    // Wait for Telegram script to load
    if ((window as any).Telegram) {
      checkTelegramReady();
    } else {
      // Retry after a short delay
      const timer = setTimeout(checkTelegramReady, 1000);
      return () => clearTimeout(timer);
    }
  }, [botUsername, buttonSize, cornerRadius, requestAccess, usePic, onAuth]);

  const sizeMap = {
    small: '20px',
    medium: '28px',
    large: '40px',
  };

  return (
    <div className="flex justify-center">
      <script
        async
        src={`https://telegram.org/js/telegram-widget.js?15`}
        data-telegram-login={botUsername}
        data-size={buttonSize}
        data-onauth="onTelegramAuth"
        data-request-access="notify"
        data-userpic="true"
        data-radius={cornerRadius}
      />
      <div id="telegram-login-widget" />
    </div>
  );
};

export default TelegramLoginWidget;
