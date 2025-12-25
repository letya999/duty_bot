import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { BarChart3, Calendar, Home, LogOut, Menu, Settings, X, Users, AlertCircle, ChevronDown } from 'lucide-react';
import { User } from '../types';

interface Workspace {
  id: number;
  name: string;
  type: string;
  is_current: boolean;
  is_admin: boolean;
  role: string;
}

const Navigation: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [isWorkspaceSwitcherOpen, setIsWorkspaceSwitcherOpen] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace | null>(null);
  const user: User | null = JSON.parse(localStorage.getItem('user') || 'null');

  // Load available workspaces on mount
  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    try {
      const token = localStorage.getItem('session_token');
      const response = await fetch('/web/auth/workspaces', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setWorkspaces(data.workspaces);
        const current = data.workspaces.find((w: Workspace) => w.is_current);
        setCurrentWorkspace(current || null);
      }
    } catch (error) {
      console.error('Failed to load workspaces:', error);
    }
  };

  const handleSwitchWorkspace = async (workspaceId: number) => {
    try {
      const token = localStorage.getItem('session_token');
      const response = await fetch('/web/auth/switch-workspace', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({ workspace_id: workspaceId }),
      });

      if (response.ok) {
        const data = await response.json();
        // Store new token and reload
        localStorage.setItem('session_token', data.session_token);
        // Close switcher and reload page to get new workspace data
        setIsWorkspaceSwitcherOpen(false);
        window.location.href = '/';
      } else {
        console.error('Failed to switch workspace');
      }
    } catch (error) {
      console.error('Error switching workspace:', error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('session_token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <Home size={20} /> },
    { path: '/schedules', label: 'Schedules', icon: <Calendar size={20} /> },
    ...(user?.is_admin ? [
      { path: '/teams', label: 'Teams', icon: <Users size={20} /> },
      { path: '/escalations', label: 'Escalations', icon: <AlertCircle size={20} /> },
    ] : []),
    { path: '/reports', label: 'Reports', icon: <BarChart3 size={20} /> },
    ...(user?.is_admin ? [{ path: '/settings', label: 'Settings', icon: <Settings size={20} /> }] : []),
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="md:hidden fixed bottom-4 right-4 z-40 bg-blue-600 text-white p-3 rounded-full shadow-lg"
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Sidebar */}
      <nav
        className={`${isOpen ? 'translate-x-0' : '-translate-x-full'
          } md:translate-x-0 fixed md:relative w-64 h-screen bg-white border-r border-gray-200 flex flex-col transition-transform duration-300 z-30`}
      >
        {/* Logo */}
        <div className="px-6 py-4 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-blue-600">🎯 Duty Bot</h1>
        </div>

        {/* Nav items */}
        <div className="flex-1 overflow-y-auto">
          <ul className="py-4">
            {navItems.map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  onClick={() => setIsOpen(false)}
                  className={`flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors ${isActive(item.path)
                    ? 'text-blue-600 bg-blue-50 border-r-4 border-blue-600'
                    : 'text-gray-700 hover:bg-gray-50'
                    }`}
                >
                  {item.icon}
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* User section */}
        {user && (
          <div className="border-t border-gray-200 p-4">
            <div className="mb-4">
              <p className="text-sm font-semibold text-gray-900">
                {user.first_name} {user.last_name || ''}
              </p>
              <p className="text-xs text-gray-500">@{user.username}</p>
              {user.is_admin && (
                <span className="inline-block mt-2 px-2 py-1 bg-purple-100 text-purple-700 text-xs font-semibold rounded">
                  Admin
                </span>
              )}
            </div>

            {/* Workspace Switcher - show only if multiple workspaces */}
            {workspaces.length > 1 && (
              <div className="mb-4">
                <div className="relative">
                  <button
                    onClick={() => setIsWorkspaceSwitcherOpen(!isWorkspaceSwitcherOpen)}
                    className="w-full flex items-center justify-between gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 text-gray-700 rounded-lg transition-colors text-xs font-medium border border-gray-200"
                  >
                    <span className="truncate">
                      {currentWorkspace?.name || 'Workspace'}
                    </span>
                    <ChevronDown size={14} />
                  </button>

                  {/* Workspace dropdown menu */}
                  {isWorkspaceSwitcherOpen && (
                    <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                      {workspaces.map((workspace) => (
                        <button
                          key={workspace.id}
                          onClick={() => handleSwitchWorkspace(workspace.id)}
                          disabled={workspace.is_current}
                          className={`w-full text-left px-3 py-2 text-xs font-medium transition-colors ${workspace.is_current
                            ? 'bg-blue-50 text-blue-700 border-l-2 border-blue-600'
                            : 'text-gray-700 hover:bg-gray-50'
                            } ${workspace !== workspaces[workspaces.length - 1] ? 'border-b border-gray-100' : ''}`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="font-medium">{workspace.name}</div>
                              <div className="text-xs text-gray-500 mt-0.5">
                                {workspace.type === 'telegram' ? '✈️ Telegram' : '⚡ Slack'} • {workspace.role}
                              </div>
                            </div>
                            {workspace.is_current && <span className="text-green-600">✓</span>}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg transition-colors text-sm font-medium"
            >
              <LogOut size={18} />
              Logout
            </button>
          </div>
        )}
      </nav>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black bg-opacity-50 z-20"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
};

export default Navigation;
