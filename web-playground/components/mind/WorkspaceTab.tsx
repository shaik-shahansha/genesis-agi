'use client';

import { useState } from 'react';

interface WorkspaceTabProps {
  mindId: string;
}

export default function WorkspaceTab({ mindId }: WorkspaceTabProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  // Note: Workspace file management endpoints are not yet implemented in the backend
  // This is a placeholder UI for future functionality

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Coming Soon Notice */}
      <div className="bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-200 rounded-lg p-8 text-center">
        <div className="text-6xl mb-4">🚧</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Workspace Coming Soon</h2>
        <p className="text-gray-700 mb-4">
          File management and workspace features are currently under development.
        </p>
        <p className="text-sm text-gray-600">
          This will include:
        </p>
        <ul className="text-sm text-gray-600 mt-2 space-y-1">
          <li>📁 File uploads and management</li>
          <li>💾 Document storage</li>
          <li>🔍 File search and organization</li>
          <li>🤖 AI-powered file analysis</li>
          <li>🔗 File sharing and collaboration</li>
        </ul>
      </div>

      {/* Temporary Workaround */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Current Alternatives</h3>
        <div className="space-y-3 text-sm text-gray-700">
          <div>
            <p className="font-medium">📝 Use the CLI:</p>
            <code className="block mt-1 bg-gray-100 p-2 rounded text-xs font-mono">
              genesis workspace add {mindId} &lt;file-path&gt;
            </code>
          </div>
          <div>
            <p className="font-medium">💬 Share via Chat:</p>
            <p className="text-gray-600">You can discuss files and content directly in the Chat tab</p>
          </div>
        </div>
      </div>
    </div>
  );
}
