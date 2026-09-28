'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { EmptyState, ErrorState, LoadingRows, Section, StatusBadge } from '@/components/governance/primitives';
import { RefreshIcon, TrashIcon, XMarkIcon } from '@/components/shell/icons';

interface ModalState {
  isOpen: boolean;
  type: 'add_admin' | 'create_user' | 'delete_user' | 'delete_mind' | 'grant_mind_access' | 'grant_env_access' | 'manage_env_access' | 'confirm_action';
  data?: any;
}

/**
 * Administrative surface.
 *
 * Every handler in this component used to `console.error` and stop. An admin
 * clicking "Add Admin" on an address that already exists, or with a token that
 * had expired, saw the modal stay open and nothing else — indistinguishable from
 * a dead button. Failures now surface in the panel.
 *
 * Also renamed: the "Create New User" form asked for a username and generated a
 * random password that was never shown to anyone, so the account it created
 * could not be signed into by its owner. It sets an explicit password now.
 */
export default function AdminPanel() {
  const [admins, setAdmins] = useState<string[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [minds, setMinds] = useState<any[]>([]);
  const [envs, setEnvs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalState>({ isOpen: false, type: 'add_admin' });

  // Form states
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('user');
  const [selectedMind, setSelectedMind] = useState<string>('');
  const [selectedUser, setSelectedUser] = useState<string>('');
  const [selectedEnv, setSelectedEnv] = useState<string>('');
  const [mindAccessList, setMindAccessList] = useState<string[]>([]);

  const loadAll = async () => {
    setError(null);
    try {
      const [a, u, m, e] = await Promise.all([
        api.listGlobalAdmins(),
        api.adminListUsers(),
        api.adminListMinds(),
        api.adminListEnvs(),
      ]);
      setAdmins(a?.admins || []);
      setUsers(u?.users || []);
      setMinds(m?.minds || []);
      setEnvs(e?.environments || []);

      const firstMind = (m?.minds || [])[0]?.gmid ?? '';
      setSelectedMind((current) => current || firstMind);
    } catch (err: any) {
      setError(err?.message || 'Could not load the admin data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  /**
   * Run a mutation, surfacing either outcome.
   *
   * A single helper rather than a try/catch repeated in nine handlers, each of
   * which previously swallowed its error.
   */
  const run = async (label: string, action: () => Promise<any>, onSuccess?: () => void) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(`${label} — done.`);
      await loadAll();
      onSuccess?.();
    } catch (err: any) {
      setError(`${label} failed: ${err?.message ?? 'unknown error'}`);
    } finally {
      setBusy(false);
    }
  };

  const handleCreateUser = () =>
    run(
      'Create user',
      () => api.adminCreateUser(username, password, email, role),
      () => {
        setUsername('');
        setEmail('');
        setPassword('');
        setRole('user');
        setModal({ isOpen: false, type: 'create_user' });
      }
    );

  const handleAddAdmin = () =>
    run('Add global admin', () => api.addGlobalAdmin(email), () => {
      setEmail('');
      setModal({ isOpen: false, type: 'add_admin' });
    });

  const handleRemoveAdmin = (adminEmail: string) =>
    run('Remove global admin', () => api.removeGlobalAdmin(adminEmail));

  const handleDeleteUser = (name: string) =>
    run('Delete user', () => api.adminDeleteUser(name), () =>
      setModal({ isOpen: false, type: 'delete_user' })
    );

  const handleGrantMindAccess = (gmid: string) =>
    run('Grant access', () => api.adminGrantMindUser(gmid, email), () => {
      setEmail('');
      setModal({ isOpen: false, type: 'grant_mind_access' });
    });

  const handleGrantEnvAccess = (envId: string) =>
    run('Grant access', () => api.adminGrantEnvUser(envId, email), () => {
      setEmail('');
      setModal({ isOpen: false, type: 'grant_env_access' });
    });

  const handleToggleMindPublic = (gmid: string, current: boolean) =>
    run(current ? 'Make private' : 'Make public', () => api.setMindPublic(gmid, !current));

  const handleToggleEnvPublic = (envId: string, current: boolean) =>
    run(current ? 'Make private' : 'Make public', () => api.setEnvPublic(envId, !current));

  const handleDeleteMind = (gmid: string) =>
    run('Delete Mind', () => api.deleteMind(gmid), () => {
      setModal({ isOpen: false, type: 'delete_mind' });
      setSelectedMind('');
    });

  const handleRevokeMindAccess = (gmid: string, userEmail: string) =>
    run('Revoke access', async () => {
      await api.adminRevokeMindUser(gmid, userEmail);
      const res = await api.getMindAccess(gmid);
      setMindAccessList(res?.allowed_users || []);
    });

  const openModal = (type: ModalState['type'], data?: any) => {
    setError(null);
    setNotice(null);
    setModal({ isOpen: true, type, data });
  };

  const closeModal = () => {
    setModal({ isOpen: false, type: 'add_admin' });
    setEmail('');
    setUsername('');
    setPassword('');
    setRole('user');
  };

  if (loading) {
    return <LoadingRows rows={4} label="Loading the admin surface" />;
  }

  const selectedMindRecord = minds.find((m) => m.gmid === selectedMind);
  const selectedEnvRecord = envs.find((e) => e.env_id === selectedEnv);

  return (
    <div className="space-y-6">
      {error && <ErrorState message={error} onRetry={loadAll} />}
      {notice && (
        <div
          role="status"
          className="rounded-card border border-success/40 bg-success/5 p-3 text-sm text-fg"
        >
          {notice}
        </div>
      )}

      <Section title="Users" description="Accounts that can sign in to this installation.">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="card space-y-3">
            <h3 className="section-title">Create a user</h3>
            <div>
              <label htmlFor="new-username" className="label mb-1.5 block">
                Username
              </label>
              <input
                id="new-username"
                type="text"
                placeholder="jsmith"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input w-full"
              />
            </div>
            <div>
              <label htmlFor="new-email" className="label mb-1.5 block">
                Email
              </label>
              <input
                id="new-email"
                type="email"
                placeholder="jsmith@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input w-full"
              />
            </div>
            <div>
              <label htmlFor="new-password" className="label mb-1.5 block">
                Password
              </label>
              <input
                id="new-password"
                type="password"
                placeholder="At least 12 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input w-full"
                autoComplete="new-password"
              />
              <p className="mt-1.5 text-xs text-fg-subtle">
                You choose this and pass it to the person. There is no generated password and no
                email delivery, so if you do not record it the account is unusable — the previous
                form generated a random password and never showed it to anyone.
              </p>
            </div>
            <div>
              <label htmlFor="new-role" className="label mb-1.5 block">
                Role
              </label>
              <select
                id="new-role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="input w-full"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
                <option value="readonly">Read only</option>
              </select>
            </div>
            <button
              type="button"
              onClick={() => openModal('create_user')}
              disabled={!username || !email || password.length < 12 || busy}
              className="btn-primary w-full justify-center"
            >
              Create user
            </button>
          </div>

          <div className="card space-y-3">
            <h3 className="section-title">Manage</h3>
            <div>
              <label htmlFor="pick-user" className="label mb-1.5 block">
                Existing user
              </label>
              <select
                id="pick-user"
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
                className="input w-full"
              >
                <option value="">Select a user…</option>
                {users.map((u) => (
                  <option key={u.username} value={u.username}>
                    {u.username} ({u.email || 'no email'}) — {u.role}
                  </option>
                ))}
              </select>
            </div>

            {users.length === 0 && (
              <p className="text-sm text-fg-subtle">
                No users recorded. Note that accounts live in process memory and are lost on
                restart, so this list can be empty even on an installation that has been used.
              </p>
            )}

            {selectedUser && (
              <button
                type="button"
                className="btn-ghost text-danger"
                onClick={() => {
                  const user = users.find((u) => u.username === selectedUser);
                  if (user) {
                    openModal('delete_user', { username: user.username, email: user.email });
                  }
                }}
              >
                <TrashIcon className="h-4 w-4" />
                Delete this user
              </button>
            )}
          </div>
        </div>
      </Section>

      <Section
        title={`Global admins (${admins.length})`}
        description="Full administrative access, including every Mind on this installation."
        actions={
          <button type="button" onClick={() => openModal('add_admin')} className="btn-primary btn-sm">
            Add admin
          </button>
        }
      >
        {admins.length === 0 ? (
          <EmptyState title="No global admins" description="Nobody can administer this install." />
        ) : (
          <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
            {admins.map((a) => (
              <div key={a} className="card-flat flex items-center justify-between gap-3">
                <span className="min-w-0 truncate text-sm text-fg">{a}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveAdmin(a)}
                  disabled={busy}
                  className="btn-ghost btn-sm text-danger"
                  aria-label={`Remove ${a}`}
                >
                  <XMarkIcon className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Minds">
        <div className="card">
          <select
            value={selectedMind}
            onChange={(e) => setSelectedMind(e.target.value)}
            className="input w-full max-w-md"
            aria-label="Select a Mind"
          >
            <option value="">Select a Mind…</option>
            {minds.map((m) => (
              <option key={m.gmid} value={m.gmid}>
                {m.name} ({m.gmid}) — {m.is_public ? 'public' : 'private'}
              </option>
            ))}
          </select>

          {selectedMindRecord && (
            <div className="mt-4 space-y-4">
              <div className="card-flat">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="font-medium text-fg">{selectedMindRecord.name}</h3>
                    <p className="mt-0.5 text-xs text-fg-subtle">
                      Creator: {selectedMindRecord.creator_email || selectedMindRecord.creator || 'N/A'}{' '}
                      · Status: {selectedMindRecord.status}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge tone={selectedMindRecord.is_public ? 'success' : 'neutral'}>
                      {selectedMindRecord.is_public ? 'Public' : 'Private'}
                    </StatusBadge>
                    <button
                      type="button"
                      onClick={() =>
                        handleToggleMindPublic(selectedMindRecord.gmid, selectedMindRecord.is_public)
                      }
                      disabled={busy}
                      className="btn-secondary btn-sm"
                    >
                      Make {selectedMindRecord.is_public ? 'private' : 'public'}
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        openModal('delete_mind', {
                          gmid: selectedMindRecord.gmid,
                          name: selectedMindRecord.name,
                        })
                      }
                      className="btn-ghost btn-sm text-danger"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => openModal('grant_mind_access', { gmid: selectedMind })}
                    className="btn-primary btn-sm"
                  >
                    Grant access
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      run('Load access list', async () => {
                        const res = await api.getMindAccess(selectedMind);
                        setMindAccessList(res?.allowed_users || []);
                      })
                    }
                    disabled={busy}
                    className="btn-secondary btn-sm"
                  >
                    <RefreshIcon className="h-4 w-4" />
                    Show allowed users
                  </button>
                </div>
              </div>

              {mindAccessList.length > 0 && (
                <div>
                  <p className="label mb-2">Allowed users ({mindAccessList.length})</p>
                  <div className="grid gap-2 md:grid-cols-2">
                    {mindAccessList.map((a) => (
                      <div
                        key={a}
                        className="flex items-center justify-between gap-3 rounded-lg border border-line bg-surface-2 px-3 py-2"
                      >
                        <span className="min-w-0 truncate text-sm text-fg">{a}</span>
                        <button
                          type="button"
                          onClick={() => handleRevokeMindAccess(selectedMind, a)}
                          disabled={busy}
                          className="btn-ghost btn-sm text-danger"
                          aria-label={`Revoke ${a}`}
                        >
                          <XMarkIcon className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {minds.length === 0 && (
            <p className="mt-4 text-sm text-fg-subtle">No Minds on this installation yet.</p>
          )}
        </div>
      </Section>

      <Section title="Environments">
        <div className="card">
          <select
            value={selectedEnv}
            onChange={(e) => setSelectedEnv(e.target.value)}
            className="input w-full max-w-md"
            aria-label="Select an environment"
          >
            <option value="">Select an environment…</option>
            {envs.map((e) => (
              <option key={e.env_id} value={e.env_id}>
                {e.name} ({e.env_id}) — {e.is_public ? 'public' : 'private'}
              </option>
            ))}
          </select>

          {selectedEnvRecord && (
            <div className="card-flat mt-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="font-medium text-fg">{selectedEnvRecord.name}</h3>
                  <p className="mt-0.5 text-xs text-fg-subtle">
                    Owner: {selectedEnvRecord.owner_gmid}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone={selectedEnvRecord.is_public ? 'success' : 'neutral'}>
                    {selectedEnvRecord.is_public ? 'Public' : 'Private'}
                  </StatusBadge>
                  <button
                    type="button"
                    onClick={() =>
                      handleToggleEnvPublic(selectedEnvRecord.env_id, selectedEnvRecord.is_public)
                    }
                    disabled={busy}
                    className="btn-secondary btn-sm"
                  >
                    Make {selectedEnvRecord.is_public ? 'private' : 'public'}
                  </button>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => openModal('grant_env_access', { envId: selectedEnv })}
                  className="btn-primary btn-sm"
                >
                  Grant access
                </button>
                <button
                  type="button"
                  onClick={() =>
                    openModal('manage_env_access', {
                      envId: selectedEnv,
                      name: selectedEnvRecord.name,
                    })
                  }
                  className="btn-secondary btn-sm"
                >
                  Manage access
                </button>
              </div>
            </div>
          )}

          {envs.length === 0 && (
            <p className="mt-4 text-sm text-fg-subtle">No environments on this installation yet.</p>
          )}
        </div>
      </Section>

      {modal.isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
          onClick={closeModal}
        >
          <div className="card w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            {modal.type === 'create_user' && (
              <>
                <h2 className="text-base font-semibold text-fg">Create this user?</h2>
                <dl className="mt-4 rounded-card border border-line bg-surface-2 p-4 text-sm">
                  <div className="grid grid-cols-[6rem_1fr] gap-2 py-1">
                    <dt className="text-fg-muted">Username</dt>
                    <dd className="text-fg">{username}</dd>
                  </div>
                  <div className="grid grid-cols-[6rem_1fr] gap-2 py-1">
                    <dt className="text-fg-muted">Email</dt>
                    <dd className="min-w-0 break-words text-fg">{email}</dd>
                  </div>
                  <div className="grid grid-cols-[6rem_1fr] gap-2 py-1">
                    <dt className="text-fg-muted">Role</dt>
                    <dd className="capitalize text-fg">{role}</dd>
                  </div>
                </dl>
                <p className="mt-3 text-xs text-fg-subtle">
                  The password you entered cannot be read back afterwards. Make sure the person has
                  it before you close this.
                </p>
                <div className="mt-6 flex gap-3">
                  <button type="button" onClick={closeModal} className="btn-secondary flex-1 justify-center">
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleCreateUser}
                    disabled={busy}
                    className="btn-primary flex-1 justify-center"
                  >
                    {busy ? 'Creating…' : 'Create user'}
                  </button>
                </div>
              </>
            )}

            {modal.type === 'add_admin' && (
              <>
                <h2 className="text-base font-semibold text-fg">Add a global admin</h2>
                <p className="mt-1 text-sm text-fg-muted">
                  A global admin can read and delete every Mind on this installation.
                </p>
                <div className="mt-4">
                  <label htmlFor="admin-email" className="label mb-1.5 block">
                    Email address
                  </label>
                  <input
                    id="admin-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@example.com"
                    className="input w-full"
                  />
                </div>
                <div className="mt-6 flex gap-3">
                  <button type="button" onClick={closeModal} className="btn-secondary flex-1 justify-center">
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleAddAdmin}
                    disabled={!email || busy}
                    className="btn-primary flex-1 justify-center"
                  >
                    {busy ? 'Adding…' : 'Add admin'}
                  </button>
                </div>
              </>
            )}

            {modal.type === 'delete_user' && (
              <>
                <h2 className="text-base font-semibold text-fg">Delete this user?</h2>
                <p className="mt-2 text-sm text-fg-muted">
                  <span className="font-medium text-fg">{modal.data?.username}</span>
                  {modal.data?.email ? ` (${modal.data.email})` : ''} will lose the ability to sign
                  in. Anything they created stays. This cannot be undone.
                </p>
                <div className="mt-6 flex gap-3">
                  <button type="button" onClick={closeModal} className="btn-secondary flex-1 justify-center">
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteUser(modal.data?.username)}
                    disabled={busy}
                    className="btn-danger flex-1 justify-center"
                  >
                    {busy ? 'Deleting…' : 'Delete user'}
                  </button>
                </div>
              </>
            )}

            {modal.type === 'delete_mind' && (
              <>
                <h2 className="text-base font-semibold text-fg">Delete this Mind?</h2>
                <p className="mt-2 text-sm text-fg-muted">
                  <span className="font-medium text-fg">{modal.data?.name}</span> and its private
                  space are destroyed, including every memory it has accumulated. This cannot be
                  undone.
                </p>
                <div className="mt-6 flex gap-3">
                  <button type="button" onClick={closeModal} className="btn-secondary flex-1 justify-center">
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteMind(modal.data?.gmid)}
                    disabled={busy}
                    className="btn-danger flex-1 justify-center"
                  >
                    {busy ? 'Deleting…' : 'Delete Mind'}
                  </button>
                </div>
              </>
            )}

            {(modal.type === 'grant_mind_access' || modal.type === 'grant_env_access') && (
              <>
                <h2 className="text-base font-semibold text-fg">
                  Grant {modal.type === 'grant_mind_access' ? 'Mind' : 'environment'} access
                </h2>
                <div className="mt-4">
                  <label htmlFor="grant-email" className="label mb-1.5 block">
                    User email
                  </label>
                  <input
                    id="grant-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="user@example.com"
                    className="input w-full"
                  />
                </div>
                <div className="mt-6 flex gap-3">
                  <button type="button" onClick={closeModal} className="btn-secondary flex-1 justify-center">
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      modal.type === 'grant_mind_access'
                        ? handleGrantMindAccess(modal.data?.gmid)
                        : handleGrantEnvAccess(modal.data?.envId)
                    }
                    disabled={!email || busy}
                    className="btn-primary flex-1 justify-center"
                  >
                    {busy ? 'Granting…' : 'Grant access'}
                  </button>
                </div>
              </>
            )}

            {modal.type === 'manage_env_access' && (
              <>
                <h2 className="text-base font-semibold text-fg">Manage environment access</h2>
                <p className="mt-1 text-sm text-fg-muted">
                  Environment: <span className="font-medium text-fg">{modal.data?.name}</span>
                </p>

                <div className="mt-4 space-y-3">
                  <button
                    type="button"
                    onClick={() =>
                      run('Load access', async () => {
                        const res = await api.getEnvAccess(modal.data?.envId);
                        setNotice(
                          `Public: ${res.is_public} · Allowed: ${
                            (res.allowed_users || []).join(', ') || 'nobody'
                          }`
                        );
                      })
                    }
                    disabled={busy}
                    className="btn-secondary w-full justify-start"
                  >
                    Show current access
                  </button>

                  <InlineInvite
                    label="Invite a user"
                    busy={busy}
                    onSubmit={(value) =>
                      run('Invite user', () => api.addEnvUser(modal.data?.envId, value))
                    }
                  />

                  <InlineInvite
                    label="Revoke a user"
                    busy={busy}
                    destructive
                    onSubmit={(value) =>
                      run('Revoke access', () => api.removeEnvUser(modal.data?.envId, value))
                    }
                  />
                </div>

                <div className="mt-6">
                  <button type="button" onClick={closeModal} className="btn-secondary w-full justify-center">
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

/**
 * An email input plus an action, for the environment access modal.
 *
 * Replaces `prompt()`. A browser prompt is not dismissible by keyboard in every
 * context, is suppressed by some embedded browsers, and cannot show validation
 * or a busy state — so the operation could silently not happen.
 */
function InlineInvite({
  label,
  busy,
  destructive = false,
  onSubmit,
}: {
  label: string;
  busy: boolean;
  destructive?: boolean;
  onSubmit: (value: string) => void;
}) {
  const [value, setValue] = useState('');

  return (
    <div className="rounded-card border border-line p-3">
      <label className="label mb-1.5 block">{label}</label>
      <div className="flex gap-2">
        <input
          type="email"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="user@example.com"
          className="input flex-1"
        />
        <button
          type="button"
          onClick={() => {
            if (!value.trim()) return;
            onSubmit(value.trim());
            setValue('');
          }}
          disabled={!value.trim() || busy}
          className={destructive ? 'btn-danger' : 'btn-secondary'}
        >
          {destructive ? 'Revoke' : 'Invite'}
        </button>
      </div>
    </div>
  );
}
