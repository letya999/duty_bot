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
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());

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
    return teams.find(t => t.id.toString() === formData.teamId);
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
        // Bulk assign - works for both shift and regular teams
        const userIds = formData.userIds.map(id => parseInt(id));
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
      filtered = filtered.filter(s => s.team_id?.toString() === selectedTeamFilter);
    }
    return filtered.sort((a, b) => new Date(a.duty_date).getTime() - new Date(b.duty_date).getTime());
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
    const daySchedules = getFilteredSchedules().filter(s => s.duty_date === dateStr);
    return daySchedules;
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

  const renderCalendar = () => {
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
            <Button variant="secondary" size="sm" onClick={handlePrevMonth}>
              <ChevronLeft size={18} />
            </Button>
            <Button variant="secondary" size="sm" onClick={handleNextMonth}>
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
                  className={`min-h-24 p-2 border rounded-lg ${
                    day ? 'bg-white border-gray-200 hover:border-blue-300 cursor-pointer' : 'bg-gray-50 border-gray-100'
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
                        {daySchedules.slice(0, 2).map(s => (
                          <div
                            key={s.id}
                            className="text-xs bg-blue-50 text-blue-700 p-1 rounded truncate group relative hover:bg-blue-100"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className="flex justify-between items-center">
                              <span>{s.user.first_name}</span>
                              <div className="hidden group-hover:flex gap-1 text-blue-600">
                                <Edit2
                                  size={12}
                                  className="cursor-pointer"
                                  onClick={(e) => {
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
                {filteredSchedules.map(duty => (
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
            className={`px-4 py-2 rounded flex items-center gap-2 ${
              viewMode === 'calendar'
                ? 'bg-white text-blue-600 shadow'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Calendar size={18} />
            Calendar
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-4 py-2 rounded flex items-center gap-2 ${
              viewMode === 'list'
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
                className={`px-3 py-2 rounded text-sm capitalize ${
                  calendarMode === mode
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
          onChange={(e) => setSelectedTeamFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Teams</option>
          {teams.map(team => (
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
              onChange={(e) => setListStartDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <span className="py-2 text-gray-500">to</span>
            <input
              type="date"
              value={listEndDate}
              onChange={(e) => setListEndDate(e.target.value)}
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
                  onChange={(e) => setFormData({ ...formData, isBulk: e.target.checked })}
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
              onChange={(e) => setFormData({ ...formData, teamId: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a team</option>
              {teams.map(team => (
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
                    onChange={(e) => setSelectedDate(e.target.value)}
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
                    onChange={(e) => setFormData({ ...formData, isBulk: e.target.checked })}
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
                  {users.map(user => (
                    <label key={user.id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.userIds.includes(user.id.toString())}
                        onChange={(e) => {
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

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Users *
                    </label>
                    <div className="space-y-2 max-h-48 overflow-y-auto border border-gray-300 rounded-lg p-3">
                      {users.map(user => (
                        <label key={user.id} className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={formData.userIds.includes(user.id.toString())}
                            onChange={(e) => {
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
                      onChange={(e) => setSelectedDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      User *
                    </label>
                    <select
                      value={formData.userIds[0] || ''}
                      onChange={(e) => setFormData({ ...formData, userIds: [e.target.value] })}
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
                </>
              )}
            </>
          )}

          {!editingDuty && !getSelectedTeam()?.has_shifts && (
            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.isBulk}
                  onChange={(e) => setFormData({ ...formData, isBulk: e.target.checked })}
                  className="w-4 h-4"
                />
                <span className="text-sm font-medium text-gray-700">Bulk assign for date range</span>
              </label>
            </div>
          )}

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
