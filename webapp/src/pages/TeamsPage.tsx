import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Icons } from '../components/ui/Icons';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { apiService } from '../services/api';
import { Team, User } from '../types';

interface TeamFormData {
  name: string;
  displayName: string;
  hasShifts: boolean;
  teamLeadId: string;
}

interface EditingTeam extends Team {
  memberIds?: number[];
}

const TeamsPage: React.FC = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTeam, setEditingTeam] = useState<EditingTeam | null>(null);
  const [formData, setFormData] = useState<TeamFormData>({
    name: '',
    displayName: '',
    hasShifts: false,
    teamLeadId: '',
  });

  const [selectedTeamForMembers, setSelectedTeamForMembers] = useState<Team | null>(null);
  const [memberModalOpen, setMemberModalOpen] = useState(false);
  const [selectedMembers, setSelectedMembers] = useState<number[]>([]);
  const [importHandle, setImportHandle] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [editingUser, setEditingUser] = useState<{ id: number; displayName: string } | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const [teamsData, usersData] = await Promise.all([
        apiService.getTeams(),
        apiService.getAllUsers(),
      ]);
      setTeams(teamsData);
      setUsers(usersData);

      // Update selectedTeamForMembers if it's currently open to reflect any changes (e.g. member names)
      if (selectedTeamForMembers) {
        const updatedTeam = teamsData.find(t => t.id === selectedTeamForMembers.id);
        if (updatedTeam) {
          setSelectedTeamForMembers(updatedTeam);
        }
      }
    } catch (err) {
      console.error('Failed to load data', err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const handleOpenModal = (team?: Team) => {
    if (team) {
      setEditingTeam(team);
      setFormData({
        name: team.name,
        displayName: team.display_name || team.name, // Use display_name if available
        hasShifts: team.has_shifts || false,
        teamLeadId: team.team_lead_id ? team.team_lead_id.toString() : '',
      });
    } else {
      setEditingTeam(null);
      setFormData({
        name: '',
        displayName: '',
        hasShifts: false,
        teamLeadId: '',
      });
    }
    setIsModalOpen(true);
  };

  const handleSaveTeam = async () => {
    if (!formData.name || !formData.displayName) return;

    try {
      if (editingTeam) {
        await apiService.updateTeam(editingTeam.id, {
          name: formData.name,
          display_name: formData.displayName,
          has_shifts: formData.hasShifts,
          team_lead_id: formData.teamLeadId ? parseInt(formData.teamLeadId) : null,
        });
      } else {
        await apiService.createTeam({
          name: formData.name,
          display_name: formData.displayName,
          has_shifts: formData.hasShifts,
          team_lead_id: formData.teamLeadId ? parseInt(formData.teamLeadId) : undefined,
        });
      }
      setIsModalOpen(false);
      loadData();
    } catch (err) {
      console.error('Failed to save team', err);
    }
  };

  const handleDeleteTeam = async (teamId: number) => {
    if (!window.confirm(t('teams.delete_confirm'))) return;
    try {
      await apiService.deleteTeam(teamId);
      loadData();
    } catch (err) {
      console.error('Failed to delete team', err);
    }
  };

  const handleOpenMembersModal = (team: Team) => {
    setSelectedTeamForMembers(team);
    setSelectedMembers(team.members?.map(m => m.id) || []);
    setMemberModalOpen(true);
  };

  const handleSaveMembers = async () => {
    if (!selectedTeamForMembers) return;

    try {
      // If there's an active name edit, save it first
      if (editingUser) {
        console.log('[TeamsPage] Saving pending name edit before team save');
        await apiService.updateUser(editingUser.id, { display_name: editingUser.displayName });
        setEditingUser(null);
      }

      const currentMemberIds = selectedTeamForMembers.members?.map(m => m.id) || [];

      // Add new members
      for (const userId of selectedMembers) {
        if (!currentMemberIds.includes(userId)) {
          await apiService.addTeamMember(selectedTeamForMembers.id, userId);
        }
      }

      // Remove members
      for (const userId of currentMemberIds) {
        if (!selectedMembers.includes(userId)) {
          await apiService.removeTeamMember(selectedTeamForMembers.id, userId);
        }
      }

      setMemberModalOpen(false);
      await loadData();
    } catch (err) {
      console.error('Failed to save members', err);
      alert(t('common.error'));
    }
  };

  const handleImportMember = async () => {
    if (!selectedTeamForMembers || !importHandle) return;

    try {
      setIsImporting(true);
      await apiService.importTeamMember(selectedTeamForMembers.id, importHandle);
      setImportHandle('');

      // Refresh all data
      await loadData();

      // Update local state for the modal to show the new member as checked
      const updatedTeams = await apiService.getTeams();
      const updatedTeam = updatedTeams.find(t => t.id === selectedTeamForMembers.id);
      if (updatedTeam) {
        setSelectedTeamForMembers(updatedTeam);
        setSelectedMembers(updatedTeam.members?.map(m => m.id) || []);
      }

    } catch (err) {
      console.error('Failed to import member', err);
      alert(t('teams.import_error'));
    } finally {
      setIsImporting(false);
    }
  };

  const handleMoveMember = async (userId: number, toTeamId: number) => {
    if (!selectedTeamForMembers || !toTeamId) return;

    if (!window.confirm(t('teams.move_confirm'))) return;

    try {
      await apiService.moveTeamMember(userId, selectedTeamForMembers.id, toTeamId);
      loadData();

      // Update local state to remove user from this team
      setSelectedMembers(prev => prev.filter(id => id !== userId));

    } catch (err) {
      console.error('Failed to move member', err);
    }
  };
  const handleRemoveMemberFromTeam = async (teamId: number, userId: number) => {
    if (!window.confirm(t('teams.remove_member_confirm'))) return;
    try {
      await apiService.removeTeamMember(teamId, userId);
      loadData();
    } catch (err) {
      console.error('Failed to remove member from team', err);
      alert(t('common.error'));
    }
  };

  const handleUpdateUserDisplayName = async (userId: number, newName: string) => {
    console.log(`[TeamsPage] Calling handleUpdateUserDisplayName for user ${userId}, newName: "${newName}"`);
    try {
      const response = await apiService.updateUser(userId, { display_name: newName });
      console.log('[TeamsPage] Update successful, response:', response);
      setEditingUser(null);
      await loadData(true); // silent refresh
    } catch (err: any) {
      console.error('[TeamsPage] Failed to update user display name:', err);
      if (err.response) {
        console.error('[TeamsPage] Error response data:', err.response.data);
      }
      alert(t('common.error'));
    }
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
          <h1 className="text-3xl font-bold text-gray-900">{t('teams.title')}</h1>
          <p className="text-gray-600 mt-2">{t('teams.subtitle')}</p>
        </div>
        <Button onClick={() => handleOpenModal()} variant="primary" size="md">
          <Icons.Plus size={20} />
          {t('teams.new_team')}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {teams.map(team => (
          <Card key={team.id}>
            <CardHeader className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{team.name}</h3>
                <p className="text-sm text-text-muted mt-1">{team.description || t('teams.no_description')}</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleOpenModal(team)}
                  className="p-2 text-info hover:bg-info-light rounded"
                >
                  <Icons.Edit size={18} />
                </button>
                <button
                  onClick={() => handleDeleteTeam(team.id)}
                  className="p-2 text-error hover:bg-error-light rounded"
                >
                  <Icons.Delete size={18} />
                </button>
              </div>
            </CardHeader>

            <CardBody>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <p className="text-sm font-semibold text-gray-700">{t('teams.members_count')} ({team.members?.length || 0})</p>
                  </div>
                  <div className="space-y-2">
                    {team.members?.length > 0 ? (
                      team.members.map(member => (
                        <div
                          key={member.id}
                          className={`flex items-center justify-between p-2 bg-gray-50 rounded-lg group/member border transition-all ${team.team_lead_id === member.id ? 'border-primary/20 bg-primary/5' : 'border-transparent hover:border-gray-200'
                            }`}
                        >
                          <div className="flex flex-col min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-gray-900 truncate">
                                {member.display_name || `${member.first_name} ${member.last_name || ''}`}
                              </span>
                              {team.team_lead_id === member.id && (
                                <span className="text-[10px] font-bold bg-primary text-primary-text px-1.5 py-0.5 rounded uppercase tracking-wider">
                                  Lead
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex gap-2 shrink-0 items-center">
                            {member.telegram_username && (
                              <a
                                href={`https://t.me/${member.telegram_username.replace('@', '')}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 text-[10px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full hover:bg-blue-100 transition-colors"
                              >
                                @{member.telegram_username.replace('@', '')}
                                <Icons.ExternalLink size={10} />
                              </a>
                            )}
                            {member.slack_user_id && (
                              <span className="text-[10px] bg-purple-50 text-purple-600 px-2 py-0.5 rounded-full">
                                Slack: {member.slack_user_id}
                              </span>
                            )}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRemoveMemberFromTeam(team.id, member.id);
                              }}
                              className="p-1 text-error hover:bg-error-light rounded opacity-0 group-hover/member:opacity-100 transition-opacity"
                              title={t('common.remove', 'Remove')}
                            >
                              <Icons.X size={14} />
                            </button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-text-muted italic py-2">{t('teams.no_members')}</p>
                    )}
                  </div>
                </div>

                <div className="flex gap-2 pt-3 border-t border-gray-200">
                  <button
                    onClick={() => handleOpenMembersModal(team)}
                    className="flex-1 px-3 py-2 text-sm bg-secondary-bg hover:brightness-95 rounded text-gray-700 font-medium flex items-center justify-center gap-2"
                  >
                    <Icons.Users size={16} />
                    {t('teams.manage_members')}
                  </button>
                </div>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      {teams.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-600 mb-4">{t('teams.no_teams')}</p>
          <Button onClick={() => handleOpenModal()} variant="primary">
            {t('teams.create_first')}
          </Button>
        </div>
      )}

      {/* Team Form Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingTeam ? t('teams.modal.edit_title') : t('teams.modal.create_title')}
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <Input
              label={`${t('teams.modal.name_label')} *`}
              value={formData.name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, name: e.target.value })}
              placeholder={t('teams.modal.name_placeholder')}
            />
          </div>

          <div>
            <Input
              label={`${t('teams.modal.display_name_label')} *`}
              value={formData.displayName}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, displayName: e.target.value })}
              placeholder={t('teams.modal.display_name_placeholder')}
            />
          </div>

          <div>
            <Select
              label={t('teams.modal.lead_label')}
              value={formData.teamLeadId}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFormData({ ...formData, teamLeadId: e.target.value })}
            >
              <option value="">{t('teams.modal.select_lead')}</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.display_name || `${user.first_name} ${user.last_name || ''}`}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.hasShifts}
                onChange={(e) => setFormData({ ...formData, hasShifts: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm font-medium text-gray-700">{t('teams.modal.shift_mode')}</span>
            </label>
            <p className="text-xs text-text-muted mt-1">
              {t('teams.modal.shift_hint')}
            </p>
          </div>

          <div className="flex gap-3 justify-end pt-4 border-t border-gray-200">
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveTeam}
              disabled={!formData.name || !formData.displayName}
            >
              {editingTeam ? t('teams.modal.update_btn') : t('teams.modal.create_btn')}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Members Modal */}
      <Modal
        isOpen={memberModalOpen}
        onClose={() => setMemberModalOpen(false)}
        title={`${t('teams.members_modal.title')} - ${selectedTeamForMembers?.name}`}
        size="md"
      >
        <div className="space-y-4">
          <div className="flex gap-2 mb-4">
            <input // Should be Input probably, but maybe too complex for simple field with side button? Let's use native input with same style or wrap. I'll use native for now but styled. Matches current Input style.
              type="text"
              value={importHandle}
              onChange={(e) => setImportHandle(e.target.value)}
              placeholder={t('teams.members_modal.add_placeholder')}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <Button
              size="sm"
              variant="secondary"
              onClick={handleImportMember}
              disabled={!importHandle || isImporting}
            >
              {isImporting ? t('teams.members_modal.adding') : t('teams.members_modal.add_btn')}
            </Button>
          </div>

          <div className="max-h-96 overflow-y-auto border border-gray-300 rounded-lg p-3 space-y-2">
            {users.map(user => (
              <div key={user.id} className="flex justify-between items-center group">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <input
                    type="checkbox"
                    checked={selectedMembers.includes(user.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedMembers([...selectedMembers, user.id]);
                      } else {
                        setSelectedMembers(selectedMembers.filter(id => id !== user.id));
                      }
                    }}
                    className="w-4 h-4 flex-shrink-0"
                  />
                  {editingUser?.id === user.id ? (
                    <div className="flex items-center gap-1 flex-1">
                      <input
                        type="text"
                        value={editingUser.displayName}
                        onChange={(e) => setEditingUser({ ...editingUser, displayName: e.target.value })}
                        className="flex-1 px-2 py-1 text-sm border border-primary rounded focus:outline-none"
                        autoFocus
                      />
                      <button
                        onClick={() => handleUpdateUserDisplayName(user.id, editingUser.displayName)}
                        className="p-1 text-success hover:bg-success-light rounded"
                      >
                        <Icons.Check size={16} />
                      </button>
                      <button
                        onClick={() => setEditingUser(null)}
                        className="p-1 text-error hover:bg-error-light rounded"
                      >
                        <Icons.X size={16} />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between flex-1 min-w-0">
                      <span className="text-gray-700 truncate">
                        {user.display_name || `${user.first_name} ${user.last_name || ''}`}
                        {!user.display_name && user.username && (
                          <span className="text-text-muted text-xs ml-1">(@{user.username})</span>
                        )}
                      </span>
                      <button
                        onClick={() => setEditingUser({ id: user.id, displayName: user.display_name || user.first_name })}
                        className="p-1 text-text-muted hover:text-info opacity-0 group-hover:opacity-100 transition-opacity"
                        title={t('common.edit')}
                      >
                        <Icons.Edit size={14} />
                      </button>
                    </div>
                  )}
                </div>

                {selectedMembers.includes(user.id) && !editingUser && (
                  <select
                    className="text-xs border border-gray-200 rounded px-1 py-1 text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity focus:opacity-100"
                    onChange={(e) => handleMoveMember(user.id, parseInt(e.target.value))}
                    defaultValue=""
                  >
                    <option value="" disabled>{t('teams.members_modal.move_to')}</option>
                    {teams.filter(t => t.id !== selectedTeamForMembers?.id).map(t => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                )}
              </div>
            ))}
          </div>

          <div className="flex gap-3 justify-end pt-4 border-t border-gray-200">
            <Button variant="secondary" onClick={() => setMemberModalOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button variant="primary" onClick={handleSaveMembers}>
              <Icons.Save size={18} />
              {t('teams.members_modal.save_btn')}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default TeamsPage;
