import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Plus, List, Calendar, Edit2, Trash2, Copy, AlertCircle, X } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { apiService } from '../services/api';
import { Schedule, Team, User } from '../types';

type ViewMode = 'calendar' | 'list';
type CalendarMode = 'day' | 'week' | 'month';

interface DutyFormData {
  userIds: string[];
  teamId: string;
  startDate: string;
  endDate: string;
  isBulk: boolean;
}

const getWeekDays = (date: Date) => {
  const start = new Date(date);
  start.setDate(start.getDate() - start.getDay());
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    return d;
  });
};

interface EditingDuty {
  id: number;
  userId?: number;
  userIds?: number[];
  date: string;
  teamId?: number;
  isShift?: boolean;
}

const SchedulesPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('calendar');
  const [calendarMode, setCalendarMode] = useState<CalendarMode>('month');

  // Calendar state
  const [currentDate, setCurrentDate] = useState(new Date());

  // Derived state for API calls and Month View
  const month = currentDate.getMonth() + 1;
  const year = currentDate.getFullYear();

  // List view state
  const [listStartDate, setListStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [listEndDate, setListEndDate] = useState(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);

  // Data state
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);

  // Filter state
  const [selectedTeamFilter, setSelectedTeamFilter] = useState<string>('');

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [editingDuty, setEditingDuty] = useState<EditingDuty | null>(null);
  const [formData, setFormData] = useState<DutyFormData>({
    userIds: [],
    teamId: '',
    startDate: '',
    endDate: '',
    isBulk: false,
  });

  useEffect(() => {
    loadData();
  }, [month, year, viewMode, listStartDate, listEndDate]);

  // Reset selected date when switching modes
  useEffect(() => {
    // When switching modes, we might want to sync current date or keep it?
    // For now, let's just ensure we are looking at something relevant.
  }, [viewMode, calendarMode]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [teamsData, usersData] = await Promise.all([
        apiService.getTeams(),
        apiService.getAllUsers(),
      ]);

      setTeams(teamsData);
      setUsers(usersData);

      if (viewMode === 'calendar') {
        // For calendar, we fetch the whole month (or surrounding if needed)
        const monthData = await apiService.getMonthSchedule(year, month);
        setSchedules(monthData.days.flatMap(d => d.duties));
      } else {
        const rangeData = await apiService.getSchedulesByDateRange(listStartDate, listEndDate);
        setSchedules(rangeData);
      }
    } catch (err) {
      console.error('Failed to load schedules', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAddModal = (date?: string) => {
    setEditingDuty(null);
    setSelectedDate(date || new Date().toISOString().split('T')[0]);
    setFormData({
      userIds: [],
      teamId: '',
      startDate: date || new Date().toISOString().split('T')[0],
      endDate: date || new Date().toISOString().split('T')[0],
      isBulk: false,
    });
    setIsModalOpen(true);
  };

  const getSelectedTeam = () => {
    return teams.find((t: Team) => t.id.toString() === formData.teamId);
  };

  const handleOpenEditModal = (duty: Schedule) => {
    setEditingDuty({
      id: duty.id,
      userId: duty.user_id,
      date: duty.duty_date,
      teamId: duty.team_id,
    });
    setSelectedDate(duty.duty_date);
    setFormData({
      userIds: [duty.user_id.toString()],
      teamId: duty.team_id?.toString() || '',
      startDate: duty.duty_date,
      endDate: duty.duty_date,
      isBulk: false,
    });
    setIsModalOpen(true);
  };

  const handleSaveDuty = async () => {
    try {
      const selectedTeam = getSelectedTeam();
      const isShiftTeam = selectedTeam?.has_shifts || false;

      if (editingDuty) {
        // Edit existing - only single duty edit for now
        await apiService.editDuty(
          editingDuty.id,
          parseInt(formData.userIds[0]),
          selectedDate,
          formData.teamId ? parseInt(formData.teamId) : undefined
        );
      } else if (formData.isBulk && formData.userIds.length > 0) {
        if (!formData.teamId) {
          alert('Please select a team for bulk assignment');
          return;
        }
        // Bulk assign - works for both shift and regular teams
        const userIds = formData.userIds.map((id: string) => parseInt(id));
        if (isShiftTeam && formData.teamId) {
          // For shift teams, assign all users to each date in range
          await apiService.assignShiftsBulk(
            userIds,
            formData.startDate,
            formData.endDate,
            parseInt(formData.teamId)
          );
        } else {
          // For regular teams, use schedule endpoint
          await apiService.assignBulkDuties(
            userIds,
            formData.startDate,
            formData.endDate,
            formData.teamId ? parseInt(formData.teamId) : undefined
          );
        }
      } else if (formData.userIds.length > 0) {
        // Single create
        if (isShiftTeam && formData.teamId) {
          // For shift teams, add user to shift
          await apiService.assignShift(
            parseInt(formData.userIds[0]),
            selectedDate,
            parseInt(formData.teamId)
          );
        } else {
          // For regular teams, use schedule endpoint
          await apiService.assignDuty(
            parseInt(formData.userIds[0]),
            selectedDate,
            formData.teamId ? parseInt(formData.teamId) : undefined
          );
        }
      }
      setIsModalOpen(false);
      loadData();
    } catch (err) {
      console.error('Failed to save duty', err);
    }
  };

  const handleDeleteDuty = async (scheduleId: number) => {
    if (!window.confirm('Delete this duty assignment?')) return;
    try {
      await apiService.removeDuty(scheduleId);
      loadData();
    } catch (err) {
      console.error('Failed to delete duty', err);
    }
  };

  const getFilteredSchedules = () => {
    let filtered = schedules;
    if (selectedTeamFilter) {
      filtered = filtered.filter((s: Schedule) => (s.team_id?.toString() === selectedTeamFilter) || (s.team?.id?.toString() === selectedTeamFilter));
    }
    return filtered.sort((a: Schedule, b: Schedule) => new Date(a.duty_date).getTime() - new Date(b.duty_date).getTime());
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

  const getSchedulesForDay = (day: number) => {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const daySchedules = getFilteredSchedules().filter((s: Schedule) => s.duty_date === dateStr);
    return daySchedules;
  };

  const handlePrev = () => {
    const newDate = new Date(currentDate);
    if (calendarMode === 'day') {
      newDate.setDate(newDate.getDate() - 1);
    } else if (calendarMode === 'week') {
      newDate.setDate(newDate.getDate() - 7);
    } else {
      newDate.setMonth(newDate.getMonth() - 1);
    }
    setCurrentDate(newDate);
  };

  const handleNext = () => {
    const newDate = new Date(currentDate);
    if (calendarMode === 'day') {
      newDate.setDate(newDate.getDate() + 1);
    } else if (calendarMode === 'week') {
      newDate.setDate(newDate.getDate() + 7);
    } else {
      newDate.setMonth(newDate.getMonth() + 1);
    }
    setCurrentDate(newDate);
  };

  const renderDayView = () => {
    // Use currentDate as the view cursor
    const viewDate = currentDate;
    const dateStr = viewDate.toISOString().split('T')[0];
    const duties = getFilteredSchedules().filter((s: Schedule) => s.duty_date === dateStr);

    return (
      <Card>
        <CardHeader className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">
            {viewDate.toLocaleDateString('default', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </h2>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={handlePrev}>
              <ChevronLeft size={18} />
            </Button>
            <Button variant="secondary" size="sm" onClick={handleNext}>
              <ChevronRight size={18} />
            </Button>
          </div>
        </CardHeader>
        <CardBody>
          <div className="p-4 border rounded-lg bg-white min-h-48">
            {duties.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No duties assigned</p>
            ) : (
              <div className="space-y-2">
                {duties.map((s: Schedule) => (
                  <div key={s.id} className="flex justify-between items-center p-3 bg-blue-50 rounded-lg border border-blue-100">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-200 flex items-center justify-center text-blue-700 font-bold">
                        {s.user.first_name[0]}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{s.user.first_name} {s.user.last_name}</p>
                        <p className="text-xs text-gray-500">{s.team?.name}</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => handleOpenEditModal(s)} className="p-2 text-blue-600 hover:bg-blue-100 rounded">
                        <Edit2 size={16} />
                      </button>
                      <button onClick={() => handleDeleteDuty(s.id)} className="p-2 text-red-600 hover:bg-red-100 rounded">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-4 text-center">
              <Button variant="secondary" onClick={() => handleOpenAddModal(viewDate.toISOString().split('T')[0])}>
                <Plus size={16} /> Add Duty
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>
    );
  };

  const renderWeekView = () => {
    // Determine the week to show.
    const weekDays = getWeekDays(currentDate);

    // Header date range
    const startStr = weekDays[0].toLocaleDateString('default', { month: 'short', day: 'numeric' });
    const endStr = weekDays[6].toLocaleDateString('default', { month: 'short', day: 'numeric' });
    const yearStr = weekDays[6].getFullYear();

    return (
      <Card>
        <CardHeader className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">
            {startStr} - {endStr}, {yearStr}
          </h2>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={handlePrev}>
              <ChevronLeft size={18} />
            </Button>
            <Button variant="secondary" size="sm" onClick={handleNext}>
              <ChevronRight size={18} />
            </Button>
          </div>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-7 gap-2">
            {weekDays.map(date => {
              const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
              const dateStr = date.toISOString().split('T')[0];
              const daySchedules = getFilteredSchedules().filter((s: Schedule) => s.duty_date === dateStr);
              // Show days even if not in current month, though we might not have data if not fetched.
              const isCurrentMonth = date.getMonth() === month - 1;
              const isToday = date.toDateString() === new Date().toDateString();

              return (
                <div key={date.toString()} className="flex flex-col gap-2">
                  <div className={`text-center font-semibold ${isToday ? 'text-blue-600' : 'text-gray-700'}`}>
                    {dayNames[date.getDay()]} {date.getDate()}
                  </div>
                  <div
                    className={`min-h-64 p-2 border rounded-lg ${isCurrentMonth ? 'bg-white' : 'bg-gray-50'}`}
                    onClick={() => handleOpenAddModal(dateStr)}
                  >
                    {daySchedules.map(s => (
                      <div key={s.id} className="text-xs bg-blue-50 text-blue-700 p-1 mb-1 rounded truncate flex justify-between group">
                        <span>{s.user.first_name}</span>
                        <div className="hidden group-hover:block cursor-pointer" onClick={(e) => { e.stopPropagation(); handleOpenEditModal(s); }}>
                          <Edit2 size={10} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </CardBody>
      </Card>
    );
  };

  const renderMonthView = () => {
    const daysInMonth = getDaysInMonth(month, year);
    const firstDay = getFirstDayOfMonth(month, year);
    const days = Array.from({ length: 42 }, (_, i) => {
      const dayNum = i - firstDay + 1;
      return dayNum > 0 && dayNum <= daysInMonth ? dayNum : null;
    });

    return (
      <Card>
        <CardHeader className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">
            {monthNames[month - 1]} {year}
          </h2>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={handlePrev}>
              <ChevronLeft size={18} />
            </Button>
            <Button variant="secondary" size="sm" onClick={handleNext}>
              <ChevronRight size={18} />
            </Button>
          </div>
        </CardHeader>

        <CardBody>
          <div className="grid grid-cols-7 gap-2 mb-4">
            {dayNames.map(day => (
              <div key={day} className="text-center font-semibold text-gray-700 py-2">
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-2">
            {days.map((day, idx) => {
              const daySchedules = day ? getSchedulesForDay(day) : [];
              return (
                <div
                  key={idx}
                  className={`min-h-24 p-2 border rounded-lg ${day ? 'bg-white border-gray-200 hover:border-blue-300 cursor-pointer' : 'bg-gray-50 border-gray-100'
                    }`}
                  onClick={() => {
                    if (day) {
                      const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                      handleOpenAddModal(dateStr);
                    }
                  }}
                >
                  {day && (
                    <>
                      <p className="font-semibold text-gray-700 mb-1">{day}</p>
                      <div className="space-y-1">
                        {daySchedules.slice(0, 2).map((s: Schedule) => (
                          <div
                            key={s.id}
                            className="text-xs bg-blue-50 text-blue-700 p-1 rounded truncate group relative hover:bg-blue-100"
                            onClick={(e: React.MouseEvent) => e.stopPropagation()}
                          >
                            <div className="flex justify-between items-center">
                              <span>{s.user.first_name}</span>
                              <div className="hidden group-hover:flex gap-1 text-blue-600">
                                <Edit2
                                  size={12}
                                  className="cursor-pointer"
                                  onClick={(e: React.MouseEvent) => {
                                    e.stopPropagation();
                                    handleOpenEditModal(s);
                                  }}
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                        {daySchedules.length > 2 && (
                          <div className="text-xs text-gray-500">
                            +{daySchedules.length - 2} more
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </CardBody>
      </Card>
    );
  };

  const renderCalendar = () => {
    switch (calendarMode) {
      case 'day': return renderDayView();
      case 'week': return renderWeekView();
      default: return renderMonthView();
    }
  };

  const renderListView = () => {
    const filteredSchedules = getFilteredSchedules();

    return (
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">Duty List</h2>
        </CardHeader>

        <CardBody>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Date</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">User</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Team</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredSchedules.map((duty: Schedule) => (
                  <tr key={duty.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 text-gray-900">{duty.duty_date}</td>
                    <td className="py-3 px-4 text-gray-900">{duty.user.first_name}</td>
                    <td className="py-3 px-4 text-gray-700">{duty.team?.name || '-'}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleOpenEditModal(duty)}
                          className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => handleDeleteDuty(duty.id)}
                          className="p-1 text-red-600 hover:bg-red-50 rounded"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>
    );
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
          onClick={() => handleOpenAddModal()}
          variant="primary"
          size="md"
        >
          <Plus size={20} />
          Add Duty
        </Button>
      </div>

      {/* Controls */}
      <div className="mb-6 flex gap-4 flex-wrap items-center">
        {/* View Mode Toggle */}
        <div className="flex gap-2 bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setViewMode('calendar')}
            className={`px-4 py-2 rounded flex items-center gap-2 ${viewMode === 'calendar'
              ? 'bg-white text-blue-600 shadow'
              : 'text-gray-600 hover:text-gray-900'
              }`}
          >
            <Calendar size={18} />
            Calendar
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-4 py-2 rounded flex items-center gap-2 ${viewMode === 'list'
              ? 'bg-white text-blue-600 shadow'
              : 'text-gray-600 hover:text-gray-900'
              }`}
          >
            <List size={18} />
            List
          </button>
        </div>

        {/* Calendar mode toggle */}
        {viewMode === 'calendar' && (
          <div className="flex gap-2 bg-gray-100 p-1 rounded-lg">
            {['day', 'week', 'month'].map(mode => (
              <button
                key={mode}
                onClick={() => setCalendarMode(mode as CalendarMode)}
                className={`px-3 py-2 rounded text-sm capitalize ${calendarMode === mode
                  ? 'bg-white text-blue-600 shadow'
                  : 'text-gray-600 hover:text-gray-900'
                  }`}
              >
                {mode}
              </button>
            ))}
          </div>
        )}

        {/* Team Filter */}
        <select
          value={selectedTeamFilter}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedTeamFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Teams</option>
          {teams.map((team: Team) => (
            <option key={team.id} value={team.id}>
              {team.name}
            </option>
          ))}
        </select>

        {/* Date range filter for list view */}
        {viewMode === 'list' && (
          <div className="flex gap-2">
            <input
              type="date"
              value={listStartDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setListStartDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <span className="py-2 text-gray-500">to</span>
            <input
              type="date"
              value={listEndDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setListEndDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        )}
      </div>

      {/* Main content */}
      {viewMode === 'calendar' ? renderCalendar() : renderListView()}

      {/* Duty Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingDuty ? 'Edit Duty Assignment' : 'Add Duty Assignment'}
        size="md"
      >
        <div className="space-y-4">
          {!editingDuty && (
            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.isBulk}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, isBulk: e.target.checked })}
                  className="w-4 h-4"
                />
                <span className="text-sm font-medium text-gray-700">Bulk assign for date range</span>
              </label>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Team (Optional)
            </label>
            <select
              value={formData.teamId}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFormData({ ...formData, teamId: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a team</option>
              {teams.map((team: Team) => (
                <option key={team.id} value={team.id}>
                  {team.name} {team.has_shifts ? '(Shifts)' : ''}
                </option>
              ))}
            </select>
          </div>

          {getSelectedTeam()?.has_shifts && !editingDuty ? (
            <>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-2">
                <p className="text-sm text-blue-700">
                  This team has shifts enabled. You can assign multiple people to the same day.
                </p>
              </div>

              {!formData.isBulk ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Date *
                  </label>
                  <input
                    type="date"
                    value={selectedDate}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSelectedDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Start Date *
                    </label>
                    <input
                      type="date"
                      value={formData.startDate}
                      onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      End Date *
                    </label>
                    <input
                      type="date"
                      value={formData.endDate}
                      onChange={(e) => setFormData({ ...formData, endDate: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </>
              )}

              <div>
                <label className="flex items-center gap-2 mb-3">
                  <input
                    type="checkbox"
                    checked={formData.isBulk}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, isBulk: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <span className="text-sm font-medium text-gray-700">Date range (bulk)</span>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Users *
                </label>
                <div className="space-y-2 max-h-48 overflow-y-auto border border-gray-300 rounded-lg p-3">
                  {users.map((user: User) => (
                    <label key={user.id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.userIds.includes(user.id.toString())}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                          if (e.target.checked) {
                            setFormData({
                              ...formData,
                              userIds: [...formData.userIds, user.id.toString()]
                            });
                          } else {
                            setFormData({
                              ...formData,
                              userIds: formData.userIds.filter(id => id !== user.id.toString())
                            });
                          }
                        }}
                        className="w-4 h-4"
                      />
                      <span className="text-gray-700">{user.first_name} {user.last_name || ''}</span>
                    </label>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <>
              {formData.isBulk && !getSelectedTeam()?.has_shifts ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Start Date *
                    </label>
                    <input
                      type="date"
                      value={formData.startDate}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, startDate: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      End Date *
                    </label>
                    <input
                      type="date"
                      value={formData.endDate}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, endDate: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Users *
                    </label>
                    <div className="space-y-2 max-h-48 overflow-y-auto border border-gray-300 rounded-lg p-3">
                      {users.map((user: User) => (
                        <label key={user.id} className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={formData.userIds.includes(user.id.toString())}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                              if (e.target.checked) {
                                setFormData({
                                  ...formData,
                                  userIds: [...formData.userIds, user.id.toString()]
                                });
                              } else {
                                setFormData({
                                  ...formData,
                                  userIds: formData.userIds.filter(id => id !== user.id.toString())
                                });
                              }
                            }}
                            className="w-4 h-4"
                          />
                          <span className="text-gray-700">{user.first_name} {user.last_name || ''}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Date *
                    </label>
                    <input
                      type="date"
                      value={selectedDate}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSelectedDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      User *
                    </label>
                    <select
                      value={formData.userIds[0] || ''}
                      onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFormData({ ...formData, userIds: [e.target.value] })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Select a user</option>
                      {users.map((user: User) => (
                        <option key={user.id} value={user.id}>
                          {user.first_name} {user.last_name || ''}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}
            </>
          )}

          {/* Top checkbox already handles this */}

          <div className="flex gap-3 justify-end">
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveDuty}
              disabled={formData.userIds.length === 0 && (!editingDuty || !selectedDate)}
            >
              {editingDuty ? 'Update' : 'Add'} Duty
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default SchedulesPage;
