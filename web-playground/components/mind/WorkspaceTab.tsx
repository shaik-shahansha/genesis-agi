'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';
import {
  EmptyState,
  LoadingRows,
  Section,
  StatusBadge,
} from '@/components/governance/primitives';
import { TrashIcon } from '@/components/shell/icons';

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

  const displayFiles = searchResults !== null ? searchResults : files;

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <Section
        title="Upload"
        description="Files are parsed, embedded and indexed, so the Mind can retrieve them by meaning later."
      >
        <div className="card space-y-4">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />

          <div className="flex flex-wrap gap-2">
            <label htmlFor="file-upload" className="btn-secondary cursor-pointer">
              Choose files
            </label>

            {selectedFiles.length > 0 && (
              <button
                type="button"
                onClick={handleUpload}
                disabled={uploading}
                className="btn-primary"
              >
                {uploading
                  ? 'Uploading…'
                  : `Upload ${selectedFiles.length} file${selectedFiles.length === 1 ? '' : 's'}`}
              </button>
            )}
          </div>

          {selectedFiles.length > 0 && (
            <ul className="space-y-2">
              {selectedFiles.map((file, index) => (
                <li
                  key={`${file.name}-${index}`}
                  className="flex items-center justify-between gap-3 rounded-lg border border-line bg-surface-2 p-2"
                >
                  <span className="min-w-0 truncate text-sm text-fg">
                    {file.name}{' '}
                    <span className="text-fg-subtle">({formatFileSize(file.size)})</span>
                  </span>
                  {uploadProgress[file.name] !== undefined && (
                    <StatusBadge tone={uploadProgress[file.name] ? 'success' : 'warning'}>
                      {uploadProgress[file.name] ? 'Uploaded' : 'Pending'}
                    </StatusBadge>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </Section>

      {/* Search Section */}
      <Section
        title="Search"
        description="Search by meaning, not just by filename — matches come from the embedded content."
      >
        <div className="card">
          <div className="flex flex-wrap gap-2">
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search by content, description or filename…"
              className="input min-w-0 flex-1"
              aria-label="Search workspace files"
            />
            <button
              type="button"
              onClick={handleSearch}
              disabled={!searchQuery.trim()}
              className="btn-primary"
            >
              Search
            </button>
            {searchResults !== null && (
              <button type="button" onClick={clearSearch} className="btn-secondary">
                Clear
              </button>
            )}
          </div>

          {searchResults !== null && (
            <p className="mt-3 rounded-lg border border-info/40 bg-info/5 px-3 py-2 text-sm text-fg-muted">
              {searchResults.length} {searchResults.length === 1 ? 'file' : 'files'} matched{' '}
              <span className="font-medium text-fg">“{searchQuery}”</span>
            </p>
          )}
        </div>
      </Section>

      {/* Files List */}
      <Section title={`${searchResults !== null ? 'Search results' : 'Files'} (${displayFiles.length})`}>
        {loading ? (
          <LoadingRows rows={2} label="Loading workspace files" />
        ) : displayFiles.length === 0 ? (
          <EmptyState
            title={searchResults !== null ? 'No matches' : 'No files yet'}
            description={
              searchResults !== null
                ? 'Try different words, or clear the search to see everything.'
                : 'Upload a file above and the Mind will be able to retrieve it by meaning.'
            }
          />
        ) : (
          <div className="space-y-3">
            {displayFiles.map((file) => (
              <div key={file.file_id} className="card-flat">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <FileGlyph kind={file.file_type} />
                      <span className="min-w-0 truncate font-medium text-fg">{file.filename}</span>
                      <StatusBadge tone="neutral">{file.file_type}</StatusBadge>
                    </div>

                    <div className="mt-2 pl-9">
                      {file.description && (
                        <p className="text-sm text-fg-muted">{file.description}</p>
                      )}
                      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-fg-subtle">
                        <span>{formatFileSize(file.size_bytes)}</span>
                        <span>{formatDate(file.created_at)}</span>
                        {file.tags && file.tags.length > 0 && (
                          <span>Tags: {file.tags.join(', ')}</span>
                        )}
                      </div>

                      {file.relevance_score !== undefined && (
                        <div className="mt-2 rounded-lg border border-info/40 bg-info/5 p-2 text-xs">
                          <span className="font-medium text-fg">
                            Relevance {(file.relevance_score * 100).toFixed(0)}%
                          </span>
                          {file.match_reason && (
                            <p className="mt-0.5 text-fg-muted">{file.match_reason}</p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleDelete(file.filename)}
                    className="btn-ghost btn-sm text-danger"
                    title={`Delete ${file.filename}`}
                    aria-label={`Delete ${file.filename}`}
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Info Section */}
      <Section title="What the workspace does">
        <div className="card">
          <dl className="grid gap-3 sm:grid-cols-2">
            {[
              ['Parses', 'PDF, DOCX, XLSX, CSV, images and source files are read into text.'],
              ['Embeds', 'Content is vectorised so retrieval works on meaning, not keywords.'],
              ['Tags', 'Uploader and type are attached, and each upload is journalled.'],
              ['Recalls', 'Files become retrievable context in later conversations.'],
            ].map(([term, meaning]) => (
              <div key={term}>
                <dt className="text-sm font-medium text-fg">{term}</dt>
                <dd className="mt-0.5 text-sm text-fg-muted">{meaning}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Section>
    </div>
  );
}

/**
 * File-type glyph.
 *
 * `formatFileType` used to return emoji per type from a small map. It rendered
 * fine, but the two placeholder strings in this file — the feature list's
 * `[Done]` prefixes — showed what happens when a glyph is treated as data: it
 * leaks. This keeps the mapping in code and falls back deliberately.
 */
function FileGlyph({ kind }: { kind: string }) {
  const icons: Record<string, string> = {
    text: '📄',
    code: '💻',
    data: '📊',
    image: '🖼',
    document: '📑',
    pdf: '📕',
    xlsx: '📗',
    csv: '📊',
  };
  return (
    <span className="grid h-7 w-7 flex-shrink-0 place-items-center rounded bg-surface-3 text-sm">
      {icons[kind] || '📄'}
    </span>
  );
}

