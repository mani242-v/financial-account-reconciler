// =============================================================================
// components/JobHistory.tsx — List of Past Reconciliation Jobs
// =============================================================================
import React from 'react';
import type { Job } from '../types';

interface JobHistoryProps {
  jobs: Job[];
  activeJobId: number | null;
  onSelectJob: (job: Job) => void;
  onDeleteJob: (jobId: number) => void;
  isLoading: boolean;
}

function formatDate(isoStr: string): string {
  return new Date(isoStr).toLocaleString('en-US', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

function StatusDot({ status }: { status: Job['status'] }) {
  const config = {
    pending:    { color: 'var(--color-text-muted)', label: 'Pending' },
    processing: { color: 'var(--color-warning)',    label: 'Running...' },
    completed:  { color: 'var(--color-success)',    label: 'Done' },
    error:      { color: 'var(--color-error)',      label: 'Error' },
  }[status];

  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.75rem' }}>
      <span style={{
        width: '7px', height: '7px', borderRadius: '50%',
        background: config.color,
        boxShadow: status === 'processing' ? `0 0 6px ${config.color}` : 'none',
        animation: status === 'processing' ? 'pulse 1.5s infinite' : 'none',
      }} />
      <span style={{ color: config.color }}>{config.label}</span>
    </span>
  );
}

export function JobHistory({ jobs, activeJobId, onSelectJob, onDeleteJob, isLoading }: JobHistoryProps) {
  if (isLoading) {
    return (
      <div style={{ padding: 'var(--space-4)', textAlign: 'center' }}>
        <div className="upload-spinner" style={{ margin: '0 auto' }} />
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)' }}>
        <div style={{ fontSize: '2rem', marginBottom: 'var(--space-2)' }}>📭</div>
        <p style={{ fontSize: '0.875rem' }}>No jobs yet. Upload files to start.</p>
      </div>
    );
  }

  return (
    <div>
      {jobs.map(job => {
        const isActive = job.id === activeJobId;
        return (
          <div
            key={job.id}
            onClick={() => job.status === 'completed' && onSelectJob(job)}
            style={{
              padding: 'var(--space-3) var(--space-4)',
              borderBottom: '1px solid var(--color-border)',
              cursor: job.status === 'completed' ? 'pointer' : 'default',
              background: isActive ? 'rgba(59, 130, 246, 0.08)' : 'transparent',
              borderLeft: isActive ? '3px solid var(--color-primary)' : '3px solid transparent',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={e => {
              if (!isActive && job.status === 'completed')
                (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.03)';
            }}
            onMouseLeave={e => {
              if (!isActive)
                (e.currentTarget as HTMLDivElement).style.background = 'transparent';
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Job #{job.id}</span>
                  <StatusDot status={job.status} />
                </div>
                <div className="text-xs text-muted truncate">
                  📊 {job.parent_filename?.split('_').slice(1).join('_') || 'parent'}
                </div>
                <div className="text-xs text-muted truncate">
                  📈 {job.child_filename?.split('_').slice(1).join('_') || 'child'}
                </div>
                <div className="text-xs" style={{ color: 'var(--color-text-muted)', marginTop: '4px' }}>
                  {formatDate(job.created_at)}
                </div>
                {job.error_message && (
                  <div className="text-xs" style={{ color: 'var(--color-error)', marginTop: '4px' }}>
                    ⚠️ {job.error_message.slice(0, 60)}...
                  </div>
                )}
              </div>
              <button
                className="btn btn-danger btn-sm"
                onClick={e => { e.stopPropagation(); onDeleteJob(job.id); }}
                title="Delete job"
                style={{ marginLeft: 'var(--space-2)', flexShrink: 0 }}
              >
                ✕
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
