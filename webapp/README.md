# Duty Bot Telegram Mini App

A modern Telegram mini app for managing team duty schedules with an intuitive calendar interface.

## Features

- 📅 **Interactive Calendar** - Visual month view with duty assignments
- 👥 **Team Management** - View and manage team members' duties
- 📅 **Daily Schedule** - See who's on duty for any selected day
- 🎨 **Dark Mode Support** - Automatic theme switching with Telegram client
- 📱 **Mobile First** - Optimized for Telegram mobile and desktop clients
- ⚡ **Fast & Responsive** - Built with React and Vite

## Setup

### Development

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file with:
```
VITE_API_URL=http://localhost:8000/api/admin
```

3. Start development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Production Build

```bash
npm run build
```

This creates an optimized build in the `dist` directory.

## Docker

Build and run with Docker:

```bash
docker build -t duty-bot-webapp .
docker run -p 5173:5173 duty-bot-webapp
```

Or use docker-compose from the project root:

```bash
docker-compose up webapp
```

## Architecture

### Frontend Structure

```
src/
├── components/        # React components
│   ├── Calendar.tsx   # Calendar view component
│   ├── DailySchedule.tsx  # Daily schedule component
│   ├── TeamManager.tsx    # Team management component
│   └── *.css         # Component styles
├── hooks/            # Custom React hooks
│   └── useTelegramWebApp.ts  # Telegram Web App API integration
├── services/         # API communication
│   └── api.ts        # REST API client
├── types/            # TypeScript interfaces
│   └── index.ts      # Type definitions
├── styles/           # Global styles
│   └── index.css     # Global CSS with theme variables
├── App.tsx           # Main app component
└── main.tsx          # App entry point
```

### API Integration

The app communicates with the backend API at `/api/admin` endpoints:

- User management and authentication
- Schedule management (create, update, delete schedules)
- Team management
- Reports and statistics
- Google Calendar integration
- Incident tracking

## Customization

### Theme Variables

The app uses CSS variables for theming that automatically sync with Telegram:

```css
--tg-bg-color       /* Background color */
--tg-text-color     /* Text color */
--tg-hint-color     /* Hint/secondary text */
--tg-link-color     /* Links color */
--tg-button-color   /* Button color */
--tg-button-text-color  /* Button text */
```

These are automatically set from Telegram theme parameters.

### Responsive Design

The app is fully responsive and tested on:
- iPhone/iPad (mobile Telegram)
- Android phones (mobile Telegram)
- Desktop web versions

## Development Tips

1. **Telegram Web App Debug**: Use Telegram Web App simulation in browser dev tools
2. **API Testing**: The API endpoints require valid Telegram init data
3. **Build Size**: Currently optimized with React 18 and Vite (bundle ~50KB gzipped)

## License

Same as parent project
