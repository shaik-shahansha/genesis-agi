'use client';

interface AutonomyTabProps {
  mindId: string;
}

export default function AutonomyTab({ mindId }: AutonomyTabProps) {
  return (
    <div className="space-y-6">
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Autonomy Settings</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Initiative Level
            </label>
            <select className="input">
              <option>Low - Reactive only</option>
              <option>Medium - Balanced</option>
              <option>High - Proactive</option>
            </select>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm text-gray-700">Enable autonomous actions</span>
            </label>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm text-gray-700">Allow external tool use</span>
            </label>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm text-gray-700">Require approval for actions</span>
            </label>
          </div>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Actions</h2>
        <div className="space-y-3">
          <div className="text-gray-600 text-center py-8">
            No autonomous actions yet
          </div>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Action Limits</h2>
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-700">Actions per hour</span>
            <input type="number" className="input w-24" defaultValue="100" />
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-700">Max concurrent actions</span>
            <input type="number" className="input w-24" defaultValue="5" />
          </div>
        </div>
      </div>
    </div>
  );
}
