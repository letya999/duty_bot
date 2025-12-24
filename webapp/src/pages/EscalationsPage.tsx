import React, { useEffect, useState } from 'react';
import { Plus, Trash2, X } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { apiService } from '../services/api';
import { Team, User } from '../types';

interface Escalation {
  id: number;
  team_id?: number;
  cto_id: number;
  team?: Team;
  cto_user?: User;
}

interface EscalationFormData {
  teamId: string;
  ctoId: string;
  isGlobal: boolean;
}

const EscalationsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState<EscalationFormData>({
    teamId: '',
    ctoId: '',
    isGlobal: false,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [escalationsData, teamsData, usersData] = await Promise.all([
        apiService.getEscalations(),
        apiService.getTeams(),
        apiService.getAllUsers(),
      ]);
      setEscalations(escalationsData);
      setTeams(teamsData);
      setUsers(usersData);
    } catch (err) {
      console.error('Failed to load data', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = () => {
    setFormData({
      teamId: '',
      ctoId: '',
      isGlobal: false,
    });
    setIsModalOpen(true);
  };

  const handleCreateEscalation = async () => {
    if (!formData.ctoId) return;

    try {
      await apiService.createEscalation({
        team_id: formData.isGlobal ? null : (formData.teamId ? parseInt(formData.teamId) : null),
        cto_id: parseInt(formData.ctoId),
      });
      setIsModalOpen(false);
      loadData();
    } catch (err) {
      console.error('Failed to create escalation', err);
    }
  };

  const handleDeleteEscalation = async (escalationId: number) => {
    if (!window.confirm('Delete this escalation?')) return;
    try {
      await apiService.deleteEscalation(escalationId);
      loadData();
    } catch (err) {
      console.error('Failed to delete escalation', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const globalEscalations = escalations.filter(e => !e.team_id);
  const teamEscalations = escalations.filter(e => e.team_id);

  return (
    <div className="p-8">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Escalations</h1>
          <p className="text-gray-600 mt-2">Manage CTO assignments and escalation paths</p>
        </div>
        <Button onClick={handleOpenModal} variant="primary" size="md">
          <Plus size={20} />
          Add Escalation
        </Button>
      </div>

      {/* Global Escalations */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Global CTO</h2>
        {globalEscalations.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {globalEscalations.map(escalation => (
              <Card key={escalation.id}>
                <CardBody className="flex justify-between items-center">
                  <div>
                    <p className="text-sm text-gray-600">Chief Technical Officer</p>
                    <p className="text-lg font-semibold text-gray-900 mt-1">
                      {escalation.cto_user?.first_name} {escalation.cto_user?.last_name}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteEscalation(escalation.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded"
                  >
                    <Trash2 size={18} />
                  </button>
                </CardBody>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-gray-600">No global CTO assigned</p>
        )}
      </div>

      {/* Team-specific Escalations */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-4">Team Escalations</h2>
        {teamEscalations.length > 0 ? (
          <div className="space-y-4">
            {teams.map(team => {
              const teamEsc = teamEscalations.find(e => e.team_id === team.id);
              return (
                <Card key={team.id}>
                  <CardBody className="flex justify-between items-center">
                    <div className="flex-1">
                      <p className="text-sm text-gray-600">{team.name}</p>
                      {teamEsc ? (
                        <p className="text-lg font-semibold text-gray-900 mt-1">
                          {teamEsc.cto_user?.first_name} {teamEsc.cto_user?.last_name}
                        </p>
                      ) : (
                        <p className="text-gray-500 mt-1">No escalation assigned</p>
                      )}
                    </div>
                    {teamEsc && (
                      <button
                        onClick={() => handleDeleteEscalation(teamEsc.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded"
                      >
                        <Trash2 size={18} />
                      </button>
                    )}
                  </CardBody>
                </Card>
              );
            })}
          </div>
        ) : (
          <p className="text-gray-600">No team-specific escalations yet</p>
        )}
      </div>

      {/* Add Escalation Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Add Escalation"
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.isGlobal}
                onChange={(e) => setFormData({ ...formData, isGlobal: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm font-medium text-gray-700">Global CTO (for all teams)</span>
            </label>
          </div>

          {!formData.isGlobal && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Team *
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
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              CTO User *
            </label>
            <select
              value={formData.ctoId}
              onChange={(e) => setFormData({ ...formData, ctoId: e.target.value })}
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

          <div className="flex gap-3 justify-end pt-4 border-t">
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleCreateEscalation}
              disabled={!formData.ctoId || (!formData.isGlobal && !formData.teamId)}
            >
              Create Escalation
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default EscalationsPage;
