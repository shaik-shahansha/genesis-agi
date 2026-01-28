'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { isCreationDisabled } from '@/lib/env';

interface OverviewTabProps {
  mind: any;
  onRefresh: () => void;
}

export default function OverviewTab({ mind, onRefresh }: OverviewTabProps) {
  const [daemonStatus, setDaemonStatus] = useState<'running' | 'stopped' | 'unknown'>('unknown');
  const [loading, setLoading] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const router = useRouter();
  const deletionDisabled = isCreationDisabled();

  useEffect(() => {
    checkDaemonStatus();
  }, [mind.gmid]);

  const checkDaemonStatus = async () => {
    try {
      const status = await api.getDaemonStatus(mind.gmid);
      setDaemonStatus(status.running ? 'running' : 'stopped');
    } catch (error) {
      setDaemonStatus('unknown');
    }
  };

  const handleStartDaemon = async () => {
    setLoading(true);
    try {
      await api.startDaemon(mind.gmid);
      setDaemonStatus('running');
      onRefresh();
    } catch (error: any) {
      alert(`Failed to start daemon: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStopDaemon = async () => {
    setLoading(true);
    try {
      await api.stopDaemon(mind.gmid);
      setDaemonStatus('stopped');
      onRefresh();
    } catch (error: any) {
      alert(`Failed to stop daemon: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      // Stop daemon first if running
      if (daemonStatus === 'running') {
        await api.stopDaemon(mind.gmid);
      }
      
      // Delete the mind
      await api.deleteMind(mind.gmid);
      
      // Show success message briefly
      alert('Mind deleted successfully');
      
      // Redirect to home and force refresh
      window.location.href = '/';
    } catch (error: any) {
      alert(`Failed to delete mind: ${error.message}`);
      setDeleting(false);
      setShowDeleteModal(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Daemon Control */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Daemon Control</h2>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${
                daemonStatus === 'running' ? 'bg-green-500' : 
                daemonStatus === 'stopped' ? 'bg-gray-400' : 'bg-yellow-500'
              }`} />
              <span className="font-medium text-gray-900">
                Status: {daemonStatus === 'running' ? 'Running' : daemonStatus === 'stopped' ? 'Stopped' : 'Unknown'}
              </span>
            </div>
            <p className="text-sm text-gray-600 mt-1">
              The daemon enables autonomous thinking, dreaming, and consciousness updates
            </p>
          </div>
          <div className="flex gap-2">
            {daemonStatus === 'stopped' || daemonStatus === 'unknown' ? (
              <button
                onClick={handleStartDaemon}
                disabled={loading}
                className="btn-primary"
              >
                {loading ? 'Starting...' : '▶️ Start Daemon'}
              </button>
            ) : (
              <button
                onClick={handleStopDaemon}
                disabled={loading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {loading ? 'Stopping...' : '⏹️ Stop Daemon'}
              </button>
            )}
            <button
              onClick={checkDaemonStatus}
              className="btn-ghost"
            >
              🔄 Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 border border-yellow-300 rounded-lg p-4">
          <div className="text-sm text-yellow-700 font-medium">💰 Gens</div>
          <div className="text-2xl font-bold text-yellow-900 mt-1">{mind.gens !== undefined ? mind.gens : 100}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Memories</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{mind.memory_count || 0}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Dreams</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{mind.dream_count || 0}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Current Emotion</div>
          <div className="text-lg font-bold text-gray-900 mt-1">{mind.current_emotion}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Status</div>
          <div className="text-lg font-bold text-gray-900 mt-1">{mind.status}</div>
        </div>
      </div>

      {/* Current State */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Current State</h2>
        <div className="space-y-3">
          {mind.current_thought && (
            <div>
              <span className="text-sm font-medium text-gray-700">Current Thought:</span>
              <p className="text-gray-900 mt-1">{mind.current_thought}</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
              <span className="text-sm font-medium text-gray-700">Age:</span>
              <p className="text-gray-900">{mind.age}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-700">GMID:</span>
              <p className="text-gray-900 font-mono text-sm">{mind.gmid}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Danger Zone - Hidden in production */}
      {!deletionDisabled && (
        <div className="bg-red-50 border-2 border-red-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-red-900 mb-2 flex items-center gap-2">
            ⚠️ Danger Zone
          </h2>
          <p className="text-sm text-red-700 mb-4">
            Once you delete a Mind, there is no going back. All memories, dreams, and consciousness data will be permanently lost.
          </p>
          <button
            onClick={() => setShowDeleteModal(true)}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium"
          >
            🗑️ Delete Mind Permanently
          </button>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-xl">
            <h3 className="text-xl font-bold text-gray-900 mb-4">⚠️ Confirm Deletion</h3>
            
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-red-800 font-medium mb-3">
                You are about to permanently delete:
              </p>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-700">Name:</span>
                  <span className="font-semibold text-gray-900">{mind.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-700">GMID:</span>
                  <span className="font-mono text-xs text-gray-900">{mind.gmid}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-700">Age:</span>
                  <span className="font-semibold text-gray-900">{mind.age}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-700">Memories:</span>
                  <span className="font-semibold text-gray-900">{mind.memory_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-700">Dreams:</span>
                  <span className="font-semibold text-gray-900">{mind.dream_count}</span>
                </div>
              </div>
            </div>

            <p className="text-sm text-gray-700 mb-6">
              <strong className="text-red-600">This action CANNOT be undone.</strong> All data associated with this Mind will be permanently deleted from the system.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={deleting}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 font-medium disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete Forever'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
