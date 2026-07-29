# =============================================================================
# services/excel_parser.py — Read & Parse the Financial Excel Files
# =============================================================================
# WHAT THIS FILE DOES:
#   Takes the complex Excel file (like the one in the screenshot) and converts
#   it into clean Python data structures (lists of dicts) that the rest of
#   the app can work with.
#
# THE CHALLENGE:
#   The Excel file has:
#   - Rows 1-9: Metadata (title, company name, date range, currency, etc.)
#   - Row 10-11: Column headers (split across two rows!)
#   - Row 14+: Actual data (mixed with sector headers like "Health care")
#
#   pandas handles this with the 'skiprows' and 'header' parameters.
#
# WHAT IS PANDAS?
#   pandas is the most popular Python library for working with tabular data.
#   It reads Excel, CSV, JSON, and converts them into a "DataFrame" —
#   think of a DataFrame as a spreadsheet in Python memory.
#
# KEY CONCEPTS USED:
#   - pd.read_excel() : Read an Excel file into a DataFrame
#   - df.dropna()     : Remove rows where all values are missing
#   - df.fillna()     : Replace NaN (empty cells) with a default value
#   - df.iterrows()   : Loop through each row of a DataFrame
#   - df.columns      : The column header names
# =============================================================================

import re
from pathlib import Path
from typing import Optional
import pandas as pd


# =============================================================================
# CONSTANTS — Column Names We Expect to Find
# =============================================================================
# These are the "canonical" (official) names we'll use internally.
# The actual Excel might have "Avg W" or "Average Weight" — we'll map both.

PORTFOLIO_COLUMNS = {
    "company_name":  ["Company Name", "company name", "Name", "Stock"],
    "exchange":      ["Exchange", "Ticker", "Symbol"],
    "price":         ["Price", "Price 12/31", "Price 12/3"],
    "avg_weight":    ["Average W", "Avg W", "Average Weight", "Avg Weight"],
    "ending_weight": ["Ending W", "Ending Weight", "End W"],
    "return_pct":    ["Return (%)", "Return%", "Return (%)"],
    "contrib":       ["Contrib", "Contribution"],
}


# =============================================================================
# HELPER FUNCTION: Find the actual column name in the DataFrame
# =============================================================================
def find_column(df_columns: list, candidates: list) -> Optional[str]:
    """
    Searches the DataFrame's column list for any of the candidate names.
    
    Why do we need this?
    Excel files from different sources may use different names for the same thing.
    E.g., "Average Weight", "Avg Weight", "Avg W" all mean the same thing.
    
    Args:
        df_columns: The actual column names in the DataFrame (e.g., ['Company Name', 'Exchange', ...])
        candidates: List of possible names to look for (e.g., ['Avg W', 'Average Weight'])
    
    Returns:
        The first matching column name, or None if not found.
    
    Example:
        df_columns = ['Company Name', 'Exchange', 'Avg W', 'Return (%)']
        candidates = ['Average Weight', 'Avg W', 'Avg Weight']
        → Returns 'Avg W'  (because that's what actually exists)
    """
    # Convert everything to lowercase for case-insensitive matching
    lower_cols = {col.lower().strip(): col for col in df_columns}
    
    for candidate in candidates:
        if candidate.lower().strip() in lower_cols:
            return lower_cols[candidate.lower().strip()]
    
    return None  # Not found


# =============================================================================
# MAIN FUNCTION: Parse a Parent or Child Excel File
# =============================================================================
def parse_excel(file_path: str) -> dict:
    """
    Reads a financial Excel file and extracts:
    1. Metadata (report title, portfolio name, date range, etc.)
    2. A list of company records with their financial data
    3. Sector groupings
    
    Args:
        file_path: Full path to the .xlsx file
    
    Returns:
        A dictionary with:
        {
            "metadata": {...},         # Report info from header rows
            "portfolio_name": "...",   # e.g., "Harris Corporation - Large-cap Growth"
            "benchmark_name": "...",   # e.g., "Russell 1000 Growth Index"
            "companies": [            # List of company records
                {
                    "company_name": "Abbvie Inc.",
                    "sector": "Health care",
                    "exchange": "ABBV",
                    "avg_weight": 0.0,
                    "ending_weight": 0.0,
                    "return_pct": 0.0,
                    "contrib": 0.0,
                    ...
                },
                ...
            ]
        }
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    
    # ------------------------------------------------------------------
    # STEP 1: Read the raw file to extract metadata from header rows
    # ------------------------------------------------------------------
    # header=None means "don't treat any row as column headers yet"
    # We read all rows as raw data first, so we can look at rows 1-10
    raw_df = pd.read_excel(file_path, header=None, nrows=15)
    
    metadata = _extract_metadata(raw_df)
    
    # ------------------------------------------------------------------
    # STEP 2: Read the file again, this time treating row 10 as header
    # ------------------------------------------------------------------
    # skiprows=10 means "skip the first 10 rows" (the metadata rows)
    # After skipping, pandas treats the NEXT row as column names
    #
    # The actual header row number may vary — we try to detect it
    header_row = _find_header_row(raw_df)
    
    # Read with detected header row
    # dtype=str keeps all values as strings initially (prevents number formatting issues)
    df = pd.read_excel(file_path, skiprows=header_row, dtype=str)
    
    # ------------------------------------------------------------------
    # STEP 3: Clean up the DataFrame
    # ------------------------------------------------------------------
    # Strip whitespace from column names (Excel often has trailing spaces)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Drop completely empty rows (where EVERY cell is NaN or empty)
    df = df.dropna(how='all')
    
    # Replace 'nan' strings (from dtype=str conversion) with empty string
    df = df.replace({'nan': '', 'NaN': '', 'None': ''})
    
    # ------------------------------------------------------------------
    # STEP 4: Extract company records row by row
    # ------------------------------------------------------------------
    companies = _extract_companies(df)
    
    return {
        "metadata": metadata,
        "portfolio_name": metadata.get("portfolio_name", "Unknown Portfolio"),
        "benchmark_name": metadata.get("benchmark_name", "Unknown Benchmark"),
        "companies": companies,
        "column_names": list(df.columns),  # Return actual column names for debugging
    }


# =============================================================================
# PRIVATE HELPER: Extract metadata from the first few rows
# =============================================================================
def _extract_metadata(raw_df: pd.DataFrame) -> dict:
    """
    The first ~10 rows of the Excel contain report metadata like:
    Row 2: "Performance Attribution - Detail"
    Row 3: "Harris Corporation - Large-cap Growth (total return)"  ← portfolio name
    Row 4: "Russell 1000 Growth Index (Total Return)"             ← benchmark name
    Row 5: "11 Groups of TRP GICS Sector"
    Row 6: "09/30/2025 - 12/31/2025"                             ← date range
    Row 7: "Base Currency: U.S. dollar"
    """
    metadata = {}
    
    # Loop through first 10 rows looking for known patterns
    for idx, row in raw_df.iterrows():
        # Get the first non-empty cell in this row
        first_val = str(row.dropna().iloc[0]).strip() if not row.dropna().empty else ""
        
        if not first_val or first_val in ['nan', '']:
            continue
        
        # Row 2 (index 1): Report title
        if idx == 1:
            metadata["report_title"] = first_val
        
        # Row 3 (index 2): Portfolio name (contains "Corporation" or similar)
        elif idx == 2:
            metadata["portfolio_name"] = first_val
        
        # Row 4 (index 3): Benchmark name (often "Russell" or "Index")
        elif idx == 3:
            metadata["benchmark_name"] = first_val
        
        # Row 5 (index 4): Grouping info
        elif idx == 4:
            metadata["grouping"] = first_val
        
        # Look for date range pattern (MM/DD/YYYY - MM/DD/YYYY)
        if re.search(r'\d{1,2}/\d{1,2}/\d{4}', first_val):
            metadata["date_range"] = first_val
        
        # Look for currency info
        if "currency" in first_val.lower():
            metadata["currency"] = first_val
    
    return metadata


# =============================================================================
# PRIVATE HELPER: Find which row contains the column headers
# =============================================================================
def _find_header_row(raw_df: pd.DataFrame) -> int:
    """
    The column header row contains "Company Name" as the first column.
    We search for that row to know where to start reading data.
    
    This makes our parser flexible — it works even if someone adds an
    extra row of metadata in the future.
    """
    for idx, row in raw_df.iterrows():
        # Convert row to string and look for "Company Name"
        row_str = ' '.join([str(v) for v in row.values]).lower()
        if 'company name' in row_str or 'company' in row_str and 'name' in row_str:
            return idx  # This row is the header row
    
    # Default: skip 10 rows if we can't find the header
    return 10


# =============================================================================
# PRIVATE HELPER: Extract company data rows
# =============================================================================
def _extract_companies(df: pd.DataFrame) -> list:
    """
    Goes through each row of the main data section and builds a list
    of company records, tracking which sector each company belongs to.
    
    Key challenge: Some rows are SECTOR HEADERS (e.g., "Health care")
    and some rows are actual COMPANY DATA (e.g., "Abbvie Inc.").
    
    HOW WE TELL THEM APART:
    - Sector header rows: Only have text in the first column, the rest are empty
    - Company rows: Have data in multiple columns (exchange ticker, numbers, etc.)
    - Special rows: "*** Top 10 ***" markers that we skip
    """
    companies = []
    current_sector = None
    
    # Find the "Company Name" column (first column with actual names)
    company_col = find_column(list(df.columns), PORTFOLIO_COLUMNS["company_name"])
    exchange_col = find_column(list(df.columns), PORTFOLIO_COLUMNS["exchange"])
    
    # Find numeric data columns
    avg_weight_col    = find_column(list(df.columns), PORTFOLIO_COLUMNS["avg_weight"])
    ending_weight_col = find_column(list(df.columns), PORTFOLIO_COLUMNS["ending_weight"])
    return_col        = find_column(list(df.columns), PORTFOLIO_COLUMNS["return_pct"])
    contrib_col       = find_column(list(df.columns), PORTFOLIO_COLUMNS["contrib"])
    
    for _, row in df.iterrows():
        # Get the value in the company name column
        name_val = str(row[company_col]).strip() if company_col else ""
        
        # Skip empty rows or separator rows
        if not name_val or name_val in ['', 'nan', 'Company Name']:
            continue
        
        # Skip "*** Top 10 ***" markers
        if "***" in name_val or "top 10" in name_val.lower():
            continue
        
        # Check if this is a SECTOR HEADER ROW
        # Sector rows have text in the name column but mostly empty other columns
        other_values = [str(v).strip() for col, v in row.items() 
                       if col != company_col and str(v).strip() not in ('', 'nan')]
        
        if len(other_values) <= 1:
            # This is a sector header (like "Health care", "Information technology")
            current_sector = name_val
            continue
        
        # This is a real company row — extract all available data
        company_data = {
            "company_name": name_val,
            "sector": current_sector,
            "exchange": _safe_str(row, exchange_col),
            "avg_weight": _safe_float(row, avg_weight_col),
            "ending_weight": _safe_float(row, ending_weight_col),
            "return_pct": _safe_float(row, return_col),
            "contrib": _safe_float(row, contrib_col),
            # Store the full row as a dict for flexibility
            "raw": {col: str(val).strip() for col, val in row.items() 
                   if str(val).strip() not in ('', 'nan')}
        }
        
        companies.append(company_data)
    
    return companies


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
def _safe_float(row, col_name: Optional[str]) -> Optional[float]:
    """Safely get a float value from a row, returning None if not found/invalid."""
    if col_name is None:
        return None
    val = str(row.get(col_name, '')).strip()
    if val in ('', 'nan', 'None', '--'):
        return None
    try:
        return float(val.replace(',', '').replace('%', ''))
    except (ValueError, AttributeError):
        return None


def _safe_str(row, col_name: Optional[str]) -> Optional[str]:
    """Safely get a string value from a row, returning None if not found/empty."""
    if col_name is None:
        return None
    val = str(row.get(col_name, '')).strip()
    return val if val not in ('', 'nan', 'None') else None
