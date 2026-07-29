# =============================================================================
# services/comparator.py — Compare Child vs Parent Account Data
# =============================================================================
# WHAT THIS FILE DOES:
#   Takes the parsed data from both Excel files and finds differences.
#   Uses "fuzzy matching" to match company names even if they're slightly
#   different (e.g., "Abbvie Inc." vs "AbbVie, Inc." → still a match!)
#
# WHAT IS FUZZY MATCHING?
#   Regular string comparison: "Abbvie Inc." == "AbbVie Inc." → FALSE (case differs)
#   Fuzzy matching:            "Abbvie Inc." ≈ "AbbVie Inc." → TRUE (95% similar)
#
#   rapidfuzz calculates a "similarity score" from 0 to 100:
#   - 100 = identical strings
#   - 85  = very similar (minor differences like case, punctuation)
#   - 50  = somewhat similar (same words, different order)
#   - 0   = completely different
#
# HOW RAPIDFUZZ WORKS (token_set_ratio):
#   "Harris Corporation Inc." vs "Harris Corp."
#   Step 1: Split into tokens: ["harris", "corporation", "inc"] vs ["harris", "corp"]
#   Step 2: Find common tokens: ["harris"]
#   Step 3: Score based on overlap → ~80/100
#
# WHY USE rapidfuzz INSTEAD OF fuzzywuzzy?
#   rapidfuzz is 10-100x FASTER because it's implemented in C++.
#   For large Excel files with thousands of rows, speed matters a lot.
# =============================================================================

from typing import Optional
from rapidfuzz import process, fuzz


# =============================================================================
# CONSTANTS
# =============================================================================
# Fields we compare between child and parent records
# This is a list of (internal_name, display_label) pairs
COMPARISON_FIELDS = [
    ("avg_weight",    "Average Weight"),
    ("ending_weight", "Ending Weight"),
    ("return_pct",    "Return (%)"),
    ("contrib",       "Contribution"),
]

# Tolerance for numeric comparison
# 0.001 means values within 0.001 of each other are considered equal
# This prevents false differences from floating-point precision issues
NUMERIC_TOLERANCE = 0.001


# =============================================================================
# MAIN FUNCTION: Run Full Reconciliation
# =============================================================================
def reconcile(
    child_companies: list,
    parent_companies: list,
    threshold: float = 85.0
) -> dict:
    """
    Compare each child company against the parent companies.
    
    ALGORITHM:
    1. For each company in the child file:
       a. Use rapidfuzz to find the best-matching company in the parent file
       b. If match score >= threshold, compare their financial fields
       c. Record any differences found
    2. Collect stats: how many matched? how many had differences?
    
    Args:
        child_companies:  List of company dicts from the child Excel
        parent_companies: List of company dicts from the parent Excel
        threshold:        Minimum fuzzy match score (0-100) to consider a match
    
    Returns:
        {
            "results": [CompanyDiff, ...],  # One entry per child company
            "stats": {
                "total": int,
                "matched": int,
                "unmatched": int,
                "with_differences": int
            }
        }
    """
    # Build a list of parent company names for rapidfuzz to search through
    # rapidfuzz needs a list of strings to compare against
    parent_names = [c["company_name"] for c in parent_companies]
    
    # Build a lookup dict: parent_name → parent_company_data
    # This lets us quickly find a parent company once we know its name
    parent_lookup = {c["company_name"]: c for c in parent_companies}
    
    results = []
    stats = {
        "total": len(child_companies),
        "matched": 0,
        "unmatched": 0,
        "with_differences": 0
    }
    
    for child_company in child_companies:
        child_name = child_company["company_name"]
        
        # ---------------------------------------------------------------
        # STEP 1: Find the best matching parent company using rapidfuzz
        # ---------------------------------------------------------------
        # process.extractOne() finds the SINGLE best match
        # It returns: (matched_string, score, index) or None
        #
        # fuzz.WRatio is a "smart" scorer that tries multiple algorithms
        # and picks the best result — good for company names
        match_result = process.extractOne(
            query=child_name,           # The name we're searching for
            choices=parent_names,       # The list to search in
            scorer=fuzz.WRatio,         # Scoring algorithm
            score_cutoff=threshold      # Only return results >= threshold
        )
        
        if match_result is None:
            # No match found above the threshold
            results.append({
                "company_name": child_name,
                "matched_parent_name": None,
                "sector": child_company.get("sector"),
                "exchange": child_company.get("exchange"),
                "match_score": None,
                "diffs": [],
                "status": "unmatched"
            })
            stats["unmatched"] += 1
            continue
        
        # match_result = (matched_name, score, index)
        matched_name, match_score, _ = match_result
        parent_company = parent_lookup[matched_name]
        stats["matched"] += 1
        
        # ---------------------------------------------------------------
        # STEP 2: Compare the financial fields between child and parent
        # ---------------------------------------------------------------
        diffs = _compare_fields(child_company, parent_company)
        
        has_differences = any(d["is_different"] for d in diffs)
        if has_differences:
            stats["with_differences"] += 1
        
        results.append({
            "company_name": child_name,
            "matched_parent_name": matched_name,
            "sector": child_company.get("sector"),
            "exchange": child_company.get("exchange"),
            "match_score": round(match_score, 2),
            "diffs": diffs,
            "status": "matched_with_diff" if has_differences else "matched_ok"
        })
    
    return {"results": results, "stats": stats}


# =============================================================================
# HELPER: Compare Individual Fields
# =============================================================================
def _compare_fields(child: dict, parent: dict) -> list:
    """
    Compare each financial field between child and parent records.
    
    For NUMERIC fields: Use tolerance comparison
    For STRING fields: Use exact comparison (after normalization)
    
    Returns a list of diff objects:
    [
        {
            "field": "avg_weight",
            "label": "Average Weight",
            "child_value": "0.0",
            "parent_value": "1.29",
            "is_different": True,
            "diff_amount": -1.29    # parent - child
        },
        ...
    ]
    """
    diffs = []
    
    for field_key, field_label in COMPARISON_FIELDS:
        child_val = child.get(field_key)
        parent_val = parent.get(field_key)
        
        # Determine if values are different
        is_different = _values_differ(child_val, parent_val)
        
        # Calculate numeric difference (for reporting purposes)
        diff_amount = None
        if isinstance(child_val, (int, float)) and isinstance(parent_val, (int, float)):
            if child_val is not None and parent_val is not None:
                diff_amount = round(parent_val - child_val, 6)
        
        diffs.append({
            "field": field_key,
            "label": field_label,
            "child_value":  _format_value(child_val),
            "parent_value": _format_value(parent_val),
            "is_different": is_different,
            "diff_amount": diff_amount
        })
    
    return diffs


# =============================================================================
# HELPER: Check If Two Values Are Different
# =============================================================================
def _values_differ(child_val, parent_val) -> bool:
    """
    Compare two values intelligently.
    
    Cases handled:
    1. Both None → NOT different (both missing = they agree)
    2. One is None, other is not → IS different
    3. Both are numbers → compare with tolerance (0.001)
    4. Both are strings → compare after stripping whitespace + lowercasing
    
    WHY TOLERANCE FOR NUMBERS?
    Floating point numbers in computers can have tiny precision errors.
    For example: 0.1 + 0.2 = 0.30000000000000004 (not exactly 0.3)
    So "2.5000001" and "2.5" should be considered EQUAL.
    """
    # Case 1: Both None or empty
    if child_val is None and parent_val is None:
        return False
    
    # Case 2: One is missing
    if child_val is None or parent_val is None:
        return True
    
    # Case 3: Both numeric
    if isinstance(child_val, (int, float)) and isinstance(parent_val, (int, float)):
        return abs(float(child_val) - float(parent_val)) > NUMERIC_TOLERANCE
    
    # Case 4: Both strings — normalize before comparing
    return str(child_val).strip().lower() != str(parent_val).strip().lower()


def _format_value(val) -> Optional[str]:
    """Convert a value to a display-friendly string."""
    if val is None:
        return "N/A"
    if isinstance(val, float):
        return f"{val:.4f}"
    return str(val)
