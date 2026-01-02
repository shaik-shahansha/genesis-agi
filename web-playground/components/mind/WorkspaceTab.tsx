'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';

interface WorkspaceTabProps {
  mindId: string;
}

interface WorkspaceFile {
  file_id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  created_at: string;
  modified_at?: string;
  tags: string[];
  description: string;
  relevance_score?: number;
  match_reason?: string;
}

export default function WorkspaceTab({ mindId }: WorkspaceTabProps) {
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<WorkspaceFile[] | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<Record<string, boolean>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchFiles();
  }, [mindId]);

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const data = await api.getWorkspaceFiles(mindId);
      setFiles(data.files || []);
    } catch (error) {
      console.error('Error fetching files:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setUploading(true);
    const newProgress: Record<string, boolean> = {};

    try {
      for (const file of selectedFiles) {
        newProgress[file.name] = false;
        setUploadProgress({ ...newProgress });

        try {
          await api.uploadFile(mindId, file);
          newProgress[file.name] = true;
          setUploadProgress({ ...newProgress });
        } catch (error) {
          console.error(`Failed to upload ${file.name}:`, error);
          alert(`Failed to upload ${file.name}`);
        }
      }

      // Refresh file list
      await fetchFiles();
      setSelectedFiles([]);
      setUploadProgress({});
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (filename: string) => {
    if (!confirm(`Delete ${filename}?`)) return;

    try {
      await api.deleteWorkspaceFile(mindId, filename);
      await fetchFiles();
      if (searchResults) {
        setSearchResults(searchResults.filter(f => f.filename !== filename));
      }
    } catch (error) {
      console.error('Error deleting file:', error);
      alert('Failed to delete file');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }

    try {
      const data = await api.searchWorkspaceFiles(mindId, searchQuery);
      setSearchResults(data.files || []);
    } catch (error) {
      console.error('Error searching files:', error);
      alert('Search failed');
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults(null);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  const getFileIcon = (fileType: string): string => {
    const icons: Record<string, string> = {
      'text': '📄',
      'code': '💻',
      'data': '📊',
      'image': '🖼️',
      'document': '📑',
      'pdf': '📕',
      'xlsx': '📗',
      'csv': '📊',
    };
    return icons[fileType] || '📄';
  };

  const displayFiles = searchResults !== null ? searchResults : files;

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">📤 Upload Files</h3>
        
        <div className="space-y-4">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />
          
          <div className="flex gap-2">
            <label
              htmlFor="file-upload"
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 cursor-pointer transition"
            >
              Choose Files
            </label>
            
            {selectedFiles.length > 0 && (
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {uploading ? 'Uploading...' : `Upload ${selectedFiles.length} file(s)`}
              </button>
            )}
          </div>

          {/* Selected Files Preview */}
          {selectedFiles.length > 0 && (
            <div className="space-y-2">
              {selectedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                  <span className="text-sm text-gray-700">
                    {file.name} ({formatFileSize(file.size)})
                  </span>
                  {uploadProgress[file.name] !== undefined && (
                    <span className="text-sm">
                      {uploadProgress[file.name] ? '✅' : '⏳'}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          <p className="text-xs text-gray-500">
            💡 Files are automatically processed, embedded, and indexed for semantic search
          </p>
        </div>
      </div>

      {/* Search Section */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">🔍 Search Files</h3>
        
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search by content, description, or filename..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSearch}
            disabled={!searchQuery.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            Search
          </button>
          {searchResults !== null && (
            <button
              onClick={clearSearch}
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition"
            >
              Clear
            </button>
          )}
        </div>

        {searchResults !== null && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
            <p className="text-sm text-blue-900">
              Found {searchResults.length} file(s) matching "{searchQuery}"
            </p>
          </div>
        )}
      </div>

      {/* Files List */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          📁 {searchResults !== null ? 'Search Results' : 'All Files'} ({displayFiles.length})
        </h3>

        {loading ? (
          <div className="text-center py-8 text-gray-500">
            <div className="spinner mx-auto mb-2"></div>
            Loading files...
          </div>
        ) : displayFiles.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">📂</div>
            <p>{searchResults !== null ? 'No files found' : 'No files uploaded yet'}</p>
            <p className="text-sm mt-2">
              {searchResults !== null
                ? 'Try a different search query'
                : 'Upload files using the section above'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {displayFiles.map((file) => (
              <div
                key={file.file_id}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-2xl">{getFileIcon(file.file_type)}</span>
                    <span className="font-medium text-gray-900">{file.filename}</span>
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                      {file.file_type}
                    </span>
                  </div>
                  
                  <div className="text-sm text-gray-600 ml-8">
                    <p>{file.description}</p>
                    <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                      <span>Size: {formatFileSize(file.size_bytes)}</span>
                      <span>Created: {formatDate(file.created_at)}</span>
                      {file.tags && file.tags.length > 0 && (
                        <span>Tags: {file.tags.join(', ')}</span>
                      )}
                    </div>
                    
                    {file.relevance_score !== undefined && (
                      <div className="mt-2 p-2 bg-blue-50 rounded text-xs">
                        <span className="font-semibold">Relevance: {(file.relevance_score * 100).toFixed(0)}%</span>
                        {file.match_reason && (
                          <p className="mt-1 text-gray-600">{file.match_reason}</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(file.filename)}
                  className="ml-4 px-3 py-2 text-red-600 hover:bg-red-50 rounded transition"
                  title="Delete file"
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info Section */}
      <div className="bg-gradient-to-br from-green-50 to-blue-50 border border-green-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">✨ Smart Workspace Features</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>✅ <strong>Universal File Support:</strong> PDF, DOCX, XLSX, CSV, images, code files, and more</li>
          <li>✅ <strong>Automatic Processing:</strong> Files are intelligently parsed and analyzed</li>
          <li>✅ <strong>Vector Embeddings:</strong> Content is embedded using ChromaDB for semantic search</li>
          <li>✅ <strong>Memory Integration:</strong> Mind remembers all uploaded files</li>
          <li>✅ <strong>Semantic Search:</strong> Find files by meaning, not just filename</li>
          <li>✅ <strong>Chat Integration:</strong> Reference files in conversations</li>
        </ul>
      </div>
    </div>
  );
}
