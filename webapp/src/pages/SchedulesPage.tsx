import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { apiService } from '../services/api';
import { Schedule, Team, User } from '../types';

const SchedulesPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [formData, setFormData] = useState({
    userId: '',
    teamId: '',
  });

  useEffect(() => {
    loadData();
  }, [month, year]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [monthData, teamsData, usersData] = await Promise.all([
        apiService.getMonthSchedule(year, month),
        apiService.getTeams(),
        apiService.getAllUsers(),
      ]);

      setSchedules(monthData.days.flatMap(d => d.duties));
      setTeams(teamsData);
      setUsers(usersData);
    } catch (err) {
      console.error('Failed to load schedules', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddDuty = async () => {
    if (!selectedDate || !formData.userId) return;

    try {
      await apiService.assignDuty(
        parseInt(formData.userId),
        selectedDate,
        formData.teamId ? parseInt(formData.teamId) : undefined
      );
      setIsModalOpen(false);
      setFormData({ userId: '', teamId: '' });
      loadData();
    } catch (err) {
      console.error('Failed to add duty', err);
    }
  };

  const handlePrevMonth = () => {
    if (month === 1) {
      setMonth(12);
      setYear(year - 1);
    } else {
      setMonth(month - 1);
    }
  };

  const handleNextMonth = () => {
    if (month === 12) {
      setMonth(1);
      setYear(year + 1);
    } else {
      setMonth(month + 1);
    }
  };

  const getDaysInMonth = (m: number, y: number) => {
    return new Date(y, m, 0).getDate();
  };

  const getFirstDayOfMonth = (m: number, y: number) => {
    return new Date(y, m - 1, 1).getDay();
  };

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  const daysInMonth = getDaysInMonth(month, year);
  const firstDay = getFirstDayOfMonth(month, year);
  const days = Array.from({ length: 42 }, (_, i) => {
    const dayNum = i - firstDay + 1;
    return dayNum > 0 && dayNum <= daysInMonth ? dayNum : null;
  });

  const getSchedulesForDay = (day: number) => {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return schedules.filter(s => s.duty_date === dateStr);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Schedules</h1>
          <p className="text-gray-600 mt-2">Manage duty assignments</p>
        </div>
        <Button
          onClick={() => {
            setSelectedDate(new Date().toISOString().split('T')[0]);
            setIsModalOpen(true);
          }}
          variant="primary"
          size="md"
        >
          <Plus size={20} />
          Add Duty
        </Button>
      </div>

      <Card>
        {/* Calendar Header */}
        <CardHeader className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">
            {monthNames[month - 1]} {year}
          </h2>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={handlePrevMonth}>
              <ChevronLeft size={18} />
            </Button>
            <Button variant="secondary" size="sm" onClick={handleNextMonth}>
              <ChevronRight size={18} />
            </Button>
          </div>
        </CardHeader>

        {/* Calendar */}
        <CardBody>
          {/* Day headers */}
          <div className="grid grid-cols-7 gap-2 mb-4">
            {dayNames.map(day => (
              <div key={day} className="text-center font-semibold text-gray-700 py-2">
                {day}
              </div>
            ))}
          </div>

          {/* Calendar days */}
          <div className="grid grid-cols-7 gap-2">
            {days.map((day, idx) => (
              <div
                key={idx}
                className={`min-h-24 p-2 border rounded-lg ${
                  day ? 'bg-white border-gray-200 hover:border-blue-300 cursor-pointer' : 'bg-gray-50 border-gray-100'
                }`}
                onClick={() => {
                  if (day) {
                    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                    setSelectedDate(dateStr);
                    setIsModalOpen(true);
                  }
                }}
              >
                {day && (
                  <>
                    <p className="font-semibold text-gray-700 mb-1">{day}</p>
                    <div className="space-y-1">
                      {getSchedulesForDay(day).slice(0, 2).map(s => (
                        <div
                          key={s.id}
                          className="text-xs bg-blue-50 text-blue-700 p-1 rounded truncate"
                        >
                          {s.user.first_name}
                        </div>
                      ))}
                      {getSchedulesForDay(day).length > 2 && (
                        <div className="text-xs text-gray-500">
                          +{getSchedulesForDay(day).length - 2} more
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </CardBody>
      </Card>

      {/* Add Duty Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Add Duty Assignment"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Date
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              User *
            </label>
            <select
              value={formData.userId}
              onChange={(e) => setFormData({ ...formData, userId: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a user</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.first_name} {user.last_name || ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Team (Optional)
            </label>
            <select
              value={formData.teamId}
              onChange={(e) => setFormData({ ...formData, teamId: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a team</option>
              {teams.map(team => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-3 justify-end">
            <Button
              variant="secondary"
              onClick={() => setIsModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleAddDuty}
              disabled={!formData.userId}
            >
              Add Duty
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default SchedulesPage;
