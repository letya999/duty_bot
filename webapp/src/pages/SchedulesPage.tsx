import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Icons } from '../components/ui/Icons';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Select } from '../components/ui/Select';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { apiService } from '../services/api';
import { Team, User, Schedule } from '../types';

type ViewMode = 'calendar' | 'list';
type CalendarMode = 'month' | 'week' | 'day';

const SchedulesPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('calendar');
  const [calendarMode, setCalendarMode] = useState<CalendarMode>('month');
  const [currentDate, setCurrentDate] = useState(new Date());

  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);

  const [selectedTeamFilter, setSelectedTeamFilter] = useState<string>('');
  const [listStartDate, setListStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [listEndDate, setListEndDate] = useState(
    new Date(new Date().setDate(new Date().getDate() + 30)).toISOString().split('T')[0]
  );

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDuty, setEditingDuty] = useState<Schedule | null>(null);
  const [selectedDate, setSelectedDate] = useState('');
  const [formData, setFormData] = useState({
    teamId: '',
    userIds: [] as string[],
    isBulk: false,
    startDate: '',
    endDate: ''
  });

  useEffect(() => {
    loadData();
  }, [currentDate, viewMode, calendarMode, selectedTeamFilter, listStartDate, listEndDate]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [teamsData, usersData] = await Promise.all([
        apiService.getTeams(),
        apiService.getAllUsers()
      ]);
      setTeams(teamsData);
      setUsers(usersData);

      let startStr: string, endStr: string;
      const formatDate = (d: Date) => {
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
      };

      if (viewMode === 'calendar') {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();

        if (calendarMode === 'month') {
          startStr = formatDate(new Date(year, month, 1));
          endStr = formatDate(new Date(year, month + 1, 0));
        } else if (calendarMode === 'week') {
          const firstDay = currentDate.getDate() - currentDate.getDay();
          const start = new Date(currentDate);
          start.setDate(firstDay);
          const end = new Date(currentDate);
          end.setDate(firstDay + 6);
          startStr = formatDate(start);
          endStr = formatDate(end);
        } else {
          startStr = formatDate(currentDate);
          endStr = formatDate(currentDate);
        }
      } else {
        startStr = listStartDate;
        endStr = listEndDate;
      }

      const schedulesData = await apiService.getSchedulesByDateRange(startStr, endStr);

      // Filter by team if selected
      const filtered = selectedTeamFilter
        ? schedulesData.filter(s => s.team_id === parseInt(selectedTeamFilter))
        : schedulesData;

      setSchedules(filtered);
    } catch (err) {
      console.error('Failed to load schedules', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAddModal = (dateStr?: string) => {
    setEditingDuty(null);
    setSelectedDate(dateStr || new Date().toISOString().split('T')[0]);
    setFormData({
      teamId: '',
      userIds: [],
      isBulk: false,
      startDate: dateStr || new Date().toISOString().split('T')[0],
      endDate: dateStr || new Date().toISOString().split('T')[0]
    });
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (duty: Schedule) => {
    setEditingDuty(duty);
    setSelectedDate(duty.duty_date);
    setFormData({
      teamId: duty.team_id ? duty.team_id.toString() : '',
      userIds: [duty.user_id.toString()],
      isBulk: false,
      startDate: duty.duty_date,
      endDate: duty.duty_date
    });
    setIsModalOpen(true);
  };

  const handleSaveDuty = async () => {
    if (formData.isBulk && !formData.teamId) {
      alert(t('schedules.modal.no_team_error'));
      return;
    }
    try {
      if (editingDuty) {
        // Edit single duty
        await apiService.editDuty(
          editingDuty.id,
          parseInt(formData.userIds[0]),
          selectedDate,
          formData.teamId ? parseInt(formData.teamId) : undefined
        );
      } else {
        if (formData.isBulk) {
          // Bulk assignment (works for both shifts and regular duties)
          await apiService.assignBulkDuties(
            formData.userIds.map((id: string) => parseInt(id)),
            formData.startDate,
            formData.endDate,
            formData.teamId ? parseInt(formData.teamId) : undefined
          );
        } else {
          // Single day assignment (possibly multiple users if shift enabled)
          if (formData.userIds.length > 1) {
            // treat as bulk for single day
            await apiService.assignBulkDuties(
              formData.userIds.map((id: string) => parseInt(id)),
              selectedDate,
              selectedDate,
              formData.teamId ? parseInt(formData.teamId) : undefined
            );
          } else if (formData.userIds.length > 0) {
            await apiService.assignDuty(
              parseInt(formData.userIds[0]),
              selectedDate,
              formData.teamId ? parseInt(formData.teamId) : undefined
            );
          }
        }
      }
      setIsModalOpen(false);
      loadData();
    } catch (err) {
      console.error('Failed to save duty', err);
    }
  };

  const handleDeleteDuty = async (id: number) => {
    if (!window.confirm(t('schedules.modal.delete_confirm'))) return;
    try {
      await apiService.removeDuty(id);
      loadData();
    } catch (err) {
      console.error('Failed to delete duty', err);
    }
  };

  const getSelectedTeam = () => {
    return teams.find(t => t.id.toString() === formData.teamId);
  };

  const nextPeriod = () => {
    const newDate = new Date(currentDate);
    if (calendarMode === 'month') {
      newDate.setMonth(newDate.getMonth() + 1);
    } else if (calendarMode === 'week') {
      newDate.setDate(newDate.getDate() + 7);
    } else {
      newDate.setDate(newDate.getDate() + 1);
    }
    setCurrentDate(newDate);
  };

  const prevPeriod = () => {
    const newDate = new Date(currentDate);
    if (calendarMode === 'month') {
      newDate.setMonth(newDate.getMonth() - 1);
    } else if (calendarMode === 'week') {
      newDate.setDate(newDate.getDate() - 7);
    } else {
      newDate.setDate(newDate.getDate() - 1);
    }
    setCurrentDate(newDate);
  };

  const renderCalendar = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const locale = i18n.language || 'default';

    let days: (Date | null)[] = [];
    let headers: string[] = [];
    let gridCols = 'grid-cols-7';

    if (calendarMode === 'month') {
      const daysInMonth = new Date(year, month + 1, 0).getDate();
      const firstDayOfMonth = new Date(year, month, 1).getDay(); // 0 is Sunday
      // Padding for first week
      for (let i = 0; i < firstDayOfMonth; i++) {
        days.push(null);
      }
      // Days of month
      for (let i = 1; i <= daysInMonth; i++) {
        days.push(new Date(year, month, i));
      }

      const tempDate = new Date(2024, 0, 7); // A Sunday (Jan 7, 2024 was Sunday)
      for (let i = 0; i < 7; i++) {
        headers.push(tempDate.toLocaleDateString(locale, { weekday: 'short' }));
        tempDate.setDate(tempDate.getDate() + 1);
      }
    } else if (calendarMode === 'week') {
      const firstDay = currentDate.getDate() - currentDate.getDay();
      for (let i = 0; i < 7; i++) {
        const d = new Date(currentDate);
        d.setDate(firstDay + i);
        days.push(d);
      }
      const tempDate = new Date(2024, 0, 7); // A Sunday
      for (let i = 0; i < 7; i++) {
        headers.push(tempDate.toLocaleDateString(locale, { weekday: 'short' }));
        tempDate.setDate(tempDate.getDate() + 1);
      }
    } else {
      days.push(new Date(currentDate));
      headers.push(currentDate.toLocaleDateString(locale, { weekday: 'long' }));
      gridCols = 'grid-cols-1';
    }

    const getPeriodDisplay = () => {
      if (calendarMode === 'month') {
        return currentDate.toLocaleDateString(locale, { month: 'long', year: 'numeric' });
      }
      if (calendarMode === 'week') {
        const firstDay = currentDate.getDate() - currentDate.getDay();
        const start = new Date(currentDate);
        start.setDate(firstDay);
        const end = new Date(currentDate);
        end.setDate(firstDay + 6);
        return `${start.toLocaleDateString(locale, { day: 'numeric', month: 'short' })} - ${end.toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' })}`;
      }
      return currentDate.toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
    };

    return (
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div className="flex gap-1">
            <button onClick={prevPeriod} title={t('common.prev')} className="p-1 hover:bg-gray-100 rounded text-gray-600 transition-colors">
              <Icons.ChevronLeft size={20} />
            </button>
            <button onClick={nextPeriod} title={t('common.next')} className="p-1 hover:bg-gray-100 rounded text-gray-600 transition-colors">
              <Icons.ChevronRight size={20} />
            </button>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 capitalize">
            {getPeriodDisplay()}
          </h2>
        </CardHeader>
        <CardBody>
          <div className={`grid ${gridCols} gap-px bg-gray-200 border border-gray-200 rounded-lg overflow-hidden`}>
            {headers.map((day, idx) => (
              <div key={idx} className="bg-gray-50 p-2 text-center text-sm font-medium text-text-muted capitalize">
                {day}
              </div>
            ))}
            {days.map((day, idx) => {
              if (!day) return <div key={`pad-${idx}`} className="bg-white min-h-[120px]" />;

              const dateStr = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
              const daySchedules = schedules.filter(s => s.duty_date === dateStr);
              const isToday = new Date().toISOString().split('T')[0] === dateStr;

              return (
                <div
                  key={dateStr}
                  className={`bg-white min-h-[120px] p-2 hover:bg-gray-50 transition-colors group relative ${isToday ? 'bg-info-light/30' : ''
                    }`}
                  onClick={() => handleOpenAddModal(dateStr)} // Click cell to add
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className={`text-sm font-medium ${isToday
                      ? 'bg-primary text-primary-text w-6 h-6 flex items-center justify-center rounded-full'
                      : 'text-gray-700'
                      }`}>
                      {day.getDate()}
                    </span>
                    <button
                      className="opacity-0 group-hover:opacity-100 text-primary hover:text-primary-dark transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenAddModal(dateStr);
                      }}
                    >
                      <Icons.Plus size={16} />
                    </button>
                  </div>
                  <div className="space-y-1">
                    {daySchedules.map(schedule => (
                      <div
                        key={schedule.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenEditModal(schedule);
                        }}
                        className="text-xs p-1.5 rounded bg-info-light border-l-2 border-info cursor-pointer hover:brightness-95 transition-all truncate"
                        title={`${schedule.user.display_name || schedule.user.first_name} ${schedule.team ? `(${schedule.team.name})` : ''}`}
                      >
                        <span className="font-medium text-info-dark">
                          {schedule.user.display_name || schedule.user.first_name}
                        </span>
                        {schedule.team && (
                          <span className="text-info-dark/70 ml-1">
                            • {schedule.team.name}
                          </span>
                        )}
                      </div>
                    ))}
                    {daySchedules.length > 2 && (
                      <div className="text-xs text-text-muted pl-1">
                        + {daySchedules.length - 2} more
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </CardBody>
      </Card>
    );
  };

  const renderListView = () => {
    return (
      <Card>
        <CardBody>
          {schedules.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">{t('schedules.list_view.date')}</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">{t('schedules.list_view.user')}</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">{t('schedules.list_view.team')}</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-700">{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {schedules.sort((a, b) => new Date(a.duty_date).getTime() - new Date(b.duty_date).getTime()).map(schedule => (
                    <tr key={schedule.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-900">{schedule.duty_date}</td>
                      <td className="py-3 px-4 text-gray-900 font-medium">
                        {schedule.user.display_name || `${schedule.user.first_name} ${schedule.user.last_name || ''}`}
                      </td>
                      <td className="py-3 px-4 text-text-muted">
                        {schedule.team?.name || '-'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleOpenEditModal(schedule)}
                            className="p-1.5 text-info hover:bg-info-light rounded"
                          >
                            <Icons.Edit size={16} />
                          </button>
                          <button
                            onClick={() => handleDeleteDuty(schedule.id)}
                            className="p-1.5 text-error hover:bg-error-light rounded"
                          >
                            <Icons.Delete size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 text-text-muted">
              {t('schedules.list_view.no_duties')}
            </div>
          )}
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
          <h1 className="text-3xl font-bold text-gray-900">{t('schedules.title')}</h1>
          <p className="text-gray-600 mt-2">{t('schedules.subtitle')}</p>
        </div>
        <Button
          onClick={() => handleOpenAddModal()}
          variant="primary"
          size="md"
          className="mt-6 shadow-lg transform hover:scale-105 transition-all"
        >
          <Icons.Plus size={20} />
          {t('schedules.add_duty')}
        </Button>
      </div>

      <div className="mb-6 flex gap-4 flex-wrap items-center">
        <div className="flex gap-2 bg-secondary-bg p-1 rounded-lg">
          <button
            onClick={() => setViewMode('calendar')}
            className={`px-4 py-2 rounded flex items-center gap-2 ${viewMode === 'calendar'
              ? 'bg-white text-primary shadow'
              : 'text-text-muted hover:text-gray-900'
              }`}
          >
            <Icons.Calendar size={18} />
            {t('schedules.calendar')}
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-4 py-2 rounded flex items-center gap-2 ${viewMode === 'list'
              ? 'bg-white text-primary shadow'
              : 'text-text-muted hover:text-gray-900'
              }`}
          >
            <Icons.List size={18} />
            {t('schedules.list')}
          </button>
        </div>

        {viewMode === 'calendar' && (
          <div className="flex gap-2 bg-secondary-bg p-1 rounded-lg">
            {['day', 'week', 'month'].map(mode => (
              <button
                key={mode}
                onClick={() => setCalendarMode(mode as CalendarMode)}
                className={`px-3 py-2 rounded text-sm capitalize ${calendarMode === mode
                  ? 'bg-white text-primary shadow'
                  : 'text-text-muted hover:text-gray-900'
                  }`}
              >
                {t(`schedules.${mode}`)}
              </button>
            ))}
          </div>
        )}

        <Select
          className="w-48"
          value={selectedTeamFilter}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedTeamFilter(e.target.value)}
        >
          <option value="">{t('schedules.filters.all_teams')}</option>
          {teams.map((team: Team) => (
            <option key={team.id} value={team.id}>
              {team.name}
            </option>
          ))}
        </Select>

        {viewMode === 'list' && (
          <div className="flex gap-2 items-center">
            <Input
              type="date"
              className="w-40"
              value={listStartDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setListStartDate(e.target.value)}
            />
            <span className="text-text-muted">{t('schedules.filters.to')}</span>
            <Input
              type="date"
              className="w-40"
              value={listEndDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setListEndDate(e.target.value)}
            />
          </div>
        )}
      </div>

      {viewMode === 'calendar' ? renderCalendar() : renderListView()}

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingDuty ? t('schedules.modal.edit_title') : t('schedules.modal.add_title')}
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
                <span className="text-sm font-medium text-gray-700">{t('schedules.modal.bulk_assign')}</span>
              </label>
            </div>
          )}

          <div>
            <Select
              label={t('schedules.filters.team')}
              value={formData.teamId}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFormData({ ...formData, teamId: e.target.value })}
            >
              <option value="">{t('schedules.modal.select_team')}</option>
              {teams.map((team: Team) => (
                <option key={team.id} value={team.id}>
                  {team.name} {team.has_shifts ? '(Shifts)' : ''}
                </option>
              ))}
            </Select>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              {getSelectedTeam()?.has_shifts ? t('schedules.modal.users_label') : t('schedules.modal.user_label')}
            </label>
            {getSelectedTeam()?.has_shifts ? (
              <div className="border border-gray-200 rounded-lg bg-gray-50/50 p-2 max-h-48 overflow-y-auto space-y-1 shadow-inner">
                {(formData.teamId ? (getSelectedTeam()?.members || []) : users).map(u => (
                  <label key={u.id} className="flex items-center gap-3 p-2 hover:bg-white hover:shadow-sm rounded-md cursor-pointer transition-all border border-transparent hover:border-gray-200">
                    <input
                      type="checkbox"
                      checked={formData.userIds.includes(u.id.toString())}
                      onChange={(e) => {
                        const id = u.id.toString();
                        if (e.target.checked) {
                          setFormData({ ...formData, userIds: [...formData.userIds, id] });
                        } else {
                          setFormData({ ...formData, userIds: formData.userIds.filter(uid => uid !== id) });
                        }
                      }}
                      className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary/20"
                    />
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-gray-900">
                        {u.display_name || u.first_name}
                      </span>
                      {u.username && (
                        <span className="text-[10px] text-gray-500">@{u.username}</span>
                      )}
                    </div>
                  </label>
                ))}
                {(formData.teamId ? (getSelectedTeam()?.members || []) : users).length === 0 && (
                  <p className="text-xs text-center py-6 text-gray-400 italic">
                    {t('schedules.modal.no_members')}
                  </p>
                )}
              </div>
            ) : (
              <Select
                value={formData.userIds[0] || ''}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFormData({ ...formData, userIds: [e.target.value] })}
              >
                <option value="">{t('schedules.modal.select_user')}</option>
                {(formData.teamId ? (getSelectedTeam()?.members || []) : users).map(u => (
                  <option key={u.id} value={u.id}>
                    {u.display_name || `${u.first_name} ${u.last_name || ''}`}
                  </option>
                ))}
              </Select>
            )}
            {getSelectedTeam()?.has_shifts && (
              <p className="text-[10px] text-text-muted mt-1 italic">
                {t('common.multi_select_hint', 'Select all users that should be assigned to this day')}
              </p>
            )}
          </div>

          {formData.isBulk ? (
            <div className="grid grid-cols-2 gap-4">
              <Input
                label={`${t('schedules.modal.start_date_label')} *`}
                type="date"
                value={formData.startDate}
                onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
              />
              <Input
                label={`${t('schedules.modal.end_date_label')} *`}
                type="date"
                value={formData.endDate}
                onChange={(e) => setFormData({ ...formData, endDate: e.target.value })}
              />
            </div>
          ) : (
            <Input
              label={`${t('schedules.modal.date_label')} *`}
              type="date"
              value={selectedDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSelectedDate(e.target.value)}
            />
          )}

          {getSelectedTeam()?.has_shifts && !editingDuty && (
            <div className="bg-info-light border border-info-light/50 rounded-lg p-3">
              <p className="text-sm text-info-dark">
                {t('schedules.modal.shifts_enabled_hint')}
              </p>
            </div>
          )}

          <div className="flex gap-3 justify-end pt-4 border-t border-gray-200">
            {editingDuty && (
              <Button
                variant="danger"
                className="mr-auto"
                onClick={async () => {
                  await handleDeleteDuty(editingDuty.id);
                  setIsModalOpen(false);
                }}
              >
                <Icons.Delete size={18} />
                {t('common.delete')}
              </Button>
            )}
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveDuty}
            >
              {t('common.save')}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default SchedulesPage;
