'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface ModalState {
  isOpen: boolean;
  type: 'add_admin' | 'create_user' | 'delete_user' | 'delete_mind' | 'grant_mind_access' | 'grant_env_access' | 'manage_env_access' | 'confirm_action';
  data?: any;
}

export default function AdminPanel() {
  const [admins, setAdmins] = useState<string[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [minds, setMinds] = useState<any[]>([]);
  const [envs, setEnvs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState<ModalState>({ isOpen: false, type: 'add_admin' });

  // Form states
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [role, setRole] = useState('user');
  const [selectedMind, setSelectedMind] = useState<string>('');
  const [selectedUser, setSelectedUser] = useState<string>('');
  const [selectedEnv, setSelectedEnv] = useState<string>('');
  const [mindAccessList, setMindAccessList] = useState<string[]>([]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const a = await api.listGlobalAdmins();
      setAdmins(a.admins || []);
      const u = await api.adminListUsers();
      setUsers(u.users || []);
      const m = await api.adminListMinds();
      setMinds(m.minds || []);
      const e = await api.adminListEnvs();
      setEnvs(e.environments || []);

      // Set default mind selection for access management
      if (m.minds && m.minds.length > 0) {
        setSelectedMind(m.minds[0].gmid);
      } else {
        setSelectedMind('');
      }
    } catch (err) {
      console.error('Admin load error', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleCreateUser = async () => {
    if (!username || !email) return;
    // Generate a random password for Firebase users
    const randomPassword = Math.random().toString(36).slice(-12) + Math.random().toString(36).slice(-12);
    try {
      await api.adminCreateUser(username, randomPassword, email, role);
      setUsername('');
      setEmail('');
      setRole('user');
      setModal({ isOpen: false, type: 'create_user' });
      loadAll();
    } catch (err) {
      console.error('Create user error', err);
    }
  };

  const handleAddAdmin = async () => {
    if (!email) return;
    try {
      await api.addGlobalAdmin(email);
      setEmail('');
      setModal({ isOpen: false, type: 'add_admin' });
      loadAll();
    } catch (err) {
      console.error('Add admin error', err);
    }
  };

  const handleRemoveAdmin = async (adminEmail: string) => {
    try {
      await api.removeGlobalAdmin(adminEmail);
      loadAll();
    } catch (err) {
      console.error('Remove admin error', err);
    }
  };

  const handleDeleteUser = async (username: string) => {
    try {
      await api.adminDeleteUser(username);
      setModal({ isOpen: false, type: 'delete_user' });
      loadAll();
    } catch (err) {
      console.error('Delete user error', err);
    }
  };

  const handleGrantMindAccess = async (gmid: string) => {
    if (!email) return;
    try {
      await api.adminGrantMindUser(gmid, email);
      setEmail('');
      setModal({ isOpen: false, type: 'grant_mind_access' });
      loadAll();
    } catch (err) {
      console.error('Grant mind access error', err);
    }
  };

  const handleGrantEnvAccess = async (envId: string) => {
    if (!email) return;
    try {
      await api.adminGrantEnvUser(envId, email);
      setEmail('');
      setModal({ isOpen: false, type: 'grant_env_access' });
      loadAll();
    } catch (err) {
      console.error('Grant env access error', err);
    }
  };

  const handleToggleMindPublic = async (gmid: string, currentStatus: boolean) => {
    try {
      await api.setMindPublic(gmid, !currentStatus);
      loadAll();
    } catch (err) {
      console.error('Toggle mind public error', err);
    }
  };

  const handleToggleEnvPublic = async (envId: string, currentStatus: boolean) => {
    try {
      await api.setEnvPublic(envId, !currentStatus);
      loadAll();
    } catch (err) {
      console.error('Toggle env public error', err);
    }
  };

  const handleDeleteMind = async (gmid: string) => {
    try {
      await api.deleteMind(gmid);
      setModal({ isOpen: false, type: 'delete_mind' });
      setSelectedMind('');
      loadAll();
    } catch (err) {
      console.error('Delete mind error', err);
    }
  };

  const handleRevokeMindAccess = async (gmid: string, userEmail: string) => {
    try {
      await api.adminRevokeMindUser(gmid, userEmail);
      const res = await api.getMindAccess(gmid);
      setMindAccessList(res.allowed_users || []);
    } catch (err) {
      console.error('Revoke mind access error', err);
    }
  };

  const openModal = (type: ModalState['type'], data?: any) => {
    setModal({ isOpen: true, type, data });
  };

  const closeModal = () => {
    setModal({ isOpen: false, type: 'add_admin' });
    setEmail('');
    setUsername('');
    setRole('user');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner-large"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* User Management Section */}
      <div className="clean-card p-6">
        <h2 className="text-2xl font-semibold text-gray-100 mb-6">User Management</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Create User */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-100">Create New User</h3>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input w-full"
              />
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input w-full"
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="input w-full"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
                <option value="readonly">Read Only</option>
              </select>
              <button
                onClick={() => openModal('create_user')}
                disabled={!username || !email}
                className="btn-primary w-full disabled:opacity-50"
              >
                Create User
              </button>
            </div>
          </div>

          {/* Manage Existing Users */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-100">Manage Users</h3>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="input w-full"
            >
              <option value="">-- Select User --</option>
              {users.map(u => (
                <option key={u.username} value={u.username}>
                  {u.username} ({u.email}) - {u.role}
                </option>
              ))}
            </select>

            {selectedUser && (
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    const user = users.find(u => u.username === selectedUser);
                    if (user) openModal('delete_user', { username: user.username, email: user.email });
                  }}
                  className="btn-ghost text-red-400 hover:text-red-300 flex-1"
                >
                  Delete User
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Global Admins Section */}
      <div className="clean-card p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold text-gray-100">Global Admins</h2>
          <button
            onClick={() => openModal('add_admin')}
            className="btn-primary"
          >
            Add Admin
          </button>
        </div>

        <div className="space-y-3">
          {admins.length ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {admins.map(a => (
                <div key={a} className="flex items-center justify-between py-2 px-3 bg-slate-700/50 rounded-md">
                  <div className="text-gray-200 font-medium truncate">{a}</div>
                  <button
                    onClick={() => handleRemoveAdmin(a)}
                    className="btn-ghost text-red-400 hover:text-red-300 ml-2"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              No global admins configured
            </div>
          )}
        </div>
      </div>

      {/* Minds Management */}
      <div className="clean-card p-6">
        <h2 className="text-2xl font-semibold text-gray-100 mb-6">Minds Management</h2>

        <div className="space-y-4">
          <select
            value={selectedMind}
            onChange={(e) => setSelectedMind(e.target.value)}
            className="input w-full max-w-md"
          >
            <option value="">-- Select Mind --</option>
            {minds.map(m => (
              <option key={m.gmid} value={m.gmid}>
                {m.name} ({m.gmid}) - {m.is_public ? 'Public' : 'Private'}
              </option>
            ))}
          </select>

          {selectedMind && (
            <>
              {/* Mind Details */}
              {(() => {
                const mind = minds.find(m => m.gmid === selectedMind);
                return mind ? (
                  <div className="p-4 bg-slate-700/50 rounded-md">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-medium text-gray-100">{mind.name}</h3>
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 rounded text-xs ${mind.is_public ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                          {mind.is_public ? 'Public' : 'Private'}
                        </span>
                        <button
                          onClick={() => handleToggleMindPublic(mind.gmid, mind.is_public)}
                          className="btn-secondary text-sm"
                        >
                          Make {mind.is_public ? 'Private' : 'Public'}
                        </button>                      <button
                        onClick={() => openModal('delete_mind', { gmid: mind.gmid, name: mind.name })}
                        className="btn-ghost text-red-400 hover:text-red-300 text-sm"
                      >
                        Delete Mind
                      </button>                      </div>
                    </div>
                    <div className="text-sm text-gray-400 mb-4">
                      Creator: {mind.creator} • Status: {mind.status}
                    </div>

                    {/* Mind Actions */}
                    <div className="flex gap-3">
                      <button
                        onClick={() => openModal('grant_mind_access', { gmid: selectedMind })}
                        className="btn-primary"
                      >
                        Grant Access
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            const res = await api.getMindAccess(selectedMind);
                            setMindAccessList(res.allowed_users || []);
                          } catch (err) {
                            console.error('Failed to fetch access list', err);
                          }
                        }}
                        className="btn-secondary"
                      >
                        Show Access List
                      </button>
                    </div>
                  </div>
                ) : null;
              })()}

              {/* Access List */}
              {mindAccessList.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-lg font-medium text-gray-100">Allowed Users</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {mindAccessList.map(a => (
                      <div key={a} className="flex items-center justify-between py-2 px-3 bg-slate-700/50 rounded-md">
                        <div className="text-gray-200 truncate">{a}</div>
                        <button
                          onClick={() => handleRevokeMindAccess(selectedMind, a)}
                          className="btn-ghost text-red-400 hover:text-red-300 ml-2"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Environments Management */}
      <div className="clean-card p-6">
        <h2 className="text-2xl font-semibold text-gray-100 mb-6">Environments Management</h2>

        <div className="space-y-4">
          <select
            value={selectedEnv}
            onChange={(e) => setSelectedEnv(e.target.value)}
            className="input w-full max-w-md"
          >
            <option value="">-- Select Environment --</option>
            {envs.map(e => (
              <option key={e.env_id} value={e.env_id}>
                {e.name} ({e.env_id}) - {e.is_public ? 'Public' : 'Private'}
              </option>
            ))}
          </select>

          {selectedEnv && (
            <>
              {/* Environment Details */}
              {(() => {
                const env = envs.find(e => e.env_id === selectedEnv);
                return env ? (
                  <div className="p-4 bg-slate-700/50 rounded-md">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-medium text-gray-100">{env.name}</h3>
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 rounded text-xs ${env.is_public ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                          {env.is_public ? 'Public' : 'Private'}
                        </span>
                        <button
                          onClick={() => handleToggleEnvPublic(env.env_id, env.is_public)}
                          className="btn-secondary text-sm"
                        >
                          Make {env.is_public ? 'Private' : 'Public'}
                        </button>
                      </div>
                    </div>
                    <div className="text-sm text-gray-400 mb-4">
                      Owner: {env.owner_gmid}
                    </div>

                    {/* Environment Actions */}
                    <div className="flex gap-3">
                      <button
                        onClick={() => openModal('grant_env_access', { envId: selectedEnv })}
                        className="btn-primary"
                      >
                        Grant Access
                      </button>
                      <button
                        onClick={() => openModal('manage_env_access', { envId: selectedEnv, name: env.name })}
                        className="btn-secondary"
                      >
                        Manage Access
                      </button>
                    </div>
                  </div>
                ) : null;
              })()}
            </>
          )}
        </div>
      </div>

      {/* Modal */}
      {modal.isOpen && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={closeModal}>
          <div className="clean-card p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            {modal.type === 'create_user' && (
              <>
                <h2 className="text-xl font-semibold text-white mb-4">Create New User</h2>
                <div className="space-y-4 mb-6">
                  <div>
                    <label className="block text-sm text-gray-300 mb-2">Username</label>
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="username"
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-300 mb-2">Email</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="user@example.com"
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-300 mb-2">Role</label>
                    <select
                      value={role}
                      onChange={(e) => setRole(e.target.value)}
                      className="input w-full"
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                      <option value="readonly">Read Only</option>
                    </select>
                  </div>
                </div>
                <div className="flex gap-3">
                  <button onClick={closeModal} className="flex-1 btn-secondary">
                    Cancel
                  </button>
                  <button
                    onClick={handleCreateUser}
                    disabled={!username || !email}
                    className="flex-1 btn-primary disabled:opacity-50"
                  >
                    Create User
                  </button>
                </div>
              </>
            )}

            {modal.type === 'add_admin' && (
              <>
                <h2 className="text-xl font-semibold text-white mb-4">Add Global Admin</h2>
                <div className="space-y-4 mb-6">
                  <div>
                    <label className="block text-sm text-gray-300 mb-2">Email Address</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="admin@example.com"
                      className="input w-full"
                    />
                  </div>
                </div>
                <div className="flex gap-3">
                  <button onClick={closeModal} className="flex-1 btn-secondary">
                    Cancel
                  </button>
                  <button
                    onClick={handleAddAdmin}
                    disabled={!email}
                    className="flex-1 btn-primary disabled:opacity-50"
                  >
                    Add Admin
                  </button>
                </div>
              </>
            )}

            {modal.type === 'delete_user' && (
              <>
                <h2 className="text-xl font-semibold text-white mb-4">Delete User</h2>
                <p className="text-gray-300 mb-6">
                  Are you sure you want to delete user <strong>{modal.data?.username}</strong> ({modal.data?.email})?
                  This action cannot be undone.
                </p>
                <div className="flex gap-3">
                  <button onClick={closeModal} className="flex-1 btn-secondary">
                    Cancel
                  </button>
                  <button
                    onClick={() => handleDeleteUser(modal.data?.username)}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md transition-colors"
                  >
                    Delete User
                  </button>
                </div>
              </>
            )}

            {modal.type === 'delete_mind' && (
              <>
                <h2 className="text-xl font-semibold text-white mb-4">Delete Mind</h2>
                <p className="text-gray-300 mb-6">
                  Are you sure you want to delete mind <strong>{modal.data?.name}</strong>?
                  This will permanently delete the mind and its associated private space. This action cannot be undone.
                </p>
                <div className="flex gap-3">
                  <button onClick={closeModal} className="flex-1 btn-secondary">
                    Cancel
                  </button>
                  <button
                    onClick={() => handleDeleteMind(modal.data?.gmid)}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md transition-colors"
                  >
                    Delete Mind
                  </button>
                </div>
              </>
            )}

            {(modal.type === 'grant_mind_access' || modal.type === 'grant_env_access') && (
              <>
                <h2 className="text-xl font-semibold text-white mb-4">
                  Grant {modal.type === 'grant_mind_access' ? 'Mind' : 'Environment'} Access
                </h2>
                <div className="space-y-4 mb-6">
                  <div>
                    <label className="block text-sm text-gray-300 mb-2">User Email</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="user@example.com"
                      className="input w-full"
                    />
                  </div>
                </div>
                <div className="flex gap-3">
                  <button onClick={closeModal} className="flex-1 btn-secondary">
                    Cancel
                  </button>
                  <button
                    onClick={() => modal.type === 'grant_mind_access'
                      ? handleGrantMindAccess(modal.data?.gmid)
                      : handleGrantEnvAccess(modal.data?.envId)
                    }
                    disabled={!email}
                    className="flex-1 btn-primary disabled:opacity-50"
                  >
                    Grant Access
                  </button>
                </div>
              </>
            )}

            {modal.type === 'manage_env_access' && (
              <>
                <h2 className="text-xl font-semibold text-white mb-4">Manage Environment Access</h2>
                <p className="text-gray-300 mb-4">Environment: <strong>{modal.data?.name}</strong></p>
                <div className="space-y-3">
                  <button
                    onClick={async () => {
                      try {
                        const res = await api.getEnvAccess(modal.data?.envId);
                        alert(`Public: ${res.is_public}\nAllowed Users: ${res.allowed_users.join(', ')}`);
                      } catch (err) {
                        console.error('Failed to fetch access', err);
                        alert('Failed to fetch access list');
                      }
                    }}
                    className="w-full btn-secondary text-left"
                  >
                    Show Current Access
                  </button>
                  <button
                    onClick={() => {
                      const email = prompt('Email to invite:');
                      if (!email) return;
                      api.addEnvUser(modal.data?.envId, email).then(() => {
                        alert('User invited successfully');
                      }).catch(err => {
                        console.error('Invite failed', err);
                        alert('Invite failed');
                      });
                    }}
                    className="w-full btn-primary text-left"
                  >
                    Invite User
                  </button>
                  <button
                    onClick={() => {
                      const email = prompt('Email to revoke:');
                      if (!email) return;
                      api.removeEnvUser(modal.data?.envId, email).then(() => {
                        alert('Access revoked successfully');
                      }).catch(err => {
                        console.error('Revoke failed', err);
                        alert('Revoke failed');
                      });
                    }}
                    className="w-full bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md transition-colors text-left"
                  >
                    Revoke User Access
                  </button>
                </div>
                <div className="mt-6">
                  <button onClick={closeModal} className="w-full btn-secondary">
                    Close
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}