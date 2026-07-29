// =============================================================================
// components/DiffTable.tsx — Display Reconciliation Results
// =============================================================================
// WHAT THIS COMPONENT DOES:
//   Shows the full comparison results in a rich, filterable table.
//   - Each company gets a row with expandable diffs
//   - Color coding: green = matches, red = differences, gray = unmatched
//   - Filters: show only diffs, search by name, filter by sector
//   - Stats cards at the top showing summary numbers
//
// REACT CONCEPTS USED:
//
// 1. CONDITIONAL RENDERING:
//    JSX supports showing different UI based on conditions:
//    {condition && <Element />}         → Show if true
//    {condition ? <A /> : <B />}        → Show A or B
//
// 2. LIST RENDERING:
//    {items.map((item, index) => <Element key={index} ... />)}
//    The 'key' prop helps React efficiently update only changed items.
//    ALWAYS provide a unique key when rendering lists!
//
// 3. MEMO (useMemo):
//    useMemo(() => expensiveComputation(), [deps])
//    Caches a computed value and only recomputes when deps change.
//    Used for filtering/sorting large datasets without re-computing on every render.
//
// 4. CALLBACK (useCallback):
//    Similar to useMemo but for functions.
//    Prevents functions from being recreated on every render.
// =============================================================================

import React, { useState, useMemo } from 'react';
import type { ReconciliationResponse, CompanyResult, FieldDiff, ResultFilters } from '../types';

interface DiffTableProps {
  data: ReconciliationResponse;
}

// =============================================================================
// STATS CARDS — Summary at the top
// =============================================================================
function StatsCards({ stats }: { stats: ReconciliationResponse['stats'] }) {
  const cards = [
    { label: 'Total Companies', value: stats.total, color: 'var(--color-primary)', icon: '🏢' },
    { label: 'Matched',         value: stats.matched, color: 'var(--color-success)', icon: '✅' },
    { label: 'Unmatched',       value: stats.unmatched, color: 'var(--color-warning)', icon: '⚠️' },
    { label: 'With Differences', value: stats.with_differences, color: 'var(--color-error)', icon: '🔴' },
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
      gap: 'var(--space-3)',
      marginBottom: 'var(--space-6)'
    }}>
      {cards.map(card => (
        <div key={card.label} className="card" style={{ padding: 'var(--space-4)', textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: '4px' }}>{card.icon}</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: card.color }}>
            {card.value}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {card.label}
          </div>
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// FIELD DIFF PILLS — Show each field comparison inline
// =============================================================================
function FieldDiffBadge({ diff }: { diff: FieldDiff }) {
  const isDiff = diff.is_different;

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '3px 8px',
      borderRadius: 'var(--radius-sm)',
      background: isDiff ? 'var(--color-diff-bg)' : 'var(--color-match-bg)',
      border: `1px solid ${isDiff ? 'var(--color-diff-border)' : 'var(--color-match-border)'}`,
      fontSize: '0.7rem',
      whiteSpace: 'nowrap',
    }}>
      <span style={{ color: 'var(--color-text-muted)' }}>{diff.label}:</span>
      {isDiff ? (
        <>
          {/* Show child value (strikethrough) → parent value */}
          <span style={{ color: 'var(--color-error)', textDecoration: 'line-through', fontFamily: 'var(--font-mono)' }}>
            {diff.child_value}
          </span>
          <span style={{ color: 'var(--color-text-muted)' }}>→</span>
          <span style={{ color: 'var(--color-success)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
            {diff.parent_value}
          </span>
          {diff.diff_amount !== null && (
            <span style={{ color: diff.diff_amount > 0 ? 'var(--color-success)' : 'var(--color-error)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem' }}>
              ({diff.diff_amount > 0 ? '+' : ''}{diff.diff_amount.toFixed(3)})
            </span>
          )}
        </>
      ) : (
        <span style={{ color: 'var(--color-success)', fontFamily: 'var(--font-mono)' }}>
          ✓ {diff.child_value}
        </span>
      )}
    </div>
  );
}

// =============================================================================
// COMPANY ROW — One row per company (expandable)
// =============================================================================
function CompanyRow({ company, index }: { company: CompanyResult; index: number }) {
  // Track if this row is expanded to show field details
  const [expanded, setExpanded] = useState(false);

  const hasAnyDiff = company.diffs.some(d => d.is_different);
  const diffCount = company.diffs.filter(d => d.is_different).length;

  // Status badge configuration
  const statusConfig = {
    matched_ok:        { label: 'OK',        color: 'badge-success' },
    matched_with_diff: { label: `${diffCount} DIFF${diffCount > 1 ? 'S' : ''}`, color: 'badge-error' },
    unmatched:         { label: 'UNMATCHED', color: 'badge-warning' },
  }[company.status];

  return (
    <>
      {/* Main row */}
      <tr
        className={hasAnyDiff ? 'row-diff' : ''}
        onClick={() => company.status !== 'unmatched' && setExpanded(!expanded)}
        style={{
          cursor: company.status !== 'unmatched' ? 'pointer' : 'default',
          transition: 'all 0.15s ease',
        }}
      >
        {/* Row number */}
        <td style={{ color: 'var(--color-text-muted)', width: '40px' }}>
          {index + 1}
        </td>

        {/* Company name */}
        <td>
          <div style={{ fontWeight: 500 }}>{company.company_name}</div>
          {company.matched_parent_name &&
           company.matched_parent_name !== company.company_name && (
            <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
              matched: {company.matched_parent_name}
            </div>
          )}
        </td>

        {/* Sector */}
        <td style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>
          {company.sector || '—'}
        </td>

        {/* Ticker */}
        <td>
          {company.exchange ? (
            <code style={{ fontSize: '0.75rem' }}>{company.exchange}</code>
          ) : '—'}
        </td>

        {/* Match score */}
        <td>
          {company.match_score !== null ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{
                width: `${company.match_score}%`,
                height: '4px',
                background: company.match_score >= 90
                  ? 'var(--color-success)'
                  : company.match_score >= 80
                  ? 'var(--color-warning)'
                  : 'var(--color-error)',
                borderRadius: '2px',
                maxWidth: '60px',
              }} />
              <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                {company.match_score.toFixed(0)}%
              </span>
            </div>
          ) : <span style={{ color: 'var(--color-text-muted)' }}>—</span>}
        </td>

        {/* Status badge */}
        <td>
          <span className={`badge ${statusConfig.color}`}>
            {statusConfig.label}
          </span>
        </td>

        {/* Expand indicator */}
        <td style={{ textAlign: 'right' }}>
          {company.status !== 'unmatched' && (
            <span style={{
              color: 'var(--color-text-muted)',
              transition: 'transform 0.2s',
              display: 'inline-block',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)'
            }}>▾</span>
          )}
        </td>
      </tr>

      {/* Expanded detail row — shows field-by-field comparison */}
      {expanded && company.status !== 'unmatched' && (
        <tr>
          <td colSpan={7} style={{ padding: '8px 16px 16px', background: 'rgba(0,0,0,0.2)' }}>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 'var(--space-2)',
              paddingTop: 'var(--space-2)',
            }}>
              {company.diffs.map(diff => (
                <FieldDiffBadge key={diff.field} diff={diff} />
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// =============================================================================
// MAIN DIFF TABLE COMPONENT
// =============================================================================
export function DiffTable({ data }: DiffTableProps) {
  // Filter state
  const [filters, setFilters] = useState<ResultFilters>({
    showOnlyDiffs: false,
    showUnmatched: true,
    sector: '',
    searchTerm: '',
  });

  // Get unique sectors for the filter dropdown
  // useMemo caches this — only recomputes when data changes
  const sectors = useMemo(() => {
    const sectorSet = new Set<string>();
    data.results.forEach(r => { if (r.sector) sectorSet.add(r.sector); });
    return Array.from(sectorSet).sort();
  }, [data]);

  // Apply all filters to results
  // This runs whenever results or filters change
  const filteredResults = useMemo(() => {
    return data.results.filter(company => {
      // Filter: only show companies with differences
      if (filters.showOnlyDiffs && !company.diffs.some(d => d.is_different)) {
        return false;
      }

      // Filter: hide unmatched companies
      if (!filters.showUnmatched && company.status === 'unmatched') {
        return false;
      }

      // Filter: by sector
      if (filters.sector && company.sector !== filters.sector) {
        return false;
      }

      // Filter: search by company name
      if (filters.searchTerm) {
        const term = filters.searchTerm.toLowerCase();
        if (!company.company_name.toLowerCase().includes(term)) {
          return false;
        }
      }

      return true;  // This company passes all filters
    });
  }, [data.results, filters]);

  return (
    <div className="animate-fade-in">
      {/* Stats Cards */}
      <StatsCards stats={data.stats} />

      {/* Metadata Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(59,130,246,0.1), rgba(16,185,129,0.05))',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-4)',
        marginBottom: 'var(--space-5)',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 'var(--space-4)',
      }}>
        <div>
          <p className="text-xs text-muted" style={{ marginBottom: '4px' }}>CHILD PORTFOLIO</p>
          <p style={{ fontWeight: 600 }}>
            {data.child_metadata?.portfolio_name || 'Portfolio'}
          </p>
          <p className="text-xs text-muted">{data.child_metadata?.date_range}</p>
        </div>
        <div>
          <p className="text-xs text-muted" style={{ marginBottom: '4px' }}>PARENT BENCHMARK</p>
          <p style={{ fontWeight: 600 }}>
            {data.parent_metadata?.benchmark_name || 'Benchmark'}
          </p>
          <p className="text-xs text-muted">{data.parent_metadata?.date_range}</p>
        </div>
      </div>

      {/* Filters Bar */}
      <div style={{
        display: 'flex',
        gap: 'var(--space-3)',
        marginBottom: 'var(--space-4)',
        flexWrap: 'wrap',
        alignItems: 'center',
      }}>
        {/* Search */}
        <input
          type="text"
          placeholder="🔍 Search company..."
          className="form-input"
          style={{ maxWidth: '220px', flex: 1 }}
          value={filters.searchTerm}
          onChange={e => setFilters(prev => ({ ...prev, searchTerm: e.target.value }))}
        />

        {/* Sector filter */}
        <select
          className="form-input"
          style={{ maxWidth: '200px' }}
          value={filters.sector}
          onChange={e => setFilters(prev => ({ ...prev, sector: e.target.value }))}
        >
          <option value="">All Sectors</option>
          {sectors.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        {/* Toggle: only show diffs */}
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.875rem' }}>
          <input
            type="checkbox"
            checked={filters.showOnlyDiffs}
            onChange={e => setFilters(prev => ({ ...prev, showOnlyDiffs: e.target.checked }))}
            style={{ accentColor: 'var(--color-primary)' }}
          />
          <span>Show only differences</span>
        </label>

        {/* Toggle: show unmatched */}
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.875rem' }}>
          <input
            type="checkbox"
            checked={filters.showUnmatched}
            onChange={e => setFilters(prev => ({ ...prev, showUnmatched: e.target.checked }))}
            style={{ accentColor: 'var(--color-warning)' }}
          />
          <span>Show unmatched</span>
        </label>

        <span style={{ marginLeft: 'auto', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
          Showing {filteredResults.length} of {data.results.length}
        </span>
      </div>

      {/* Results Table */}
      <div className="overflow-auto" style={{ borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Company Name</th>
              <th>Sector</th>
              <th>Ticker</th>
              <th>Match Score</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filteredResults.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-muted)' }}>
                  No results match your filters
                </td>
              </tr>
            ) : (
              filteredResults.map((company, index) => (
                // key prop: React uses this to efficiently update only changed rows
                <CompanyRow key={company.company_name} company={company} index={index} />
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div style={{
        display: 'flex',
        gap: 'var(--space-4)',
        marginTop: 'var(--space-3)',
        fontSize: '0.75rem',
        color: 'var(--color-text-muted)',
      }}>
        <span>💡 Click a row to see field-by-field differences</span>
        <span style={{ color: 'var(--color-error)' }}>■</span> Different values
        <span style={{ color: 'var(--color-success)' }}>■</span> Values match
      </div>
    </div>
  );
}
