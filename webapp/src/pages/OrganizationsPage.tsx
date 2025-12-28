import React, { useState, useEffect } from 'react';
import { Building2, Plus, Users, Globe, ExternalLink } from 'lucide-react';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

interface Organization {
    id: number;
    name: string;
    created_at: string;
}

interface Workspace {
    id: number;
    name: string;
    workspace_type: string;
    external_id: string;
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
    user_accounts: UserAccount[];
}

const OrganizationsPage: React.FC = () => {
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [orgUsers, setOrgUsers] = useState<UserInOrg[]>([]);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [newOrgName, setNewOrgName] = useState('');
    const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);
    const [accountModalUser, setAccountModalUser] = useState<number | null>(null);
    const [newAccountProvider, setNewAccountProvider] = useState('telegram');
    const [newAccountProviderId, setNewAccountProviderId] = useState('');
    const [newAccountUsername, setNewAccountUsername] = useState('');

    useEffect(() => {
        fetchOrganizations();
    }, []);

    const fetchOrganizations = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch('/api/organizations', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (response.ok) {
                const data = await response.json();
                setOrganizations(data);
            }
        } catch (error) {
            console.error('Failed to fetch organizations:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchOrgDetails = async (orgId: number) => {
        const token = localStorage.getItem('session_token');

        // Fetch workspaces
        try {
            const wsRes = await fetch(`/api/organizations/${orgId}/workspaces`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (wsRes.ok) setWorkspaces(await wsRes.json());

            const usersRes = await fetch(`/api/organizations/${orgId}/users`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (usersRes.ok) setOrgUsers(await usersRes.json());
        } catch (error) {
            console.error('Failed to fetch org details:', error);
        }
    };

    const handleCreateOrg = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch('/api/organizations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ name: newOrgName })
            });
            if (response.ok) {
                setIsCreateModalOpen(false);
                setNewOrgName('');
                fetchOrganizations();
            }
        } catch (error) {
            console.error('Failed to create organization:', error);
        }
    };
    const handleAddAccount = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedOrg || !accountModalUser) return;
        try {
            const token = localStorage.getItem('session_token');
            const response = await fetch(`/api/organizations/${selectedOrg.id}/users/${accountModalUser}/accounts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
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

    if (loading) return <div className="flex justify-center p-12"><LoadingSpinner size="lg" /></div>;

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Organizations</h1>
                    <p className="text-gray-500">Manage multi-workspace organizations and shared resources</p>
                </div>
                <button
                    onClick={() => setIsCreateModalOpen(true)}
                    className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                >
                    <Plus size={20} />
                    Create Organization
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Organizations List */}
                <div className="md:col-span-1 space-y-4">
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                        <Building2 size={20} className="text-blue-500" />
                        Organizations List
                    </h2>
                    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                        {organizations.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">No organizations found</div>
                        ) : (
                            organizations.map(org => (
                                <button
                                    key={org.id}
                                    onClick={() => {
                                        setSelectedOrg(org);
                                        fetchOrgDetails(org.id);
                                    }}
                                    className={`w-full text-left px-4 py-3 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors ${selectedOrg?.id === org.id ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''
                                        }`}
                                >
                                    <div className="font-medium text-gray-900">{org.name}</div>
                                    <div className="text-xs text-gray-500 mt-1">ID: {org.id} • Created: {new Date(org.created_at).toLocaleDateString()}</div>
                                </button>
                            ))
                        )}
                    </div>
                </div>

                {/* Organization Details */}
                <div className="md:col-span-2 space-y-6">
                    {selectedOrg ? (
                        <>
                            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                                <h3 className="text-xl font-bold text-gray-900 mb-4">{selectedOrg.name} Details</h3>

                                <div className="space-y-6">
                                    {/* Workspaces Section */}
                                    <div>
                                        <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3 flex items-center gap-2">
                                            <Globe size={16} />
                                            Connected Workspaces
                                        </h4>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                            {workspaces.map(ws => (
                                                <div key={ws.id} className="p-3 bg-gray-50 border border-gray-200 rounded-lg flex items-center justify-between">
                                                    <div>
                                                        <div className="text-sm font-medium">{ws.name}</div>
                                                        <div className="text-xs text-gray-500">{ws.workspace_type} • {ws.external_id}</div>
                                                    </div>
                                                    <ExternalLink size={14} className="text-gray-400" />
                                                </div>
                                            ))}
                                            {workspaces.length === 0 && <div className="col-span-2 text-sm text-gray-500 italic">No workspaces connected</div>}
                                        </div>
                                    </div>

                                    {/* Users Section */}
                                    <div>
                                        <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3 flex items-center gap-2">
                                            <Users size={16} />
                                            Organization Users
                                        </h4>
                                        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                                            <table className="min-w-full divide-y divide-gray-200">
                                                <thead className="bg-gray-50">
                                                    <tr>
                                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Accounts</th>
                                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-gray-200">
                                                    {orgUsers.map(user => (
                                                        <tr key={user.id}>
                                                            <td className="px-4 py-3">
                                                                <div className="text-sm font-medium text-gray-900">{user.display_name || `User ${user.id}`}</div>
                                                                <div className="text-xs text-gray-500">ID: {user.id}</div>
                                                            </td>
                                                            <td className="px-4 py-3">
                                                                <div className="flex flex-wrap gap-1 mb-2">
                                                                    {user.user_accounts.map(acc => (
                                                                        <span key={acc.id} className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-800" title={`Account/Provider ID: ${acc.provider_id}`}>
                                                                            {acc.provider === 'telegram' ? '✈️' : '⚡'} {acc.username || acc.provider_id}
                                                                        </span>
                                                                    ))}
                                                                    {user.user_accounts.length === 0 && <span className="text-xs text-gray-400">No accounts</span>}
                                                                </div>
                                                                <button
                                                                    onClick={() => {
                                                                        setAccountModalUser(user.id);
                                                                        setIsAccountModalOpen(true);
                                                                    }}
                                                                    className="text-[10px] text-blue-600 hover:text-blue-800 font-bold uppercase"
                                                                >
                                                                    + Add Account
                                                                </button>
                                                            </td>
                                                            <td className="px-4 py-3">
                                                                {user.is_superadmin && (
                                                                    <span className="px-2 py-0.5 bg-red-100 text-red-700 text-[10px] font-bold rounded uppercase">SuperAdmin</span>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="h-64 flex flex-col items-center justify-center text-gray-500 bg-gray-50 border-2 border-dashed border-gray-200 rounded-xl">
                            <Building2 size={48} className="mb-2 opacity-20" />
                            <p>Select an organization to view details</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Add Account Modal */}
            {isAccountModalOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100] p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-gray-900">Add User Account</h3>
                            <button onClick={() => setIsAccountModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                                <Plus size={24} className="rotate-45" />
                            </button>
                        </div>
                        <form onSubmit={handleAddAccount}>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
                                    <select
                                        value={newAccountProvider}
                                        onChange={e => setNewAccountProvider(e.target.value)}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                    >
                                        <option value="telegram">Telegram</option>
                                        <option value="slack">Slack</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Account / Provider ID</label>
                                    <input
                                        type="text"
                                        required
                                        value={newAccountProviderId}
                                        onChange={e => setNewAccountProviderId(e.target.value)}
                                        placeholder="e.g. 123456789 or U12345678"
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                    />
                                    <p className="text-[10px] text-gray-500 mt-1">Numerical ID for Telegram, User ID for Slack</p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Username (Optional)</label>
                                    <input
                                        type="text"
                                        value={newAccountUsername}
                                        onChange={e => setNewAccountUsername(e.target.value)}
                                        placeholder="e.g. john_doe"
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                    />
                                </div>
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <button
                                    type="button"
                                    onClick={() => setIsAccountModalOpen(false)}
                                    className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                                >
                                    Add Account
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Create Modal */}
            {isCreateModalOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100] p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-gray-900">Create New Organization</h3>
                            <button onClick={() => setIsCreateModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                                <Plus size={24} className="rotate-45" />
                            </button>
                        </div>
                        <form onSubmit={handleCreateOrg}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">Organization Name</label>
                                <input
                                    type="text"
                                    required
                                    value={newOrgName}
                                    onChange={e => setNewOrgName(e.target.value)}
                                    placeholder="e.g. Acme Corp"
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all outline-none"
                                />
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <button
                                    type="button"
                                    onClick={() => setIsCreateModalOpen(false)}
                                    className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-md shadow-blue-200"
                                >
                                    Create
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default OrganizationsPage;
