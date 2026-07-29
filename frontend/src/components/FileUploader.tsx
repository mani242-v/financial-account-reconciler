// =============================================================================
// components/FileUploader.tsx — Drag-and-Drop File Upload Component
// =============================================================================
// WHAT THIS COMPONENT DOES:
//   Renders three drop zones: Parent Excel, Child Excel, Word Template.
//   Each zone accepts drag-and-drop OR click-to-browse.
//   Shows upload progress, success state, and errors.
//   Calls the API to upload each file and returns the filenames.
//
// REACT CONCEPTS USED:
//
// 1. COMPONENTS:
//    A React component is a function that returns JSX (HTML-like syntax in JS).
//    It receives "props" (properties) from its parent.
//
// 2. STATE (useState):
//    State is data that can change and causes the UI to re-render.
//    const [value, setValue] = useState(initialValue);
//    value    = current state value
//    setValue = function to update it (triggers re-render)
//
// 3. EFFECTS (useEffect):
//    Side effects that run after renders (data fetching, subscriptions, etc.)
//    useEffect(() => { /* effect code */ }, [deps]);
//    The deps array controls WHEN the effect runs:
//    - []          → run once after mount
//    - [someVar]   → run when someVar changes
//    - no array    → run after every render
//
// 4. REACT-DROPZONE:
//    A library that handles the complex drag-and-drop file upload UI.
//    useDropzone() hook gives you:
//    - getRootProps() → spread onto your container div
//    - getInputProps() → spread onto a hidden <input> element
//    - isDragActive → boolean: is a file currently being dragged over?
//    - acceptedFiles → array of File objects the user dropped
//
// 5. ASYNC EVENT HANDLERS:
//    When a file is dropped, we call our API to upload it.
//    This is async, so we use async/await in the callback.
// =============================================================================

import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import type { UploadedFiles, UploadResponse } from '../types';
import { uploadParentFile, uploadChildFile, uploadTemplateFile, getSampleTemplateUrl } from '../api/client';
import './FileUploader.css';

// =============================================================================
// TYPES — Props this component accepts
// =============================================================================
interface FileUploaderProps {
  /**
   * Called when all three files have been uploaded.
   * The parent App component needs these filenames to create a job.
   */
  onFilesReady: (files: UploadedFiles) => void;
}

// =============================================================================
// SINGLE DROP ZONE COMPONENT
// =============================================================================
// We define this as an inner component because it's only used inside FileUploader.
// It handles one file upload at a time.

interface SingleDropZoneProps {
  label: string;           // e.g., "Parent Excel (Benchmark)"
  icon: string;            // emoji icon
  accept: Record<string, string[]>;  // File type filter for react-dropzone
  uploaded: UploadResponse | null;   // If set, file already uploaded
  onUpload: (file: File) => Promise<void>;  // What to do when file is dropped
  hint?: string;           // Hint text shown in the zone
}

function SingleDropZone({ label, icon, accept, uploaded, onUpload, hint }: SingleDropZoneProps) {
  // State for this specific zone
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // useDropzone sets up all the drag-and-drop logic
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    // accept defines which file types are allowed
    // e.g., { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] }
    accept,

    // Only allow one file at a time
    maxFiles: 1,

    // This runs when a file is dropped or selected
    // It receives an array of File objects
    onDrop: async (acceptedFiles) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];  // Take the first (and only) file
      setIsUploading(true);
      setError(null);

      try {
        await onUpload(file);  // Call the upload function (defined by parent)
      } catch (err: unknown) {
        // Type-safe error handling in TypeScript
        // We don't know if err is Error, string, or something else
        const message = err instanceof Error
          ? err.message
          : 'Upload failed. Please try again.';
        setError(message);
      } finally {
        // 'finally' runs whether upload succeeded or failed
        setIsUploading(false);
      }
    },
  });

  // Determine CSS classes based on state
  const zoneClasses = [
    'drop-zone',
    isDragActive ? 'drag-active' : '',
    uploaded ? 'uploaded' : '',
    isUploading ? 'uploading' : '',
  ].filter(Boolean).join(' ');

  return (
    <div>
      {/* getRootProps() adds onClick, onDragOver, onDrop etc. to this div */}
      <div {...getRootProps({ className: zoneClasses })}>
        {/* getInputProps() creates a hidden <input type="file"> */}
        <input {...getInputProps()} />

        {isUploading ? (
          // Show spinner while uploading
          <div className="upload-spinner" />
        ) : uploaded ? (
          // Show success state
          <div className="drop-zone-success">
            <span style={{ fontSize: '2rem' }}>✅</span>
            <span className="drop-zone-filename">{uploaded.original_filename}</span>
            <span className="drop-zone-filesize">
              {(uploaded.size_bytes / 1024).toFixed(1)} KB
            </span>
            <span className="text-xs text-muted">Click to replace</span>
          </div>
        ) : (
          // Show empty state
          <>
            <span className="drop-zone-icon">{icon}</span>
            <span className="drop-zone-label">{label}</span>
            <span className="drop-zone-hint">
              {isDragActive ? '📂 Drop here!' : (hint || 'Drag & drop or click to browse')}
            </span>
          </>
        )}
      </div>
      {error && <p className="upload-error">⚠️ {error}</p>}
    </div>
  );
}

// =============================================================================
// MAIN FILE UPLOADER COMPONENT
// =============================================================================
export function FileUploader({ onFilesReady }: FileUploaderProps) {
  // State: track which files have been uploaded
  // Each can be null (not uploaded) or an UploadResponse (uploaded)
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFiles>({
    parent: null,
    child: null,
    template: null,
  });

  // Helper: update one file in state and check if all three are done
  // This function uses the "functional update" form of setState:
  // prevState => newState
  // This ensures we always work with the LATEST state value
  const handleFileUploaded = (
    key: keyof UploadedFiles,
    response: UploadResponse
  ) => {
    setUploadedFiles(prev => {
      // Create a new object with the updated file
      // '...prev' is the spread operator — copies all properties of prev
      const updated = { ...prev, [key]: response };

      // Check if all three files are uploaded
      if (updated.parent && updated.child && updated.template) {
        // Tell the parent component we're ready!
        // We use setTimeout to let the state update render first
        setTimeout(() => onFilesReady(updated), 100);
      }

      return updated;
    });
  };

  // How many files are uploaded? For the progress display
  const uploadCount = Object.values(uploadedFiles).filter(Boolean).length;

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="upload-panel-header">
        <div className="step-indicator">1</div>
        <div>
          <h3 style={{ fontSize: '1.125rem', marginBottom: '2px' }}>Upload Files</h3>
          <p className="upload-panel-title">{uploadCount} of 3 files ready</p>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{
        height: '4px',
        background: 'var(--color-border)',
        borderRadius: '2px',
        marginBottom: 'var(--space-6)',
        overflow: 'hidden'
      }}>
        <div style={{
          height: '100%',
          width: `${(uploadCount / 3) * 100}%`,
          background: 'linear-gradient(90deg, var(--color-primary), var(--color-success))',
          borderRadius: '2px',
          transition: 'width 0.5s ease',
        }} />
      </div>

      {/* Three drop zones in a responsive grid */}
      <div className="uploader-grid">
        {/* DROP ZONE 1: Parent (Benchmark) Excel */}
        <SingleDropZone
          label="Parent / Benchmark Excel"
          icon="📊"
          accept={{
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
            'application/vnd.ms-excel': ['.xls'],
          }}
          uploaded={uploadedFiles.parent}
          hint=".xlsx benchmark data"
          onUpload={async (file) => {
            const response = await uploadParentFile(file);
            handleFileUploaded('parent', response);
          }}
        />

        {/* DROP ZONE 2: Child (Portfolio) Excel */}
        <SingleDropZone
          label="Child / Portfolio Excel"
          icon="📈"
          accept={{
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
            'application/vnd.ms-excel': ['.xls'],
          }}
          uploaded={uploadedFiles.child}
          hint=".xlsx portfolio data"
          onUpload={async (file) => {
            const response = await uploadChildFile(file);
            handleFileUploaded('child', response);
          }}
        />

        {/* DROP ZONE 3: Word Template */}
        <SingleDropZone
          label="Word Template (.docx)"
          icon="📝"
          accept={{
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
          }}
          uploaded={uploadedFiles.template}
          hint=".docx with {{PLACEHOLDERS}}"
          onUpload={async (file) => {
            const response = await uploadTemplateFile(file);
            handleFileUploaded('template', response);
          }}
        />
      </div>

      {/* Sample template download link */}
      <div style={{ marginTop: 'var(--space-5)', textAlign: 'center' }}>
        <a href={getSampleTemplateUrl()} target="_blank" rel="noreferrer"
           style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
          📥 Download sample Word template
        </a>
        <span style={{ color: 'var(--color-border)', margin: '0 8px' }}>|</span>
        <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
          Use <code>{'{{COMPANY_NAME}}'}</code>, <code>{'{{RETURN}}'}</code> etc. in your template
        </span>
      </div>
    </div>
  );
}
