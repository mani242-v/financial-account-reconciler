// =============================================================================
// api/client.ts — Typed API Client (Centralized HTTP Communication)
// =============================================================================
// WHAT THIS FILE DOES:
//   Provides a set of typed functions that call our FastAPI backend.
//   Instead of writing fetch() calls scattered all over the components,
//   we centralize all API calls here.
//
// WHY CENTRALIZE API CALLS?
//   1. Single place to change the API URL (e.g., when deploying to production)
//   2. TypeScript types ensure we handle responses correctly
//   3. Reusable across multiple components
//   4. Easy to add auth headers or error handling in one place
//
// WHAT IS axios?
//   axios is an HTTP client library (alternative to built-in fetch()).
//   Benefits over fetch:
//   - Automatic JSON parsing (fetch requires response.json())
//   - Better error handling (fetch doesn't throw on 4xx/5xx, axios does)
//   - Simpler request/response interceptors
//   - Better browser compatibility
//
// ASYNC/AWAIT REFRESHER:
//   JavaScript is single-threaded — it can't "pause" while waiting for data.
//   Instead, it uses "Promises" — a promise to deliver data later.
//   async/await is syntactic sugar over Promises that makes async code
//   look like synchronous code.
//
//   WITHOUT async/await (Promise chains):
//     api.uploadParent(file).then(data => { ... }).catch(err => { ... })
//
//   WITH async/await:
//     try {
//       const data = await api.uploadParent(file);  // wait here
//       // continue with data
//     } catch (err) { ... }
// =============================================================================

import axios from 'axios';
import type {
  Job,
  UploadResponse,
  ReconciliationResponse,
  GeneratedFile,
  ExcelPreview,
} from '../types';

// =============================================================================
// Create axios instance with base configuration
// =============================================================================
// By creating an "instance", we can set default config once:
// - baseURL: all requests will start with this (no need to repeat "http://localhost:8000")
// - timeout: abort request if it takes longer than 30 seconds
function getBaseUrl(): string {
  if (import.meta.env.VITE_API_BASE_URL) {
    const envUrl = import.meta.env.VITE_API_BASE_URL;
    return envUrl.startsWith('http://') || envUrl.startsWith('https://')
      ? envUrl
      : `https://${envUrl}`;
  }
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return window.location.origin;
  }
  return 'http://localhost:8000';
}

const API_BASE_URL = getBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// =============================================================================
// FILE UPLOAD FUNCTIONS
// =============================================================================

/**
 * Upload the parent (benchmark) Excel file.
 * Uses FormData (multipart/form-data) for file uploads.
 *
 * FORMDATA EXPLAINED:
 * Files can't be sent as plain JSON. Instead, they use "multipart/form-data"
 * which is the same format as HTML <input type="file"> submissions.
 * We create a FormData object, append the file to it, and send it.
 */
export async function uploadParentFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  // 'file' is the parameter name FastAPI expects (matching UploadFile = File(...))
  formData.append('file', file);

  const response = await api.post<UploadResponse>('/upload/parent', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',  // Override JSON default for file uploads
    },
  });
  return response.data;  // axios wraps response in {data, status, headers, ...}
}

export async function uploadChildFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<UploadResponse>('/upload/child', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function uploadTemplateFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<UploadResponse>('/upload/template', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

/** Download the sample Word template file */
export function getSampleTemplateUrl(): string {
  return `${api.defaults.baseURL}/upload/sample-template`;
}

/** Preview the contents of an uploaded Excel file */
export async function previewExcel(filename: string): Promise<ExcelPreview> {
  const response = await api.get<ExcelPreview>(`/upload/preview/${filename}`);
  return response.data;
}

// =============================================================================
// JOB FUNCTIONS
// =============================================================================

/**
 * Create a new reconciliation job.
 * Sends the filenames of previously uploaded files.
 */
export async function createJob(params: {
  parent_filename: string;
  child_filename: string;
  template_filename?: string;
  match_threshold?: number;
}): Promise<Job> {
  const response = await api.post<Job>('/jobs/', params);
  return response.data;
}

/** Fetch all jobs (with optional pagination) */
export async function listJobs(skip = 0, limit = 50): Promise<Job[]> {
  const response = await api.get<Job[]>('/jobs/', { params: { skip, limit } });
  return response.data;
}

/** Fetch one job's details */
export async function getJob(jobId: number): Promise<Job> {
  const response = await api.get<Job>(`/jobs/${jobId}`);
  return response.data;
}

/** Fetch the diff results for a completed job */
export async function getJobDiff(jobId: number): Promise<ReconciliationResponse> {
  const response = await api.get<ReconciliationResponse>(`/jobs/${jobId}/diff`);
  return response.data;
}

/** Delete a job */
export async function deleteJob(jobId: number): Promise<void> {
  await api.delete(`/jobs/${jobId}`);
}

// =============================================================================
// WORD GENERATION FUNCTIONS
// =============================================================================

/** Trigger Word file generation for a completed job */
export async function generateFiles(jobId: number): Promise<{
  message: string;
  files: Array<{ filename: string; account_name: string; path: string }>;
}> {
  const response = await api.post(`/generate/${jobId}`);
  return response.data;
}

/** List generated files for a job */
export async function listGeneratedFiles(jobId: number): Promise<{
  job_id: number;
  files: GeneratedFile[];
}> {
  const response = await api.get(`/generate/${jobId}/files`);
  return response.data;
}

/** Get the download URL for a generated file */
export function getFileDownloadUrl(filename: string): string {
  return `${api.defaults.baseURL}/generate/download/${filename}`;
}

/** Update the template for an existing job */
export async function updateJobTemplate(jobId: number, templateFilename: string): Promise<void> {
  await api.patch(`/generate/${jobId}/template`, null, {
    params: { template_filename: templateFilename },
  });
}

// Export the raw axios instance in case components need it
export default api;
