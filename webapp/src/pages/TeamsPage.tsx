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
        displayName: team.description || team.name,
        hasShifts: false,
        teamLeadId: '',
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
          <div className="max-h-96 overflow-y-auto border border-gray-300 rounded-lg p-3 space-y-2">
            {users.map(user => (
              <label key={user.id} className="flex items-center gap-2">
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
                <span className="text-gray-700">{user.first_name} {user.last_name || ''}</span>
              </label>
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
