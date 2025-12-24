import React, { useEffect, useState } from 'react';
import { Plus, Edit2, Trash2, Users, X, Save } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
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
    if (!window.confirm('Delete this team?')) return;
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
      alert('Failed to import member');
    } finally {
      setIsImporting(false);
    }
  };

  const handleMoveMember = async (userId: number, toTeamId: number) => {
    if (!selectedTeamForMembers || !toTeamId) return;

    if (!window.confirm('Move member to another team?')) return;

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
          <h1 className="text-3xl font-bold text-gray-900">Teams</h1>
          <p className="text-gray-600 mt-2">Manage teams and members</p>
        </div>
        <Button onClick={() => handleOpenModal()} variant="primary" size="md">
          <Plus size={20} />
          New Team
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {teams.map(team => (
          <Card key={team.id}>
            <CardHeader className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{team.name}</h3>
                <p className="text-sm text-gray-600 mt-1">{team.description || 'No description'}</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleOpenModal(team)}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                >
                  <Edit2 size={18} />
                </button>
                <button
                  onClick={() => handleDeleteTeam(team.id)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </CardHeader>

            <CardBody>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600 mb-2">Members ({team.members?.length || 0})</p>
                  <div className="flex flex-wrap gap-2">
                    {team.members?.slice(0, 3).map(member => (
                      <span
                        key={member.id}
                        className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded"
                      >
                        {member.first_name}
                      </span>
                    ))}
                    {(team.members?.length || 0) > 3 && (
                      <span className="text-xs text-gray-600">
                        +{(team.members?.length || 0) - 3} more
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex gap-2 pt-3 border-t border-gray-200">
                  <button
                    onClick={() => handleOpenMembersModal(team)}
                    className="flex-1 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded text-gray-700 font-medium flex items-center justify-center gap-2"
                  >
                    <Users size={16} />
                    Manage Members
                  </button>
                </div>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      {teams.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-600 mb-4">No teams yet</p>
          <Button onClick={() => handleOpenModal()} variant="primary">
            Create First Team
          </Button>
        </div>
      )}

      {/* Team Form Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingTeam ? 'Edit Team' : 'Create Team'}
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Team Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Backend Team"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Display Name *
            </label>
            <input
              type="text"
              value={formData.displayName}
              onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Backend Team"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Team Lead (Optional)
            </label>
            <select
              value={formData.teamLeadId}
              onChange={(e) => setFormData({ ...formData, teamLeadId: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select team lead</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.first_name} {user.last_name || ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.hasShifts}
                onChange={(e) => setFormData({ ...formData, hasShifts: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm font-medium text-gray-700">Enable shift mode</span>
            </label>
            <p className="text-xs text-gray-600 mt-1">
              When enabled, multiple users can be assigned to the same day
            </p>
          </div>

          <div className="flex gap-3 justify-end pt-4 border-t">
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveTeam}
              disabled={!formData.name || !formData.displayName}
            >
              {editingTeam ? 'Update' : 'Create'} Team
            </Button>
          </div>
        </div>
      </Modal>

      {/* Members Modal */}
      <Modal
        isOpen={memberModalOpen}
        onClose={() => setMemberModalOpen(false)}
        title={`Manage Members - ${selectedTeamForMembers?.name}`}
        size="md"
      >
        <div className="space-y-4">
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={importHandle}
              onChange={(e) => setImportHandle(e.target.value)}
              placeholder="@username or t.me/link or Slack link"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
            <Button
              size="sm"
              variant="secondary"
              onClick={handleImportMember}
              disabled={!importHandle || isImporting}
            >
              {isImporting ? 'Adding...' : 'Add Member'}
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
                    {user.username ? <span className="text-gray-400 text-xs ml-1">(@{user.username})</span> : ''}
                  </span>
                </label>

                {selectedMembers.includes(user.id) && (
                  <select
                    className="text-xs border border-gray-200 rounded px-1 py-1 text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity focus:opacity-100"
                    onChange={(e) => handleMoveMember(user.id, parseInt(e.target.value))}
                    defaultValue=""
                  >
                    <option value="" disabled>Move to...</option>
                    {teams.filter(t => t.id !== selectedTeamForMembers?.id).map(t => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                )}
              </div>
            ))}
          </div>

          <div className="flex gap-3 justify-end pt-4 border-t">
            <Button variant="secondary" onClick={() => setMemberModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSaveMembers}>
              <Save size={18} />
              Save Members
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default TeamsPage;
