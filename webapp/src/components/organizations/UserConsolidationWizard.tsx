import React, { useState, useEffect } from 'react';
import { Users, ArrowRight, Check, X, AlertCircle, Edit2 } from 'lucide-react';
import { LoadingSpinner } from '../ui/LoadingSpinner';

interface UserAccount {
    id: number;
    provider: string;
    username: string;
    account_email: string;
}

interface User {
    id: number;
    display_name: string | null;
    is_superadmin: boolean;
    user_accounts: UserAccount[];
}

interface Organization {
    id: number;
    name: string;
}

interface UserConsolidationWizardProps {
    isOpen: boolean;
    onClose: () => void;
    organization: Organization;
    onComplete: () => void;
}

export const UserConsolidationWizard: React.FC<UserConsolidationWizardProps> = ({
    isOpen,
    onClose,
    organization,
    onComplete
}) => {
    const [loading, setLoading] = useState(true);
    const [users, setUsers] = useState<User[]>([]);

    // Map of TargetUserID -> Array of SourceUserIDs
    const [userMerges, setUserMerges] = useState<Record<number, number[]>>({});

    const [editingUserId, setEditingUserId] = useState<number | null>(null);
    const [editNameValue, setEditNameValue] = useState('');
    const [savingName, setSavingName] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchUsers();
        }
    }, [isOpen, organization.id]);

    const fetchUsers = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('session_token');
            const res = await fetch(`/api/admin/organizations/${organization.id}/users`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Failed to fetch users');
            const data = await res.json();
            // Deduplicate users by ID
            const uniqueUsers = Array.from(new Map(data.map((u: any) => [u.id, u])).values());
            setUsers(uniqueUsers as User[]);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const getConsumedUserIds = () => {
        return Object.values(userMerges).flat();
    };

    const handleToggleMerge = (targetUserId: number, sourceUserId: number) => {
        setUserMerges(prev => {
            const currentSources = prev[targetUserId] || [];
            if (currentSources.includes(sourceUserId)) {
                // Remove
                const next = currentSources.filter(id => id !== sourceUserId);
                return { ...prev, [targetUserId]: next };
            } else {
                // Add
                // Ensure sourceUserId isn't used elsewhere
                const cleaned = { ...prev };
                Object.keys(cleaned).forEach(key => {
                    const k = Number(key);
                    cleaned[k] = cleaned[k].filter(id => id !== sourceUserId);
                });
                return {
                    ...cleaned,
                    [targetUserId]: [...(cleaned[targetUserId] || []), sourceUserId]
                };
            }
        });
    };

    const handleEditName = (user: User) => {
        setEditingUserId(user.id);
        setEditNameValue(user.display_name || 'Unnamed');
    };

    const saveName = async (userId: number) => {
        setSavingName(true);
        try {
            const token = localStorage.getItem('session_token');
            const res = await fetch(`/api/admin/users/${userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ display_name: editNameValue })
            });

            if (res.ok) {
                const updated = await res.json();
                setUsers(prev => prev.map(u => u.id === userId ? { ...u, display_name: updated.display_name } : u));
                setEditingUserId(null);
            }
        } catch (error) {
            console.error("Failed to update name", error);
        } finally {
            setSavingName(false);
        }
    };

    const executeUserMerges = async () => {
        setLoading(true);
        const token = localStorage.getItem('session_token');
        try {
            for (const [targetIdStr, sourceIds] of Object.entries(userMerges)) {
                const targetId = Number(targetIdStr);
                for (const sourceId of sourceIds) {
                    await fetch(`/api/admin/organizations/${organization.id}/users/merge`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({
                            target_user_id: targetId,
                            source_user_id: sourceId
                        })
                    });
                }
            }
            onComplete();
        } catch (error) {
            console.error("Merge failed", error);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    const consumedIds = getConsumedUserIds();
    const validTargets = users.filter(u => !consumedIds.includes(u.id));

    return (
        <div className="fixed inset-0 bg-gray-900/90 backdrop-blur-sm flex items-center justify-center z-[200] p-4">
            <div className="bg-white rounded-[2rem] shadow-2xl w-full max-w-5xl h-[80vh] flex flex-col overflow-hidden">
                {/* Header */}
                <div className="bg-gray-50 border-b border-gray-100 p-8 flex justify-between items-center">
                    <div>
                        <h2 className="text-3xl font-black text-gray-900 uppercase tracking-tight">Identity Unification Wizard</h2>
                        <div className="flex items-center gap-2 mt-2">
                            <span className="px-2 py-1 rounded text-xs font-bold uppercase bg-blue-600 text-white">Merge Users & Accounts</span>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-gray-200 rounded-full transition-colors">
                        <X size={24} className="text-gray-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-8 relative">
                    <div className="space-y-6">
                        <div className="p-4 bg-blue-50 border border-blue-100 rounded-2xl flex gap-4 items-center">
                            <AlertCircle className="text-blue-600" />
                            <p className="text-sm font-bold text-blue-900">Select users to merge. Combine duplicate profiles into a single identity. Accounts (Slack, Telegram) will be unified.</p>
                        </div>

                        {loading ? (
                            <div className="flex justify-center p-20"><LoadingSpinner size="lg" /></div>
                        ) : (
                            <div className="space-y-2">
                                {validTargets.map(targetUser => (
                                    <div key={targetUser.id} className="group border border-gray-100 rounded-2xl p-4 hover:border-blue-200 hover:shadow-lg transition-all">
                                        <div className="flex flex-col md:flex-row gap-6 items-start md:items-center">
                                            {/* Target User Card */}
                                            <div className="w-full md:w-1/3 p-4 bg-gray-50 rounded-xl border border-gray-100">
                                                <div className="flex justify-between items-start">
                                                    {editingUserId === targetUser.id ? (
                                                        <div className="flex gap-2 w-full">
                                                            <input
                                                                className="flex-1 px-2 py-1 text-sm border rounded"
                                                                value={editNameValue}
                                                                onChange={(e) => setEditNameValue(e.target.value)}
                                                                autoFocus
                                                            />
                                                            <button onClick={() => saveName(targetUser.id)} disabled={savingName} className="p-1 bg-green-500 text-white rounded"><Check size={14} /></button>
                                                        </div>
                                                    ) : (
                                                        <div className="font-black text-gray-900 text-lg group-hover/edit:text-blue-600 transition-colors flex items-center gap-2">
                                                            {targetUser.display_name || 'Unnamed User'}
                                                            <button
                                                                onClick={() => handleEditName(targetUser)}
                                                                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-all text-gray-400"
                                                                title="Edit Display Name"
                                                            >
                                                                <Edit2 size={12} />
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>

                                                <div className="text-xs text-gray-400 font-bold uppercase tracking-wider mt-1 mb-2">
                                                    ID: {targetUser.id}
                                                </div>

                                                <div className="flex flex-wrap gap-1">
                                                    {targetUser.user_accounts.map(acc => (
                                                        <div key={acc.id} className="text-[10px] bg-white border border-gray-200 px-2 py-1 rounded inline-flex items-center gap-1 text-gray-500">
                                                            <span className="capitalize font-bold">{acc.provider}</span>: {acc.username}
                                                        </div>
                                                    ))}
                                                    {targetUser.user_accounts.length === 0 && <span className="text-[10px] text-gray-400 italic">No linked accounts</span>}
                                                </div>
                                                <div className="mt-2 text-[10px] bg-white border border-gray-200 px-2 py-1 rounded inline-block text-gray-500">
                                                    Primary Identity
                                                </div>
                                            </div>

                                            <ArrowRight className="text-gray-300 hidden md:block" />

                                            {/* Sources Multi-Select */}
                                            <div className="flex-1 w-full">
                                                <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 px-1">Merge these profiles into {targetUser.display_name}</div>
                                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[200px] overflow-y-auto pr-2">
                                                    {users
                                                        .filter(u => u.id !== targetUser.id)
                                                        .map(sourceUser => {
                                                            const isSelected = (userMerges[targetUser.id] || []).includes(sourceUser.id);
                                                            const isConsumedByOther = getConsumedUserIds().includes(sourceUser.id) && !isSelected;
                                                            if (isConsumedByOther) return null;

                                                            return (
                                                                <button
                                                                    key={sourceUser.id}
                                                                    onClick={() => handleToggleMerge(targetUser.id, sourceUser.id)}
                                                                    className={`text-left p-3 rounded-xl border transition-all flex items-center justify-between ${isSelected
                                                                        ? 'bg-blue-600 border-blue-600 text-white shadow-md'
                                                                        : 'bg-white border-gray-100 text-gray-600 hover:border-blue-300 hover:bg-blue-50'
                                                                        }`}
                                                                >
                                                                    <div className="truncate pr-2 w-full">
                                                                        <div className="font-bold text-sm truncate">{sourceUser.display_name || 'Unnamed'}</div>
                                                                        {sourceUser.user_accounts.length > 0 ? (
                                                                            <div className="text-[10px] opacity-70 truncate">
                                                                                {sourceUser.user_accounts.map(a => a.provider).join(', ')}
                                                                            </div>
                                                                        ) : <div className="text-[10px] opacity-70 italic">No accounts</div>}
                                                                    </div>
                                                                    {isSelected && <Check size={16} />}
                                                                </button>
                                                            );
                                                        })}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                {validTargets.length === 0 && (
                                    <div className="text-center p-12 text-gray-400 italic">No users available.</div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="bg-white border-t border-gray-100 p-6 flex justify-end gap-4">
                    <div className="mr-auto flex items-center gap-2 text-sm text-gray-500">
                        <Users size={16} />
                        <span>{getConsumedUserIds().length} profiles queued for merge</span>
                    </div>
                    <button onClick={executeUserMerges} disabled={getConsumedUserIds().length === 0} className="px-8 py-4 bg-blue-600 text-white font-bold rounded-2xl uppercase tracking-widest hover:bg-blue-700 transition-all shadow-xl shadow-blue-100 disabled:opacity-50 disabled:grayscale">
                        Merge & Finish
                    </button>
                </div>
            </div>
        </div>
    );
};
