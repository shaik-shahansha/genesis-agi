'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

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
    return (
      <div className="flex items-center justify-center py-12">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Autonomy Settings</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Initiative Level: {settings.autonomy_level}
            </label>
            <input
              type="range"
              min="0"
              max="10"
              value={settings.autonomy_level}
              onChange={(e) => setSettings({ ...settings, autonomy_level: parseInt(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Passive (0)</span>
              <span>Medium (5)</span>
              <span>Highly Proactive (10)</span>
            </div>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={settings.autonomous_actions_enabled}
                onChange={(e) => setSettings({ ...settings, autonomous_actions_enabled: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm text-gray-700">Enable autonomous actions</span>
            </label>
            <p className="text-xs text-gray-500 ml-6 mt-1">
              Allow the Mind to take actions proactively without prompting
            </p>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={settings.external_tools_allowed}
                onChange={(e) => setSettings({ ...settings, external_tools_allowed: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm text-gray-700">Allow external tool use</span>
            </label>
            <p className="text-xs text-gray-500 ml-6 mt-1">
              Permit the Mind to use plugins and external integrations
            </p>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={settings.require_approval}
                onChange={(e) => setSettings({ ...settings, require_approval: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm text-gray-700">Require approval for actions</span>
            </label>
            <p className="text-xs text-gray-500 ml-6 mt-1">
              Ask for permission before executing autonomous actions
            </p>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary w-full"
          >
            {saving ? 'Saving...' : '💾 Save Settings'}
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Actions</h2>
        <div className="space-y-3">
          {actions.length === 0 ? (
            <div className="text-gray-600 text-center py-8">
              No autonomous actions yet. Enable autonomy and give your Mind some time to act proactively.
            </div>
          ) : (
            actions.map((action) => (
              <div key={action.action_id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-medium text-gray-900">{action.action_type}</div>
                    <div className="text-sm text-gray-600">{action.description}</div>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs ${
                    action.status === 'completed' ? 'bg-green-100 text-green-700' :
                    action.status === 'failed' ? 'bg-red-100 text-red-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>
                    {action.status}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  {new Date(action.created_at).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Action Limits</h2>
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-700">Actions per hour</span>
            <input
              type="number"
              value={settings.max_actions_per_hour}
              onChange={(e) => setSettings({ ...settings, max_actions_per_hour: parseInt(e.target.value) })}
              className="input w-24"
              min="1"
              max="1000"
            />
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-700">Max concurrent actions</span>
            <input
              type="number"
              value={settings.max_concurrent_actions}
              onChange={(e) => setSettings({ ...settings, max_concurrent_actions: parseInt(e.target.value) })}
              className="input w-24"
              min="1"
              max="20"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
