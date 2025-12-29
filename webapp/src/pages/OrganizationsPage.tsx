import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Building2, Plus, Users, Globe, Trash2, FolderTree, Shield, GitMerge, Check, AlertCircle } from 'lucide-react';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

interface TeamMember {
    id: number;
    username: string | null;
    display_name: string | null;
}

interface Team {
    id: number;
    name: string;
    display_name: string;
    member_count: number;
    workspace_id?: number;
    members?: TeamMember[];
}

interface Workspace {
    id: number;
    name: string;
    workspace_type: string;
    external_id: string;
    organization_id?: number | null;
    teams?: Team[];
}

interface Organization {
    id: number;
    name: string;
    created_at: string;
}

interface UserAccount {
    id: number;
    provider: string;
    provider_id: string;
    username: string | null;
    account_email: string | null;
}

interface UserInOrg {
    id: number;
    display_name: string | null;
    is_superadmin: boolean;
    is_admin: boolean;
    user_accounts: UserAccount[];
}

import { ConsolidationWizard } from '../components/organizations/ConsolidationWizard';
import { UserConsolidationWizard } from '../components/organizations/UserConsolidationWizard';

const OrganizationsPage: React.FC = () => {
    const { t } = useTranslation();

    // Data State
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [orgUsers, setOrgUsers] = useState<UserInOrg[]>([]);
    const [allWorkspaces, setAllWorkspaces] = useState<Workspace[]>([]);

    // UI State
    const [loading, setLoading] = useState(true);
    const [isLoadingAllWorkspaces, setIsLoadingAllWorkspaces] = useState(false);
    const [openWorkspaces, setOpenWorkspaces] = useState<Set<number>>(new Set());
    const [openTeams, setOpenTeams] = useState<Set<number>>(new Set());

    // Modal States
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [newOrgName, setNewOrgName] = useState('');
    const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);
    const [accountModalUser, setAccountModalUser] = useState<number | null>(null);
    const [isWizardOpen, setIsWizardOpen] = useState(false);
    const [isUserWizardOpen, setIsUserWizardOpen] = useState(false);

    // Merge States
    const [isUserMergeModalOpen, setIsUserMergeModalOpen] = useState(false);
    const [mergeSourceUser, setMergeSourceUser] = useState<number | null>(null);
    const [mergeTargetUser, setMergeTargetUser] = useState<number | null>(null);
    const [isTeamMergeModalOpen, setIsTeamMergeModalOpen] = useState(false);
    const [mergeSourceTeam, setMergeSourceTeam] = useState<Team | null>(null);
    const [mergeTargetTeam, setMergeTargetTeam] = useState<number | null>(null);

    // New Account State
    const [newAccountProvider, setNewAccountProvider] = useState('telegram');
    const [newAccountProviderId, setNewAccountProviderId] = useState('');
    const [newAccountUsername, setNewAccountUsername] = useState('');

    useEffect(() => {
        const init = async () => {
            await fetchOrganizations();
            await fetchAllWorkspaces();
        };
        init();
    }, []);

    const fetchOrganizations = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch('/api/admin/organizations', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                setOrganizations(await response.json());
            }
        } catch (error) {
            console.error('Failed to fetch orgs:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchAllWorkspaces = async () => {
        setIsLoadingAllWorkspaces(true);
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch('/api/admin/organizations/workspaces/all', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                setAllWorkspaces(await response.json());
            }
        } catch (error) {
            console.error('Failed to fetch all workspaces:', error);
        } finally {
            setIsLoadingAllWorkspaces(false);
        }
    };

    const fetchOrgDetails = async (orgId: number) => {
        const token = localStorage.getItem('session_token');
        try {
            const [wsRes, usersRes] = await Promise.all([
                fetch(`/api/admin/organizations/${orgId}/workspaces`, { headers: { 'Authorization': `Bearer ${token}` } }),
                fetch(`/api/admin/organizations/${orgId}/users`, { headers: { 'Authorization': `Bearer ${token}` } })
            ]);

            if (wsRes.ok) setWorkspaces(await wsRes.json());
            if (usersRes.ok) setOrgUsers(await usersRes.json());
        } catch (error) {
            console.error('Failed to fetch org details:', error);
        }
    };

    const fetchWorkspaceTeams = async (workspaceId: number) => {
        const token = localStorage.getItem('session_token');
        try {
            const response = await fetch(`/api/admin/teams/workspace/${workspaceId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const teams = await response.json();
                const teamsWithWs = teams.map((t: Team) => ({ ...t, workspace_id: workspaceId }));
                setAllWorkspaces(prev => prev.map(ws => ws.id === workspaceId ? { ...ws, teams: teamsWithWs } : ws));
                setWorkspaces(prev => prev.map(ws => ws.id === workspaceId ? { ...ws, teams: teamsWithWs } : ws));
            }
        } catch (error) {
            console.error('Failed to fetch teams:', error);
        }
    };

    const toggleTeams = (workspaceId: number) => {
        const newOpen = new Set(openWorkspaces);
        if (newOpen.has(workspaceId)) {
            newOpen.delete(workspaceId);
        } else {
            newOpen.add(workspaceId);
            fetchWorkspaceTeams(workspaceId);
        }
        setOpenWorkspaces(newOpen);
    };

    const toggleTeamExpansion = (teamId: number, e: React.MouseEvent) => {
        e.stopPropagation();
        const newOpen = new Set(openTeams);
        if (newOpen.has(teamId)) {
            newOpen.delete(teamId);
        } else {
            newOpen.add(teamId);
        }
        setOpenTeams(newOpen);
    };

    const handleCreateOrg = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch('/api/admin/organizations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ name: newOrgName })
            });
            if (response.ok) {
                setIsCreateModalOpen(false);
                setNewOrgName('');
                fetchOrganizations();
            }
        } catch (error) {
            console.error('Failed to create org:', error);
        }
    };

    const handleConnectWorkspace = async (workspaceId: number, orgId: number) => {
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch(`/api/admin/organizations/${orgId}/workspaces/${workspaceId}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                await fetchAllWorkspaces();
                if (selectedOrg?.id === orgId) fetchOrgDetails(orgId);
            }
        } catch (error) {
            console.error('Failed to connect:', error);
        }
    };

    const handleDisconnectWorkspace = async (workspaceId: number) => {
        if (!selectedOrg) return;
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch(`/api/admin/organizations/${selectedOrg.id}/workspaces/${workspaceId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                await fetchAllWorkspaces();
                fetchOrgDetails(selectedOrg.id);
            }
        } catch (error) {
            console.error('Failed to disconnect:', error);
        }
    };

    const handleAddAccount = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedOrg || !accountModalUser) return;
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch(`/api/admin/organizations/${selectedOrg.id}/users/${accountModalUser}/accounts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({
                    provider: newAccountProvider,
                    provider_id: newAccountProviderId,
                    username: newAccountUsername
                })
            });
            if (response.ok) {
                setIsAccountModalOpen(false);
                setNewAccountProviderId('');
                setNewAccountUsername('');
                fetchOrgDetails(selectedOrg.id);
            }
        } catch (error) {
            console.error('Failed to add account:', error);
        }
    };

    const handleMergeUsers = async () => {
        if (!selectedOrg || !mergeSourceUser || !mergeTargetUser) return;
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch(`/api/admin/organizations/${selectedOrg.id}/users/merge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({
                    target_user_id: mergeTargetUser,
                    source_user_id: mergeSourceUser
                })
            });
            if (response.ok) {
                setIsUserMergeModalOpen(false);
                setMergeSourceUser(null);
                setMergeTargetUser(null);
                fetchOrgDetails(selectedOrg.id);
            }
        } catch (error) {
            console.error('Failed to merge users:', error);
        }
    };

    const handleMergeTeams = async () => {
        if (!selectedOrg || !mergeSourceTeam || !mergeTargetTeam) return;
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch(`/api/admin/organizations/${selectedOrg.id}/teams/merge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({
                    target_team_id: mergeTargetTeam,
                    source_team_id: mergeSourceTeam.id
                })
            });
            if (response.ok) {
                setIsTeamMergeModalOpen(false);
                setMergeSourceTeam(null);
                setMergeTargetTeam(null);
                fetchOrgDetails(selectedOrg.id);
            }
        } catch (error) {
            console.error('Failed to merge teams:', error);
        }
    };

    if (loading) return <div className="flex justify-center p-12"><LoadingSpinner size="lg" /></div>;

    const allOrgTeams = workspaces.flatMap(ws => ws.teams || []).filter((t, i, a) => a.findIndex(t2 => t2.id === t.id) === i);

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">{t('organizations.title')}</h1>
                    <p className="text-gray-500 mt-1">{t('organizations.subtitle')}</p>
                </div>
                <button
                    onClick={() => setIsCreateModalOpen(true)}
                    className="flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-xl hover:bg-blue-700 transition-all shadow-lg shadow-blue-200 font-bold"
                >
                    <Plus size={20} />
                    {t('organizations.new_org')}
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                <div className="lg:col-span-1 space-y-4">
                    <div className="flex items-center gap-2 px-1">
                        <Building2 size={18} className="text-blue-500" />
                        <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest">{t('organizations.select_header')}</h2>
                    </div>
                    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden divide-y divide-gray-100">
                        {organizations.length === 0 ? (
                            <div className="p-8 text-center text-gray-400 text-sm italic">{t('organizations.no_orgs')}</div>
                        ) : (
                            organizations.map(org => (
                                <button
                                    key={org.id}
                                    onClick={() => {
                                        setSelectedOrg(org);
                                        fetchOrgDetails(org.id);
                                    }}
                                    className={`w-full text-left px-5 py-4 transition-all group ${selectedOrg?.id === org.id
                                        ? 'bg-blue-50 border-l-4 border-l-blue-600'
                                        : 'hover:bg-gray-50'
                                        }`}
                                >
                                    <div className="font-bold text-gray-900 group-hover:text-blue-700 transition-colors">{org.name}</div>
                                    <div className="text-[10px] text-gray-400 mt-1 flex items-center gap-2">
                                        <span className="bg-gray-100 px-1.5 py-0.5 rounded">ID: {org.id}</span>
                                        <span>•</span>
                                        <span>{new Date(org.created_at).toLocaleDateString()}</span>
                                    </div>
                                </button>
                            ))
                        )}
                    </div>
                </div>

                <div className="lg:col-span-3 space-y-8">
                    {selectedOrg ? (
                        <div className="space-y-8">
                            <div className="bg-white rounded-3xl border border-gray-200 shadow-xl overflow-hidden">
                                <div className="bg-gradient-to-r from-gray-900 to-gray-800 p-8 text-white">
                                    <div className="flex items-center gap-2 text-blue-400 mb-2">
                                        <Shield size={16} />
                                        <span className="text-xs font-bold uppercase tracking-widest">{t('organizations.active_label')}</span>
                                    </div>
                                    <h2 className="text-4xl font-black">{selectedOrg.name}</h2>
                                    <div className="mt-4 flex gap-6 text-sm text-gray-400">
                                        <div className="flex items-center gap-2"><Globe size={14} /> {workspaces.length} {t('organizations.workspaces')}</div>
                                        <div className="flex items-center gap-2"><Users size={14} /> {orgUsers.length} {t('organizations.team_members')}</div>
                                    </div>

                                    <div className="mt-8 flex gap-4">
                                        <button
                                            onClick={() => setIsWizardOpen(true)}
                                            className="px-6 py-3 bg-white text-gray-900 rounded-xl font-bold uppercase tracking-widest hover:bg-gray-100 transition-all flex items-center gap-2 shadow-lg"
                                        >
                                            <GitMerge size={18} />
                                            {t('organizations.consolidate_btn')}
                                        </button>
                                        <button
                                            onClick={() => setIsUserWizardOpen(true)}
                                            className="px-6 py-3 bg-white text-gray-900 rounded-xl font-bold uppercase tracking-widest hover:bg-gray-100 transition-all flex items-center gap-2 shadow-lg"
                                        >
                                            <Users size={18} />
                                            {t('organizations.unify_ids_btn')}
                                        </button>
                                    </div>
                                </div>
                                <ConsolidationWizard
                                    isOpen={isWizardOpen}
                                    onClose={() => setIsWizardOpen(false)}
                                    organization={selectedOrg}
                                    onComplete={() => {
                                        setIsWizardOpen(false);
                                        fetchOrgDetails(selectedOrg.id);
                                    }}
                                />
                                <UserConsolidationWizard
                                    isOpen={isUserWizardOpen}
                                    onClose={() => setIsUserWizardOpen(false)}
                                    organization={selectedOrg}
                                    onComplete={() => {
                                        setIsUserWizardOpen(false);
                                        fetchOrgDetails(selectedOrg.id);
                                    }}
                                />

                                <div className="p-8 space-y-10">
                                    <section>
                                        <div className="flex items-center justify-between mb-4">
                                            <h3 className="text-lg font-bold text-gray-900">Connected Hubs</h3>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {workspaces.map(ws => (
                                                <div key={ws.id} className="group border border-gray-100 bg-gray-50 rounded-2xl overflow-hidden hover:border-blue-200 hover:bg-white transition-all hover:shadow-lg">
                                                    <div className="p-4 flex items-center justify-between">
                                                        <div className="flex items-center gap-4">
                                                            <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white font-black text-xl ${ws.workspace_type === 'telegram' ? 'bg-sky-500' : 'bg-purple-500'}`}>
                                                                {ws.workspace_type[0].toUpperCase()}
                                                            </div>
                                                            <div>
                                                                <div className="font-bold text-gray-900">{ws.name}</div>
                                                                <div className="text-[10px] text-gray-500 uppercase font-black tracking-tighter opacity-60">{ws.external_id}</div>
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <button
                                                                onClick={() => toggleTeams(ws.id)}
                                                                className={`p-2 rounded-lg ${openWorkspaces.has(ws.id) ? 'bg-blue-600 text-white' : 'bg-white text-gray-400 hover:text-blue-500 border border-gray-100'}`}
                                                            >
                                                                <FolderTree size={18} />
                                                            </button>
                                                            <button
                                                                onClick={() => handleDisconnectWorkspace(ws.id)}
                                                                className="p-2 bg-white text-gray-400 hover:text-red-500 border border-gray-100 rounded-lg"
                                                            >
                                                                <Trash2 size={18} />
                                                            </button>
                                                        </div>
                                                    </div>
                                                    {openWorkspaces.has(ws.id) && (
                                                        <div className="px-4 pb-4 bg-white border-t border-gray-50 pt-4">
                                                            <div className="grid grid-cols-2 gap-2">
                                                                {ws.teams?.map(team => (
                                                                    <div
                                                                        key={team.id}
                                                                        className={`p-3 bg-gray-50 rounded-xl border border-gray-100 group/team relative cursor-pointer hover:bg-white hover:border-blue-100 transition-all ${openTeams.has(team.id) ? 'ring-2 ring-blue-500/20 bg-blue-50/10' : ''}`}
                                                                        onClick={(e) => toggleTeamExpansion(team.id, e)}
                                                                    >
                                                                        <div className="text-xs font-bold text-gray-800 truncate">{team.display_name}</div>
                                                                        <div className="text-[10px] text-gray-400 mt-1">{team.member_count} members</div>
                                                                        <button
                                                                            onClick={(e) => { e.stopPropagation(); setMergeSourceTeam(team); setIsTeamMergeModalOpen(true); }}
                                                                            className="absolute top-2 right-2 p-1 text-gray-400 hover:text-purple-600 transition-all z-10"
                                                                            title="Merge Team"
                                                                        >
                                                                            <GitMerge size={12} />
                                                                        </button>

                                                                        {openTeams.has(team.id) && team.members && (
                                                                            <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                                                                                {team.members.length > 0 ? (
                                                                                    team.members.map(member => (
                                                                                        <div key={member.id} className="flex items-center gap-2 text-[10px] text-gray-600 bg-white p-1.5 rounded-lg border border-gray-100">
                                                                                            <div className="w-5 h-5 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full flex items-center justify-center text-[8px] font-bold text-blue-700">
                                                                                                {member.display_name?.[0]?.toUpperCase() || '?'}
                                                                                            </div>
                                                                                            <span className="truncate">{member.display_name || 'Unknown'}</span>
                                                                                        </div>
                                                                                    ))
                                                                                ) : (
                                                                                    <div className="text-[10px] text-gray-400 italic px-1">No members</div>
                                                                                )}
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                ))}
                                                                {!ws.teams && <div className="col-span-2 py-4 flex justify-center"><LoadingSpinner size="sm" /></div>}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </section>

                                    <section>
                                        <h3 className="text-lg font-bold text-gray-900 mb-4">Organization Officers</h3>
                                        <div className="border border-gray-100 rounded-2xl overflow-hidden shadow-sm">
                                            <table className="min-w-full divide-y divide-gray-100">
                                                <thead className="bg-gray-50">
                                                    <tr>
                                                        <th className="px-6 py-3 text-left text-[10px] font-black text-gray-400 uppercase tracking-widest">{t('organizations.officers.member_col')}</th>
                                                        <th className="px-6 py-3 text-left text-[10px] font-black text-gray-400 uppercase tracking-widest">{t('organizations.officers.identity_col')}</th>
                                                        <th className="px-6 py-3 text-left text-[10px] font-black text-gray-400 uppercase tracking-widest">{t('organizations.officers.roles_col')}</th>
                                                        <th className="px-6 py-3 text-right text-[10px] font-black text-gray-400 uppercase tracking-widest">{t('organizations.officers.actions_col')}</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-gray-100 bg-white">
                                                    {orgUsers.map(user => (
                                                        <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                                                            <td className="px-6 py-4">
                                                                <div className="font-bold text-gray-900">{user.display_name || `Anonymous #${user.id}`}</div>
                                                                <div className="text-[10px] text-gray-400">UID: {user.id}</div>
                                                            </td>
                                                            <td className="px-6 py-4">
                                                                <div className="flex flex-wrap gap-2 mb-2">
                                                                    {user.user_accounts.map(acc => (
                                                                        <span key={acc.id} className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-black bg-blue-50 text-blue-600 border border-blue-100">
                                                                            {acc.provider === 'telegram' ? '✈️' : '⚡'} @{acc.username || acc.provider_id.slice(0, 8)}
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                                <button
                                                                    onClick={() => { setAccountModalUser(user.id); setIsAccountModalOpen(true); }}
                                                                    className="text-[10px] font-bold text-blue-600 hover:bg-blue-50 px-2 py-0.5 rounded transition-colors uppercase"
                                                                >
                                                                    + Map Account
                                                                </button>
                                                            </td>
                                                            <td className="px-6 py-4">
                                                                <div className="flex flex-col gap-1.5 items-start">
                                                                    {user.is_superadmin && (
                                                                        <span className="px-2 py-0.5 bg-red-100 text-red-700 text-[9px] font-black rounded-md border border-red-200 uppercase tracking-widest">SUPER</span>
                                                                    )}
                                                                    {user.is_admin && (
                                                                        <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-[9px] font-black rounded-md border border-indigo-200 uppercase tracking-widest">ADMIN</span>
                                                                    )}
                                                                </div>
                                                            </td>
                                                            <td className="px-6 py-4 text-right">
                                                                <button
                                                                    onClick={() => { setMergeSourceUser(user.id); setIsUserMergeModalOpen(true); }}
                                                                    className="text-purple-600 hover:bg-purple-50 p-2 rounded-lg transition-colors inline-flex items-center gap-2 text-xs font-bold uppercase"
                                                                >
                                                                    <GitMerge size={16} />
                                                                    Merge
                                                                </button>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </section>
                                </div>
                            </div>

                            <div className="bg-white rounded-3xl border border-gray-200 shadow-xl p-8">
                                <div className="flex items-center justify-between mb-8">
                                    <div>
                                        <h3 className="text-2xl font-black text-gray-900 uppercase tracking-tight">{t('organizations.infrastructure_hub.title')}</h3>
                                        <p className="text-sm text-gray-500">{t('organizations.infrastructure_hub.subtitle')}</p>
                                    </div>
                                    <Globe size={40} className="text-gray-100" />
                                </div>

                                <div className="space-y-4">
                                    {isLoadingAllWorkspaces && allWorkspaces.length === 0 ? (
                                        <div className="flex justify-center p-12"><LoadingSpinner size="md" /></div>
                                    ) : (
                                        allWorkspaces.map(ws => (
                                            <div key={ws.id} className="border border-gray-100 rounded-2xl overflow-hidden group hover:shadow-xl transition-all">
                                                <div className="bg-gray-50 p-6 flex items-center justify-between group-hover:bg-white transition-colors">
                                                    <div className="flex items-center gap-6">
                                                        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-white font-black text-2xl shadow-lg ${ws.workspace_type === 'telegram' ? 'bg-sky-500 shadow-sky-100' : 'bg-purple-500 shadow-purple-100'}`}>
                                                            {ws.workspace_type[0].toUpperCase()}
                                                        </div>
                                                        <div>
                                                            <div className="text-xl font-bold text-gray-900">{ws.name}</div>
                                                            <div className="text-[11px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-3 mt-1">
                                                                <span>{ws.workspace_type} {t('organizations.infrastructure_hub.cluster')}</span>
                                                                <span className="w-1 h-1 bg-gray-300 rounded-full" />
                                                                <span>CID: {ws.external_id}</span>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center gap-4">
                                                        {ws.organization_id ? (
                                                            <div className="text-right">
                                                                <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none mb-1">{t('organizations.infrastructure_hub.assigned_to')}</div>
                                                                <div className="px-3 py-1 bg-emerald-50 text-emerald-600 text-sm font-bold rounded-lg border border-emerald-100">
                                                                    {organizations.find(o => o.id === ws.organization_id)?.name || `Org #${ws.organization_id}`}
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <div className="px-3 py-1 bg-yellow-50 text-yellow-600 text-[10px] font-black rounded-lg border border-yellow-100 uppercase tracking-widest">{t('organizations.infrastructure_hub.unassigned')}</div>
                                                        )}

                                                        <div className="h-10 w-[1px] bg-gray-100 mx-2" />

                                                        {ws.organization_id !== selectedOrg.id && (
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleConnectWorkspace(ws.id, selectedOrg.id); }}
                                                                className="px-4 py-2 bg-gray-900 text-white text-xs font-black rounded-xl hover:bg-black transition-all shadow-lg shadow-gray-200 uppercase tracking-widest"
                                                            >
                                                                Move to {selectedOrg.name}
                                                            </button>
                                                        )}

                                                        <button
                                                            onClick={() => toggleTeams(ws.id)}
                                                            className={`p-3 rounded-xl transition-all ${openWorkspaces.has(ws.id) ? 'bg-blue-600 text-white shadow-lg shadow-blue-100' : 'bg-gray-100 text-gray-400 hover:bg-gray-200'}`}
                                                        >
                                                            <Building2 size={24} />
                                                        </button>
                                                    </div>
                                                </div>

                                                {openWorkspaces.has(ws.id) && (
                                                    <div className="p-6 bg-white border-t border-gray-50">
                                                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                                            {ws.teams?.map(team => (
                                                                <div key={team.id} className="p-4 border border-gray-50 bg-gray-50 rounded-2xl hover:bg-white hover:border-blue-100 hover:shadow-lg transition-all group/team relative">
                                                                    <div className="font-bold text-gray-900 mb-2 truncate group-hover/team:text-blue-600 transition-colors uppercase tracking-tight text-sm">{team.display_name}</div>
                                                                    <div className="flex items-center gap-2 text-[11px] font-black text-gray-400">
                                                                        <Users size={12} />
                                                                        <span>{team.member_count} Members</span>
                                                                    </div>
                                                                    <button
                                                                        onClick={() => { setMergeSourceTeam({ ...team, workspace_id: ws.id }); setIsTeamMergeModalOpen(true); }}
                                                                        className="absolute top-4 right-4 p-2 text-gray-400 hover:text-purple-600 transition-all bg-white rounded-lg border border-gray-100 shadow-sm"
                                                                        title="Merge Team"
                                                                    >
                                                                        <GitMerge size={16} />
                                                                    </button>
                                                                    {/* This simplified team view in All Hubs doesn't need expansion yet, or can follow same pattern if prioritized */}
                                                                </div>
                                                            ))}
                                                            {!ws.teams && <div className="col-span-full py-12 flex flex-col items-center gap-4 text-blue-500 font-bold"><LoadingSpinner size="md" /><span>{t('organizations.infrastructure_hub.syncing')}</span></div>}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="h-[600px] flex flex-col items-center justify-center text-gray-400 bg-gray-50 border-4 border-dashed border-gray-200 rounded-[3rem] animate-pulse">
                            <Building2 size={80} className="mb-4 opacity-10" />
                            <p className="text-xl font-black uppercase tracking-widest opacity-20">{t('organizations.infrastructure_hub.select_entity')}</p>
                        </div>
                    )}
                </div>
            </div>

            {/* User Merge Modal */}
            {isUserMergeModalOpen && mergeSourceUser && (
                <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-md flex items-center justify-center z-[100] p-4">
                    <div className="bg-white rounded-[2rem] shadow-2xl max-w-lg w-full p-8 border border-white/20">
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h3 className="text-2xl font-black text-gray-900 uppercase">Consolidate Identity</h3>
                                <p className="text-sm text-gray-500">Merge User #{mergeSourceUser} into another record</p>
                            </div>
                            <button onClick={() => { setIsUserMergeModalOpen(false); setMergeSourceUser(null); setMergeTargetUser(null); }} className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100">
                                <Plus size={24} className="rotate-45 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-4 max-h-[400px] overflow-y-auto px-1">
                            <div className="p-4 bg-amber-50 border border-amber-100 rounded-2xl flex gap-4 items-start mb-4">
                                <AlertCircle className="text-amber-600 shrink-0" size={20} />
                                <div className="text-xs text-amber-900 font-bold leading-relaxed uppercase tracking-tight">
                                    Warning: All accounts, schedules, and team memberships will be transferred to the target user. The source user will be deleted.
                                </div>
                            </div>

                            {orgUsers.filter(u => u.id !== mergeSourceUser).map(user => (
                                <button
                                    key={user.id}
                                    onClick={() => setMergeTargetUser(user.id)}
                                    className={`w-full p-4 rounded-2xl border-2 transition-all text-left flex items-center justify-between ${mergeTargetUser === user.id ? 'border-blue-600 bg-blue-50 shadow-md' : 'border-gray-100 hover:border-blue-200 bg-gray-50'}`}
                                >
                                    <div>
                                        <div className="font-bold text-gray-900">{user.display_name || 'Anonymous'}</div>
                                        <div className="text-[10px] text-gray-400 font-black uppercase tracking-widest">UID: {user.id} • {user.user_accounts.length} Links</div>
                                    </div>
                                    {mergeTargetUser === user.id && <Check className="text-blue-600" size={20} />}
                                </button>
                            ))}
                        </div>

                        <div className="mt-8 flex gap-4">
                            <button
                                onClick={() => { setIsUserMergeModalOpen(false); setMergeSourceUser(null); setMergeTargetUser(null); }}
                                className="flex-1 px-6 py-4 bg-gray-100 text-gray-600 rounded-2xl font-black uppercase tracking-widest hover:bg-gray-200 transition-all"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleMergeUsers}
                                disabled={!mergeTargetUser}
                                className="flex-2 px-6 py-4 bg-purple-600 text-white rounded-2xl font-black uppercase tracking-widest hover:bg-purple-700 transition-all shadow-xl shadow-purple-100 disabled:opacity-50 disabled:bg-gray-400"
                            >
                                Initiate Merge
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Team Merge Modal */}
            {isTeamMergeModalOpen && mergeSourceTeam && (
                <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-md flex items-center justify-center z-[100] p-4">
                    <div className="bg-white rounded-[2rem] shadow-2xl max-w-lg w-full p-8 border border-white/20">
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h3 className="text-2xl font-black text-gray-900 uppercase">Unify Formations</h3>
                                <p className="text-sm text-gray-500">Merge "{mergeSourceTeam.display_name}" into target team</p>
                            </div>
                            <button onClick={() => { setIsTeamMergeModalOpen(false); setMergeSourceTeam(null); setMergeTargetTeam(null); }} className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100">
                                <Plus size={24} className="rotate-45 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-4 max-h-[400px] overflow-y-auto px-1">
                            <div className="p-4 bg-amber-50 border border-amber-100 rounded-2xl flex gap-4 items-start mb-4">
                                <AlertCircle className="text-amber-600 shrink-0" size={20} />
                                <div className="text-xs text-amber-900 font-bold leading-relaxed uppercase tracking-tight">
                                    All members, schedules, and configurations will be moved to the target team. Source team will be decommissioned.
                                </div>
                            </div>

                            {allOrgTeams.filter(t => t.id !== mergeSourceTeam.id).map(team => (
                                <button
                                    key={team.id}
                                    onClick={() => setMergeTargetTeam(team.id)}
                                    className={`w-full p-4 rounded-2xl border-2 transition-all text-left flex items-center justify-between ${mergeTargetTeam === team.id ? 'border-blue-600 bg-blue-50 shadow-md' : 'border-gray-100 hover:border-blue-200 bg-gray-50'}`}
                                >
                                    <div>
                                        <div className="font-bold text-gray-900">{team.display_name}</div>
                                        <div className="text-[10px] text-gray-400 font-black uppercase tracking-widest">Team ID: {team.id} • {team.member_count} Members</div>
                                    </div>
                                    {mergeTargetTeam === team.id && <Check className="text-blue-600" size={20} />}
                                </button>
                            ))}
                        </div>

                        <div className="mt-8 flex gap-4">
                            <button
                                onClick={() => { setIsTeamMergeModalOpen(false); setMergeSourceTeam(null); setMergeTargetTeam(null); }}
                                className="flex-1 px-6 py-4 bg-gray-100 text-gray-600 rounded-2xl font-black uppercase tracking-widest hover:bg-gray-200 transition-all"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleMergeTeams}
                                disabled={!mergeTargetTeam}
                                className="flex-2 px-6 py-4 bg-blue-900 text-white rounded-2xl font-black uppercase tracking-widest hover:bg-black transition-all shadow-xl shadow-blue-100 disabled:opacity-50 disabled:bg-gray-400"
                            >
                                Initialize Unification
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {isAccountModalOpen && (
                <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-md flex items-center justify-center z-[100] p-4">
                    <div className="bg-white rounded-[2rem] shadow-2xl max-w-md w-full p-8 border border-white/20">
                        <div className="flex justify-between items-center mb-8">
                            <h3 className="text-2xl font-black text-gray-900 uppercase">Map Identity</h3>
                            <button onClick={() => setIsAccountModalOpen(false)} className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors">
                                <Plus size={24} className="rotate-45 text-gray-400" />
                            </button>
                        </div>
                        <form onSubmit={handleAddAccount} className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest px-1">Network Provider</label>
                                <select
                                    value={newAccountProvider}
                                    onChange={e => setNewAccountProvider(e.target.value)}
                                    className="w-full px-5 py-4 bg-gray-50 border-2 border-transparent rounded-2xl focus:border-blue-500 focus:bg-white outline-none transition-all font-bold text-gray-900"
                                >
                                    <option value="telegram">TELEGRAM NETWORK</option>
                                    <option value="slack">SLACK CLUSTER</option>
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest px-1">Physical Identity ID</label>
                                <input
                                    type="text"
                                    required
                                    value={newAccountProviderId}
                                    onChange={e => setNewAccountProviderId(e.target.value)}
                                    placeholder="Numerical or Platform UUID"
                                    className="w-full px-5 py-4 bg-gray-50 border-2 border-transparent rounded-2xl focus:border-blue-500 focus:bg-white outline-none transition-all font-bold text-gray-900"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest px-1">Alias (Optional)</label>
                                <input
                                    type="text"
                                    value={newAccountUsername}
                                    onChange={e => setNewAccountUsername(e.target.value)}
                                    placeholder="Reference Username"
                                    className="w-full px-5 py-4 bg-gray-50 border-2 border-transparent rounded-2xl focus:border-blue-500 focus:bg-white outline-none transition-all font-bold text-gray-900"
                                />
                            </div>
                            <button
                                type="submit"
                                className="w-full bg-blue-600 text-white py-4 rounded-2xl font-black uppercase tracking-widest hover:bg-blue-700 transition-all shadow-xl shadow-blue-100"
                            >
                                Establish Link
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {isCreateModalOpen && (
                <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-md flex items-center justify-center z-[100] p-4">
                    <div className="bg-white rounded-[2rem] shadow-2xl max-w-md w-full p-8 border border-white/20">
                        <div className="flex justify-between items-center mb-8">
                            <h3 className="text-2xl font-black text-gray-900 uppercase">New Strategic Entity</h3>
                            <button onClick={() => setIsCreateModalOpen(false)} className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors">
                                <Plus size={24} className="rotate-45 text-gray-400" />
                            </button>
                        </div>
                        <form onSubmit={handleCreateOrg} className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest px-1">Entity Name</label>
                                <input
                                    type="text"
                                    required
                                    value={newOrgName}
                                    onChange={e => setNewOrgName(e.target.value)}
                                    placeholder="Enter Organization Name"
                                    className="w-full px-5 py-4 bg-gray-50 border-2 border-transparent rounded-2xl focus:border-blue-500 focus:bg-white outline-none transition-all font-bold text-gray-900"
                                />
                            </div>
                            <button
                                type="submit"
                                className="w-full bg-gray-900 text-white py-4 rounded-2xl font-black uppercase tracking-widest hover:bg-black transition-all shadow-xl shadow-gray-200"
                            >
                                Initalize Entity
                            </button>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default OrganizationsPage;
