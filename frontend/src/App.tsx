// =============================================================================
// App.tsx — Main Application Component
// =============================================================================
// This is the ROOT component — the top of the React component tree.
// Every other component is rendered inside this one.
//
// APP ARCHITECTURE:
//   App
//   ├── Header (always visible)
//   ├── Sidebar (JobHistory — always visible on left)
//   └── Main Content Area (changes based on current step)
//       ├── Step 1: FileUploader (upload files)
//       ├── Step 2: Configure (set threshold, review files)
//       ├── Step 3: DiffTable (view results)
//       └── Step 4: GeneratePanel (generate and download Word files)
//
// STATE MANAGEMENT:
//   All shared state lives here (in the App component).
//   It's passed DOWN to child components via props.
//   Children communicate UP by calling callback functions (also via props).
//   This "unidirectional data flow" is a core React pattern.
//
//   State defined here:
//   - currentJob: the currently selected/active reconciliation job
//   - jobs: list of all past jobs (from database)
//   - diffData: the comparison results for the current job
//   - step: which panel to show
//   - uploadedFiles: files uploaded in the current session
// =============================================================================

import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

import type { Job, UploadedFiles, ReconciliationResponse } from './types';
import {
  listJobs,
  createJob,
  getJobDiff,
  deleteJob,
} from './api/client';

import { FileUploader } from './components/FileUploader';
import { DiffTable } from './components/DiffTable';
import { JobHistory } from './components/JobHistory';
import { GeneratePanel } from './components/GeneratePanel';

// =============================================================================
// Type for the active panel/step
// =============================================================================
type Panel = 'upload' | 'results' | 'generate';

// =============================================================================
// APP COMPONENT
// =============================================================================
function App() {
  // ------------------------------------------------------------------
  // STATE DECLARATIONS
  // useState<Type>(initialValue) → [value, setter]
  // ------------------------------------------------------------------

  // List of all jobs from the database
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);

  // The currently active job (clicked in sidebar or just created)
  const [currentJob, setCurrentJob] = useState<Job | null>(null);

  // The diff results for the current job
  const [diffData, setDiffData] = useState<ReconciliationResponse | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);

  // Which panel is showing
  const [panel, setPanel] = useState<Panel>('upload');

  // Files uploaded in this session (before job is created)
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFiles | null>(null);

  // Match threshold setting
  const [threshold, setThreshold] = useState(85);

  // Job creation state
  const [isCreatingJob, setIsCreatingJob] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);

  // ------------------------------------------------------------------
  // LOAD JOBS ON MOUNT
  // useEffect with [] deps = runs once when the component first renders
  // ------------------------------------------------------------------
  useEffect(() => {
    loadJobs();
  }, []);

  // ------------------------------------------------------------------
  // FUNCTIONS
  // useCallback memoizes functions — prevents unnecessary re-renders
  // in child components that receive these as props
  // ------------------------------------------------------------------
  const loadJobs = useCallback(async () => {
    setJobsLoading(true);
    try {
      const fetchedJobs = await listJobs();
      setJobs(fetchedJobs);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    } finally {
      setJobsLoading(false);
    }
  }, []);

  // Called when FileUploader has all 3 files ready
  const handleFilesReady = useCallback((files: UploadedFiles) => {
    setUploadedFiles(files);
    // Don't automatically create the job — let user review threshold first
  }, []);

  // Called when user clicks "Run Reconciliation"
  const handleCreateJob = async () => {
    if (!uploadedFiles?.parent || !uploadedFiles?.child) return;

    setIsCreatingJob(true);
    setJobError(null);

    try {
      const newJob = await createJob({
        parent_filename: uploadedFiles.parent.filename,
        child_filename: uploadedFiles.child.filename,
        template_filename: uploadedFiles.template?.filename,
        match_threshold: threshold,
      });

      // Add to jobs list at the top
      setJobs(prev => [newJob, ...prev]);
      setCurrentJob(newJob);

      // Load the diff results
      await loadDiffForJob(newJob);

    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setJobError(axiosErr.response?.data?.detail || 'Failed to create job');
    } finally {
      setIsCreatingJob(false);
    }
  };

  // Load diff results for a job and navigate to results panel
  const loadDiffForJob = async (job: Job) => {
    setDiffLoading(true);
    setDiffData(null);
    setPanel('results');
    setCurrentJob(job);

    try {
      const diff = await getJobDiff(job.id);
      setDiffData(diff);
    } catch (err) {
      console.error('Failed to load diff:', err);
    } finally {
      setDiffLoading(false);
    }
  };

  // Called when user clicks a job in the sidebar
  const handleSelectJob = (job: Job) => {
    loadDiffForJob(job);
  };

  // Delete a job
  const handleDeleteJob = async (jobId: number) => {
    if (!confirm(`Delete Job #${jobId}? This cannot be undone.`)) return;
    try {
      await deleteJob(jobId);
      setJobs(prev => prev.filter(j => j.id !== jobId));
      if (currentJob?.id === jobId) {
        setCurrentJob(null);
        setDiffData(null);
        setPanel('upload');
      }
    } catch (err) {
      console.error('Failed to delete job:', err);
    }
  };

  // =============================================================================
  // RENDER — What the user sees
  // JSX is JavaScript XML — it looks like HTML but is compiled to React.createElement()
  // =============================================================================
  return (
    <div className="app-layout">

      {/* =========================================================
          HEADER
          ========================================================= */}
      <header className="app-header">
        <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <span style={{ fontSize: '1.75rem' }}>⚖️</span>
            <div>
              <h1 style={{ fontSize: '1.1rem', fontWeight: 800, letterSpacing: '-0.03em' }}>
                Financial Reconciler
              </h1>
              <p style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: '1px' }}>
                Excel → Compare → Word Reports
              </p>
            </div>
          </div>

          {/* Navigation tabs */}
          <nav style={{ display: 'flex', gap: 'var(--space-1)' }}>
            {(['upload', 'results', 'generate'] as Panel[]).map((p, i) => {
              const labels = ['📁 Upload', '📊 Results', '📄 Generate'];
              const isActive = panel === p;
              const isDisabled = (p === 'results' && !diffData) || (p === 'generate' && !currentJob);

              return (
                <button
                  key={p}
                  className={`btn ${isActive ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                  onClick={() => !isDisabled && setPanel(p)}
                  disabled={isDisabled}
                  style={{ opacity: isDisabled ? 0.4 : 1 }}
                >
                  {labels[i]}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* =========================================================
          BODY — Sidebar + Main Content
          ========================================================= */}
      <div className="app-body">

        {/* ---- SIDEBAR: Job History ---- */}
        <aside className="app-sidebar">
          <div style={{
            padding: 'var(--space-4)',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <h2 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--color-text-secondary)' }}>
              🕒 JOB HISTORY
            </h2>
            <button className="btn btn-secondary btn-sm" onClick={loadJobs}>
              ↻
            </button>
          </div>

          <JobHistory
            jobs={jobs}
            activeJobId={currentJob?.id ?? null}
            onSelectJob={handleSelectJob}
            onDeleteJob={handleDeleteJob}
            isLoading={jobsLoading}
          />
        </aside>

        {/* ---- MAIN CONTENT ---- */}
        <main className="app-main">
          <div className="app-container" style={{ paddingTop: 'var(--space-6)', paddingBottom: 'var(--space-8)' }}>

            {/* ===================================================
                PANEL 1: UPLOAD
                =================================================== */}
            {panel === 'upload' && (
              <div className="card" style={{ marginBottom: 'var(--space-5)' }}>
                <FileUploader onFilesReady={handleFilesReady} />

                {/* Configure & Run — shows after files are uploaded */}
                {uploadedFiles?.parent && uploadedFiles?.child && (
                  <div className="animate-fade-in" style={{
                    marginTop: 'var(--space-6)',
                    padding: 'var(--space-5)',
                    background: 'var(--color-bg-secondary)',
                    borderRadius: 'var(--radius-lg)',
                    border: '1px solid var(--color-border)',
                  }}>
                    <h3 style={{ marginBottom: 'var(--space-4)' }}>⚙️ Configure Reconciliation</h3>

                    <div className="form-group" style={{ maxWidth: '400px', marginBottom: 'var(--space-5)' }}>
                      <label className="form-label">
                        Fuzzy Match Threshold: <strong style={{ color: 'var(--color-primary)' }}>{threshold}%</strong>
                      </label>
                      <input
                        type="range"
                        min={50}
                        max={100}
                        value={threshold}
                        onChange={e => setThreshold(Number(e.target.value))}
                        style={{ width: '100%', accentColor: 'var(--color-primary)' }}
                      />
                      <p className="text-xs text-muted">
                        Higher = stricter matching. 85% recommended.
                        <br />
                        At {threshold}%: "Natera Inc" {threshold >= 85 ? '✅ matches' : '❌ misses'} "Natera, Inc."
                      </p>
                    </div>

                    {/* Files summary */}
                    <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)' }}>
                      <p>📊 Parent: <code>{uploadedFiles.parent.original_filename}</code></p>
                      <p>📈 Child: <code>{uploadedFiles.child.original_filename}</code></p>
                      {uploadedFiles.template && (
                        <p>📝 Template: <code>{uploadedFiles.template.original_filename}</code></p>
                      )}
                    </div>

                    {jobError && (
                      <div style={{
                        padding: 'var(--space-3)', background: 'rgba(239,68,68,0.1)',
                        borderRadius: 'var(--radius-md)', color: 'var(--color-error)',
                        fontSize: '0.875rem', marginBottom: 'var(--space-4)'
                      }}>
                        ❌ {jobError}
                      </div>
                    )}

                    <button
                      className="btn btn-primary btn-lg"
                      onClick={handleCreateJob}
                      disabled={isCreatingJob}
                    >
                      {isCreatingJob ? (
                        <>
                          <span className="upload-spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                          Running Reconciliation...
                        </>
                      ) : (
                        '🔍 Run Reconciliation'
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* ===================================================
                PANEL 2: RESULTS
                =================================================== */}
            {panel === 'results' && (
              <div>
                {diffLoading ? (
                  <div style={{ textAlign: 'center', padding: '80px 20px' }}>
                    <div className="upload-spinner" style={{ margin: '0 auto 16px', width: '40px', height: '40px', borderWidth: '3px' }} />
                    <p style={{ color: 'var(--color-text-muted)' }}>Running reconciliation...</p>
                  </div>
                ) : diffData ? (
                  <div className="card">
                    <div className="card-header">
                      <h2 className="card-title">
                        📊 Reconciliation Results — Job #{currentJob?.id}
                      </h2>
                      {currentJob && (
                        <button
                          className="btn btn-success btn-sm"
                          onClick={() => setPanel('generate')}
                        >
                          📄 Generate Reports →
                        </button>
                      )}
                    </div>
                    <DiffTable data={diffData} />
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--color-text-muted)' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📊</div>
                    <p>Select a completed job from the sidebar, or run a new reconciliation.</p>
                  </div>
                )}
              </div>
            )}

            {/* ===================================================
                PANEL 3: GENERATE
                =================================================== */}
            {panel === 'generate' && (
              <div>
                {currentJob ? (
                  <GeneratePanel job={currentJob} />
                ) : (
                  <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--color-text-muted)' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📄</div>
                    <p>Complete a reconciliation job first, then generate Word reports.</p>
                  </div>
                )}
              </div>
            )}

          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
