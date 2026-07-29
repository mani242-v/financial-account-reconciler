// =============================================================================
// components/GeneratePanel.tsx — Trigger Word Generation & Download Files
// =============================================================================
import React, { useState } from 'react';
import type { Job } from '../types';
import { generateFiles, listGeneratedFiles, getFileDownloadUrl } from '../api/client';

interface GeneratePanelProps {
  job: Job;
  onTemplateUpdate?: (templateFilename: string) => void;
}

export function GeneratePanel({ job }: GeneratePanelProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedFiles, setGeneratedFiles] = useState<Array<{
    filename: string; account_name: string;
  }>>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleGenerate() {
    if (!job.template_filename) {
      setError('No template file attached to this job. Please upload a template first.');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setMessage(null);

    try {
      const result = await generateFiles(job.id);
      setGeneratedFiles(result.files);
      setMessage(result.message);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail || 'Generation failed');
    } finally {
      setIsGenerating(false);
    }
  }

  async function loadExistingFiles() {
    try {
      const result = await listGeneratedFiles(job.id);
      if (result.files.length > 0) {
        // Convert to the format we need
        setGeneratedFiles(result.files.map(f => ({
          filename: f.filename,
          account_name: f.account_name || '',
        })));
      }
    } catch {
      // Silently fail — no existing files is okay
    }
  }

  // Load existing files on mount
  React.useEffect(() => {
    loadExistingFiles();
  }, [job.id]);

  return (
    <div className="animate-fade-in">
      {/* Generate Button */}
      <div className="card" style={{ marginBottom: 'var(--space-5)' }}>
        <div className="card-header">
          <h3 className="card-title">📄 Generate Word Reports</h3>
        </div>

        <p className="text-sm" style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)' }}>
          Generate one Word document per sector, filled with the reconciled data from your template.
          Differences will be replaced with parent (benchmark) values.
        </p>

        {/* Template status */}
        <div style={{
          padding: 'var(--space-3)',
          background: job.template_filename
            ? 'rgba(16, 185, 129, 0.08)'
            : 'rgba(239, 68, 68, 0.08)',
          borderRadius: 'var(--radius-md)',
          marginBottom: 'var(--space-4)',
          fontSize: '0.875rem',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
        }}>
          {job.template_filename ? (
            <>
              <span>✅</span>
              <span>Template: <code>{job.template_filename}</code></span>
            </>
          ) : (
            <>
              <span>⚠️</span>
              <span style={{ color: 'var(--color-error)' }}>
                No template attached. Go back and upload a .docx template.
              </span>
            </>
          )}
        </div>

        <button
          className="btn btn-success btn-lg"
          onClick={handleGenerate}
          disabled={isGenerating || !job.template_filename}
        >
          {isGenerating ? (
            <>
              <span className="upload-spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
              Generating...
            </>
          ) : (
            '⚡ Generate Word Files'
          )}
        </button>

        {message && (
          <div style={{
            marginTop: 'var(--space-3)',
            padding: 'var(--space-3)',
            background: 'rgba(16, 185, 129, 0.1)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-success)',
            fontSize: '0.875rem',
          }}>
            ✅ {message}
          </div>
        )}

        {error && (
          <div style={{
            marginTop: 'var(--space-3)',
            padding: 'var(--space-3)',
            background: 'rgba(239, 68, 68, 0.1)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-error)',
            fontSize: '0.875rem',
          }}>
            ❌ {error}
          </div>
        )}
      </div>

      {/* Generated Files List */}
      {generatedFiles.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">⬇️ Download Generated Files</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {generatedFiles.map(file => (
              <div
                key={file.filename}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: 'var(--space-3)',
                  background: 'var(--color-bg-secondary)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  <span style={{ fontSize: '1.5rem' }}>📄</span>
                  <div>
                    <p style={{ fontWeight: 500, fontSize: '0.875rem' }}>{file.account_name}</p>
                    <p className="text-xs text-muted font-mono">{file.filename}</p>
                  </div>
                </div>
                <a
                  href={getFileDownloadUrl(file.filename)}
                  download={file.filename}
                  className="btn btn-primary btn-sm"
                >
                  ⬇️ Download
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
