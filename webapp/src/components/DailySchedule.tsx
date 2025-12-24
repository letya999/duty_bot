import React, { useEffect, useState } from 'react';
import { DailySchedule, User } from '../types';
import { apiService } from '../services/api';
import './DailySchedule.css';

interface DailyScheduleProps {
  date: string;
}

export const DailyScheduleComponent: React.FC<DailyScheduleProps> = ({ date }) => {
  const [schedule, setSchedule] = useState<DailySchedule | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSchedule();
  }, [date]);

  const loadSchedule = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getDailySchedule(date);
      setSchedule(data);
    } catch (err) {
      setError('Failed to load schedule');
      console.error('Failed to load schedule:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="daily-schedule">
        <div className="loading">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="daily-schedule">
        <div className="error-message">{error}</div>
      </div>
    );
  }

  if (!schedule || schedule.users.length === 0) {
    return (
      <div className="daily-schedule">
        <h3 className="schedule-date">{formatDate(date)}</h3>
        <div className="empty-state">
          <div className="empty-state-icon">📭</div>
          <p>No one assigned to this day</p>
        </div>
      </div>
    );
  }

  return (
    <div className="daily-schedule">
      <h3 className="schedule-date">{formatDate(date)}</h3>

      {schedule.notes && (
        <div className="schedule-notes">
          <strong>Notes:</strong> {schedule.notes}
        </div>
      )}

      <div className="users-list">
        {schedule.users.map((user) => (
          <div key={user.id} className="user-card">
            <div className="user-avatar">{user.first_name.charAt(0)}</div>
            <div className="user-info">
              <div className="user-name">
                {user.first_name}
                {user.last_name && ` ${user.last_name}`}
              </div>
              {user.username && <div className="user-username">@{user.username}</div>}
            </div>
            <div className="user-badge">On Duty</div>
          </div>
        ))}
      </div>

      <p className="users-count text-center mt-lg">
        {schedule.users.length} {schedule.users.length === 1 ? 'person' : 'people'} on duty
      </p>
    </div>
  );
};
