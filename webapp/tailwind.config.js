/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'var(--primary)',
          foreground: 'var(--primary-text)',
        },
        background: {
          DEFAULT: 'var(--bg)',
          secondary: 'var(--secondary-bg)',
        },
        text: {
          DEFAULT: 'var(--text)',
          muted: 'var(--hint)',
        },
        border: 'var(--border-color)',
        success: {
          DEFAULT: 'var(--success)',
          light: 'var(--success-light)',
        },
        warning: {
          DEFAULT: 'var(--warning)',
          light: 'var(--warning-light)',
        },
        error: {
          DEFAULT: 'var(--error)',
          light: 'var(--error-light)',
        },
        info: {
          DEFAULT: 'var(--info)',
          light: 'var(--info-light)',
        },
        tg: {
          bg: 'var(--tg-bg-color)',
          text: 'var(--tg-text-color)',
          hint: 'var(--tg-hint-color)',
          link: 'var(--tg-link-color)',
          button: 'var(--tg-button-color)',
          'button-text': 'var(--tg-button-text-color)',
          'secondary-bg': 'var(--tg-secondary-bg-color)',
        }
      },
      borderRadius: {
        sm: 'var(--space-xs)', // matching css
        DEFAULT: 'var(--radius-md)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
      },
      spacing: {
        // extending default spacing
      }
    },
  },
  plugins: [],
}
