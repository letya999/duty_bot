import { useState, useEffect } from 'react';
import { Calendar } from './components/Calendar';
import { DailyScheduleComponent } from './components/DailySchedule';
import { TeamManager } from './components/TeamManager';
import { useTelegramWebApp, useTelegramBackButton } from './hooks/useTelegramWebApp';
import './App.css';

type ViewType = 'calendar' | 'schedule' | 'manage';

function App() {
  const webApp = useTelegramWebApp();
  const backButton = useTelegramBackButton();
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [currentView, setCurrentView] = useState<ViewType>('calendar');

  // Initialize with today's date
  useEffect(() => {
    const today = new Date();
    const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    setSelectedDate(dateStr);
  }, []);

  // Handle back button visibility
  useEffect(() => {
    if (currentView !== 'calendar') {
      backButton.show();
      const handleBack = () => {
        setCurrentView('calendar');
      };
      backButton.onClick(handleBack);

      return () => {
        backButton.offClick(handleBack);
        backButton.hide();
      };
    } else {
      backButton.hide();
    }
  }, [currentView, backButton]);

  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
    setCurrentView('schedule');
  };

  const handleManageClick = () => {
    if (selectedDate) {
      setCurrentView('manage');
    }
  };

  const handleViewChange = (view: ViewType) => {
    setCurrentView(view);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Duty Bot</h1>
        <p className="app-subtitle">Team duty schedule manager</p>
      </header>

      <main className="app-content">
        {currentView === 'calendar' && (
          <div className="view calendar-view">
            <Calendar onDateSelect={handleDateSelect} selectedDate={selectedDate} />

            <div className="quick-actions">
              <button className="btn btn-primary" onClick={() => handleViewChange('schedule')}>
                📅 Today's Schedule
              </button>
              <button className="btn btn-secondary" onClick={handleManageClick}>
                ⚙️ Manage Duties
              </button>
            </div>
          </div>
        )}

        {currentView === 'schedule' && selectedDate && (
          <div className="view schedule-view">
            <DailyScheduleComponent date={selectedDate} />
            <button className="btn btn-secondary" onClick={handleManageClick}>
              ⚙️ Assign for this day
            </button>
          </div>
        )}

        {currentView === 'manage' && selectedDate && (
          <div className="view manage-view">
            <TeamManager selectedDate={selectedDate} />
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p className="footer-text">
          {webApp?.initDataUnsafe?.user?.first_name && (
            <>
              👋 Hello, <strong>{webApp.initDataUnsafe.user.first_name}</strong>
            </>
          )}
        </p>
      </footer>
    </div>
  );
}

export default App;
