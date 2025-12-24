import React, { useState, useEffect } from 'react';
import { MonthSchedule, User } from '../types';
import { apiService } from '../services/api';
import './Calendar.css';

interface CalendarProps {
  onDateSelect: (date: string) => void;
  selectedDate?: string;
}

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export const Calendar: React.FC<CalendarProps> = ({ onDateSelect, selectedDate }) => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [schedule, setSchedule] = useState<MonthSchedule | null>(null);
  const [loading, setLoading] = useState(false);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  useEffect(() => {
    loadMonthSchedule();
  }, [year, month]);

  const loadMonthSchedule = async () => {
    setLoading(true);
    try {
      const data = await apiService.getMonthSchedule(year, month + 1);
      setSchedule(data);
    } catch (error) {
      console.error('Failed to load schedule:', error);
    } finally {
      setLoading(false);
    }
  };

  const getDaysInMonth = (year: number, month: number) => {
    return new Date(year, month + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (year: number, month: number) => {
    return new Date(year, month, 1).getDay();
  };

  const handlePrevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  const handleDateClick = (day: number) => {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    onDateSelect(dateStr);
  };

  const getUsersForDate = (dateStr: string): User[] => {
    if (!schedule) return [];
    const dayData = schedule.days.find((d) => d.date === dateStr);
    return dayData?.users || [];
  };

  const getDaysArray = () => {
    const days = [];
    const daysInMonth = getDaysInMonth(year, month);
    const firstDay = getFirstDayOfMonth(year, month);

    // Empty cells for days before month starts
    for (let i = 0; i < firstDay; i++) {
      days.push(null);
    }

    // Days of the month
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }

    return days;
  };

  const days = getDaysArray();
  const isSelected = (day: number | null) => {
    if (!day || !selectedDate) return false;
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return dateStr === selectedDate;
  };

  return (
    <div className="calendar">
      <div className="calendar-header">
        <button className="btn-icon" onClick={handlePrevMonth} title="Previous month">
          ←
        </button>
        <h2 className="calendar-title">
          {MONTH_NAMES[month]} {year}
        </h2>
        <button className="btn-icon" onClick={handleNextMonth} title="Next month">
          →
        </button>
      </div>

      <div className="calendar-weekdays">
        {DAY_NAMES.map((day) => (
          <div key={day} className="weekday">
            {day}
          </div>
        ))}
      </div>

      <div className="calendar-days">
        {days.map((day, index) => {
          if (day === null) {
            return <div key={`empty-${index}`} className="day empty"></div>;
          }

          const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
          const users = getUsersForDate(dateStr);
          const isToday = new Date().toDateString() === new Date(year, month, day).toDateString();

          return (
            <button
              key={day}
              className={`day ${isSelected(day) ? 'selected' : ''} ${isToday ? 'today' : ''} ${users.length > 0 ? 'has-events' : ''}`}
              onClick={() => handleDateClick(day)}
              title={`${day} - ${users.length} on duty`}
            >
              <div className="day-number">{day}</div>
              {users.length > 0 && (
                <div className="day-users">
                  {users.slice(0, 2).map((user, i) => (
                    <div key={user.id} className="user-badge" title={user.first_name}>
                      {user.first_name.charAt(0)}
                    </div>
                  ))}
                  {users.length > 2 && <div className="user-badge-more">+{users.length - 2}</div>}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {loading && <div className="text-center text-muted mt-md">Loading...</div>}
    </div>
  );
};
