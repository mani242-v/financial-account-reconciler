// =============================================================================
// types/index.ts — TypeScript Type Definitions
// =============================================================================
// WHAT IS TYPESCRIPT?
//   TypeScript is JavaScript with "types" added.
//   Types tell you WHAT kind of value a variable holds.
//
//   JavaScript: let name = "Alice";         // No type, could change to number
//   TypeScript: let name: string = "Alice"; // Locked to string type
//
// WHY USE TYPES?
//   1. Catch bugs BEFORE running: TypeScript warns if you pass a number
//      where a string is expected — in the editor, not at runtime!
//   2. Better autocomplete: your editor knows what properties exist
//   3. Self-documenting: types explain what data looks like
//
// KEY TYPE CONCEPTS:
//   interface  → Defines the shape of an object
//   type       → Alias for a type expression
//   optional?  → The property may or may not exist (? means optional)
//   string[]   → Array of strings
//   number | null → Either a number OR null (union type)
// =============================================================================

// =============================================================================
// API Response Types (must match the FastAPI Pydantic schemas!)
// =============================================================================

/** Represents a single reconciliation job stored in the database */
export interface Job {
  id: number;
  parent_filename: string | null;
  child_filename: string | null;
  template_filename: string | null;
  status: 'pending' | 'processing' | 'completed' | 'error';  // Union type!
  error_message: string | null;
  match_threshold: number;
  created_at: string;  // ISO date string from the API
  updated_at: string;
}

/** A single field comparison between child and parent values */
export interface FieldDiff {
  field: string;        // e.g., "avg_weight"
  label: string;        // e.g., "Average Weight"
  child_value: string;  // e.g., "0.0000"
  parent_value: string; // e.g., "1.2900"
  is_different: boolean;
  diff_amount: number | null;
}

/** All comparison results for one company */
export interface CompanyResult {
  company_name: string;
  matched_parent_name: string | null;
  sector: string | null;
  exchange: string | null;
  match_score: number | null;
  diffs: FieldDiff[];
  status: 'matched_ok' | 'matched_with_diff' | 'unmatched';
}

/** The full reconciliation response from GET /jobs/{id}/diff */
export interface ReconciliationResponse {
  job_id: number;
  parent_metadata: Record<string, string>;
  child_metadata: Record<string, string>;
  stats: {
    total: number;
    matched: number;
    unmatched: number;
    with_differences: number;
  };
  results: CompanyResult[];
}

/** Response from file upload endpoints */
export interface UploadResponse {
  message: string;
  filename: string;
  original_filename: string;
  file_path: string;
  size_bytes: number;
}

/** A generated Word file */
export interface GeneratedFile {
  id: number;
  job_id: number;
  filename: string;
  account_name: string | null;
  created_at: string;
}

/** Excel preview response */
export interface ExcelPreview {
  metadata: Record<string, string>;
  portfolio_name: string;
  benchmark_name: string;
  total_companies: number;
  companies_preview: Array<{
    company_name: string;
    sector: string | null;
    exchange: string | null;
    avg_weight: number | null;
    return_pct: number | null;
  }>;
  column_names: string[];
}

// =============================================================================
// UI State Types
// =============================================================================

/** Tracks which files have been uploaded in the current session */
export interface UploadedFiles {
  parent: UploadResponse | null;
  child: UploadResponse | null;
  template: UploadResponse | null;
}

/** Possible steps in the app workflow */
export type AppStep = 'upload' | 'configure' | 'results' | 'generate';

/** Filters for the results table */
export interface ResultFilters {
  showOnlyDiffs: boolean;
  showUnmatched: boolean;
  sector: string;
  searchTerm: string;
}
