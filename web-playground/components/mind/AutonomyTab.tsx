'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import {
  EmptyState,
  LoadingRows,
  Section,
  StatusBadge,
} from '@/components/governance/primitives';

interface AutonomyTabProps {
  mindId: string;
  mind?: any; // Optional mind data to avoid redundant API calls
}

interface AutonomousAction {
  action_id: string;
  action_type: string;
  description: string;
  status: string;
  created_at: string;
  completed_at?: string;
  result?: any;
}

export default function AutonomyTab({ mindId, mind }: AutonomyTabProps) {
  const [settings, setSettings] = useState({
    autonomy_level: 5,
    autonomous_actions_enabled: true,
    external_tools_allowed: true,
    require_approval: false,
    max_actions_per_hour: 100,
    max_concurrent_actions: 5,
  });
  const [actions, setActions] = useState<AutonomousAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, [mindId, mind]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Load autonomy settings - use passed mind prop if available to avoid redundant API call
      const mindData = mind || await api.getMind(mindId);
      if (mindData.autonomy) {
        setSettings({
          autonomy_level: mindData.autonomy.initiative_level || 5,
          autonomous_actions_enabled: mindData.autonomy.proactive_actions !== false,
          external_tools_allowed: mindData.autonomy.tool_execution_allowed !== false,
          require_approval: mindData.autonomy.require_user_approval === true,
          max_actions_per_hour: mindData.autonomy.max_actions_per_hour || 100,
          max_concurrent_actions: mindData.autonomy.max_concurrent || 5,
        });
      }
      
      // Load recent autonomous actions (if available)
      try {
        const actionsData = await api.getAutonomousActions(mindId, 20);
        setActions(actionsData.actions || []);
      } catch (err) {
        // Actions endpoint may not exist yet - that's ok
        setActions([]);
      }
    } catch (error) {
      console.error('Error loading autonomy data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateMindSettings(mindId, {
        autonomy: {
          initiative_level: settings.autonomy_level,
          proactive_actions: settings.autonomous_actions_enabled,
          tool_execution_allowed: settings.external_tools_allowed,
          require_user_approval: settings.require_approval,
          max_actions_per_hour: settings.max_actions_per_hour,
          max_concurrent: settings.max_concurrent_actions,
        }
      });
      alert('Autonomy settings saved successfully!');
      await loadData();
    } catch (error: any) {
      alert(`Failed to save settings: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <LoadingRows rows={3} label="Loading autonomy settings" />;
  }

  return (
    <div className="space-y-6">
      <Section
        title="Autonomy"
        description="How much initiative this Mind takes without being asked."
      >
        <div className="card space-y-5">
          <div>
            <label htmlFor="initiative" className="label mb-2 block">
              Initiative level: <span className="tabular-nums text-fg">{settings.autonomy_level}</span>
            </label>
            <input
              id="initiative"
              type="range"
              min="0"
              max="10"
              value={settings.autonomy_level}
              onChange={(e) =>
                setSettings({ ...settings, autonomy_level: parseInt(e.target.value) })
              }
              className="w-full accent-[rgb(var(--accent))]"
            />
            <div className="mt-1 flex justify-between text-xs text-fg-subtle">
              <span>Passive · 0</span>
              <span>Balanced · 5</span>
              <span>Highly proactive · 10</span>
            </div>
          </div>

          <Toggle
            id="proactive"
            label="Autonomous actions"
            hint="Let the Mind act on its own schedule rather than only when you speak to it."
            checked={settings.autonomous_actions_enabled}
            onChange={(v) => setSettings({ ...settings, autonomous_actions_enabled: v })}
          />

          <Toggle
            id="tools"
            label="External tool use"
            hint="Allow plugins and integrations. This widens what the Mind can reach; the governance gate still decides each action."
            checked={settings.external_tools_allowed}
            onChange={(v) => setSettings({ ...settings, external_tools_allowed: v })}
          />

          <Toggle
            id="approval"
            label="Require approval for external actions"
            hint="Queue risky actions for you to approve instead of running them."
            checked={settings.require_approval}
            onChange={(v) => setSettings({ ...settings, require_approval: v })}
          />

          {settings.require_approval && (
            <div className="rounded-card border border-warning/40 bg-warning/5 p-3">
              <p className="text-xs text-fg-muted">
                Worth knowing: this flag is stored, but the approval queue you actually get is
                driven by the <span className="font-medium text-fg">risk classification</span> of
                each action, not by this toggle. A capability declared R3 or above queues for
                approval whether or not this is on, and declaring nothing queues it too — an
                undeclared capability floors at R3. This switch therefore cannot make the Mind more
                permissive than the policy allows.
              </p>
            </div>
          )}

          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="btn-primary w-full justify-center"
          >
            {saving ? 'Saving…' : 'Save settings'}
          </button>
        </div>
      </Section>

      <Section title="Action limits">
        <div className="card divide-y divide-[rgb(var(--border))]">
          <NumberRow
            id="per-hour"
            label="Actions per hour"
            value={settings.max_actions_per_hour}
            min={1}
            max={1000}
            onChange={(v) => setSettings({ ...settings, max_actions_per_hour: v })}
          />
          <NumberRow
            id="concurrent"
            label="Concurrent actions"
            value={settings.max_concurrent_actions}
            min={1}
            max={20}
            onChange={(v) => setSettings({ ...settings, max_concurrent_actions: v })}
          />
        </div>
      </Section>

      <Section title="Recent autonomous actions">
        {actions.length === 0 ? (
          <EmptyState
            title="No autonomous actions yet"
            description="Actions appear here once the daemon has acted on its own. If you expect some and see none, check that the daemon is running on the Overview tab."
          />
        ) : (
          <div className="space-y-3">
            {actions.map((action) => (
              <div key={action.action_id} className="card-flat">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-fg">{action.action_type}</div>
                    <p className="mt-0.5 text-sm text-fg-muted">{action.description}</p>
                  </div>
                  <StatusBadge tone={actionTone(action.status)}>{action.status}</StatusBadge>
                </div>
                <p className="mt-2 text-xs text-fg-subtle">
                  {new Date(action.created_at).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

function actionTone(status: string) {
  if (status === 'completed') return 'success';
  if (status === 'failed') return 'danger';
  return 'warning';
}

function Toggle({
  id,
  label,
  hint,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  hint: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="flex items-center gap-2">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="h-4 w-4 rounded border-line accent-[rgb(var(--accent))]"
        />
        <span className="text-sm font-medium text-fg">{label}</span>
      </label>
      <p className="ml-6 mt-1 text-xs text-fg-muted">{hint}</p>
    </div>
  );
}

function NumberRow({
  id,
  label,
  value,
  min,
  max,
  onChange,
}: {
  id: string;
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="flex items-center justify-between py-3">
      <label htmlFor={id} className="text-sm text-fg-muted">
        {label}
      </label>
      <input
        id={id}
        type="number"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="input w-24"
        min={min}
        max={max}
      />
    </div>
  );
}

