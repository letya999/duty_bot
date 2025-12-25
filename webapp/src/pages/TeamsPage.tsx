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

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [teamsData, usersData] = await Promise.all([
        apiService.getTeams(),
        apiService.getAllUsers(),
      ]);
      setTeams(teamsData);
      setUsers(usersData);
    } catch (err) {
      console.error('Failed to load data', err);
    } finally {
      setLoading(false);
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
      loadData();
    } catch (err) {
      console.error('Failed to save members', err);
    }
  };

  const handleImportMember = async () => {
    if (!selectedTeamForMembers || !importHandle) return;

    try {
      setIsImporting(true);
      await apiService.importTeamMember(selectedTeamForMembers.id, importHandle);
      setImportHandle('');
      loadData();
      // We don't close the modal, so user can see the new member

      // Refresh the selected members list for the current modal? 
      // Actually loadData updates 'teams', but we need to update 'selectedMembers' or 'users'.
      // If we reload data, 'teams' and 'users' update.
      // But 'selectedMembers' state is static ids.
      // We should probably re-init selectedMembers if we want to reflect the change visually immediately? 
      // Or just wait for re-render.
      // Because we fetched new teams, selectedTeamForMembers (which is a reference to old team object) might be stale if we don't update it.
      // But we can just find the team again.
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
                  <p className="text-sm text-text-muted mb-2">{t('teams.members_count')} ({team.members?.length || 0})</p>
                  <div className="flex flex-wrap gap-2">
                    {team.members?.slice(0, 3).map(member => (
                      <span
                        key={member.id}
                        className="text-xs bg-info-light text-info-dark px-2 py-1 rounded"
                      >
                        {member.first_name}
                      </span>
                    ))}
                    {(team.members?.length || 0) > 3 && (
                      <span className="text-xs text-text-muted">
                        +{(team.members?.length || 0) - 3} {t('teams.more_members')}
                      </span>
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
                  {user.first_name} {user.last_name || ''}
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
                <label className="flex items-center gap-2 flex-1 cursor-pointer">
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
                    className="w-4 h-4"
                  />
                  <span className="text-gray-700">
                    {user.first_name} {user.last_name || ''}
                    {user.username ? <span className="text-text-muted text-xs ml-1">(@{user.username})</span> : ''}
                  </span>
                </label>

                {selectedMembers.includes(user.id) && (
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
