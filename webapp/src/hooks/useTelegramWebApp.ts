import { useEffect } from 'react';

export const useTelegramWebApp = () => {
  const webApp = window.Telegram?.WebApp;

  useEffect(() => {
    if (webApp) {
      // Expand the webapp to take full screen
      webApp.expand();

      // Enable closing button for back navigation
      webApp.ready();

      // Set theme based on Telegram settings
      applyTheme(webApp);

      // Listen for theme changes
      const handleThemeChange = () => {
        applyTheme(webApp);
      };

      webApp.onEvent('themeChanged', handleThemeChange);

      return () => {
        webApp.offEvent('themeChanged', handleThemeChange);
      };
    }
  }, [webApp]);

  return webApp;
};

const applyTheme = (webApp: typeof window.Telegram.WebApp) => {
  const isDark = webApp.colorScheme === 'dark';
  const theme = webApp.themeParams;

  const root = document.documentElement;
  root.style.setProperty('--tg-bg-color', theme.bg_color);
  root.style.setProperty('--tg-text-color', theme.text_color);
  root.style.setProperty('--tg-hint-color', theme.hint_color);
  root.style.setProperty('--tg-link-color', theme.link_color);
  root.style.setProperty('--tg-button-color', theme.button_color);
  root.style.setProperty('--tg-button-text-color', theme.button_text_color);
  root.style.setProperty('--tg-secondary-bg-color', theme.section_bg_color || theme.bg_color);

  if (isDark) {
    root.classList.add('dark-theme');
    root.classList.remove('light-theme');
  } else {
    root.classList.add('light-theme');
    root.classList.remove('dark-theme');
  }
};

export const useTelegramMainButton = () => {
  const webApp = window.Telegram?.WebApp;
  const mainButton = webApp?.MainButton;

  return {
    show: () => mainButton?.show(),
    hide: () => mainButton?.hide(),
    setText: (text: string) => mainButton?.setText(text),
    setColor: (color: string) => {
      if (mainButton) {
        mainButton.color = color;
      }
    },
    onClick: (callback: () => void) => {
      if (mainButton) {
        mainButton.onClick(callback);
      }
    },
    offClick: (callback: () => void) => {
      if (mainButton) {
        mainButton.offClick(callback);
      }
    },
    showProgress: () => mainButton?.showProgress(),
    hideProgress: () => mainButton?.hideProgress(),
    enable: () => mainButton?.enable(),
    disable: () => mainButton?.disable(),
  };
};

export const useTelegramBackButton = () => {
  const webApp = window.Telegram?.WebApp;
  const backButton = webApp?.BackButton;

  return {
    show: () => backButton?.show(),
    hide: () => backButton?.hide(),
    onClick: (callback: () => void) => {
      if (backButton) {
        backButton.onClick(callback);
      }
    },
    offClick: (callback: () => void) => {
      if (backButton) {
        backButton.offClick(callback);
      }
    },
  };
};

export const showAlert = (message: string) => {
  window.Telegram?.WebApp?.showAlert(message);
};

export const showConfirm = (message: string): Promise<boolean> => {
  return new Promise((resolve) => {
    window.Telegram?.WebApp?.showConfirm(message, (confirmed) => {
      resolve(confirmed);
    });
  });
};

export const sendData = (data: string) => {
  window.Telegram?.WebApp?.sendData(data);
};
