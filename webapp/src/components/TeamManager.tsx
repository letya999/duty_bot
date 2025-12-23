import React, { useState, useEffect } from 'react';
import { Team, User } from '../types';
import { apiService } from '../services/api';
import { useTelegramMainButton, showAlert } from '../hooks/useTelegramWebApp';
import './TeamManager.css';

interface TeamManagerProps {
  selectedDate: string;
}

export const TeamManager: React.FC<TeamManagerProps> = ({ selectedDate }) => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedTeam, setExpandedTeam] = useState<number | null>(null);
  const [teamMembers, setTeamMembers] = useState<{ [key: number]: User[] }>({});
  const mainButton = useTelegramMainButton();

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    setLoading(true);
    try {
      const data = await apiService.getTeams();
      setTeams(data);
    } catch (error) {
      showAlert('Failed to load teams');
      console.error('Failed to load teams:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTeamMembers = async (teamId: number) => {
    if (teamMembers[teamId]) {
      setExpandedTeam(expandedTeam === teamId ? null : teamId);
      return;
    }

    try {
      const members = await apiService.getTeamMembers(teamId);
      setTeamMembers({
        ...teamMembers,
        [teamId]: members,
      });
      setExpandedTeam(teamId);
    } catch (error) {
      showAlert('Failed to load team members');
      console.error('Failed to load team members:', error);
    }
  };

  const handleAssignDuty = async (teamId: number, userId: number) => {
    try {
      await apiService.assignDuty(teamId, userId, selectedDate);
      showAlert(`Duty assigned for ${selectedDate}`);
      // Reload teams to refresh display
      loadTeams();
    } catch (error) {
      showAlert('Failed to assign duty');
      console.error('Failed to assign duty:', error);
    }
  };

  if (loading) {
    return (
      <div className="team-manager">
        <div className="loading">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="team-manager">
      <div className="teams-header">
        <h3>Teams</h3>
        <p className="text-muted">Select a team to assign duties for {selectedDate}</p>
      </div>

      {teams.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">👥</div>
          <p>No teams available</p>
        </div>
      ) : (
        <div className="teams-list">
          {teams.map((team) => (
            <div key={team.id} className="team-card">
              <button
                className="team-header-btn"
                onClick={() => loadTeamMembers(team.id)}
              >
                <div className="team-name">{team.name}</div>
                <div className={`team-toggle ${expandedTeam === team.id ? 'expanded' : ''}`}>
                  ▼
                </div>
              </button>

              {expandedTeam === team.id && teamMembers[team.id] && (
                <div className="team-members">
                  {teamMembers[team.id].length === 0 ? (
                    <div className="empty-members">No members in this team</div>
                  ) : (
                    teamMembers[team.id].map((member) => (
                      <button
                        key={member.id}
                        className="member-btn"
                        onClick={() => handleAssignDuty(team.id, member.id)}
                      >
                        <div className="member-avatar">{member.first_name.charAt(0)}</div>
                        <div className="member-info">
                          <div className="member-name">
                            {member.first_name}
                            {member.last_name && ` ${member.last_name}`}
                          </div>
                          {member.username && (
                            <div className="member-username">@{member.username}</div>
                          )}
                        </div>
                        <div className="assign-btn">+ Assign</div>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
