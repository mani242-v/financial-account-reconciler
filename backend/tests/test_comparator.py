# =============================================================================
# tests/test_comparator.py — Unit Tests for the Comparison Logic
# =============================================================================
# WHAT IS pytest?
#   pytest is Python's most popular testing framework.
#   You write functions that start with 'test_' and pytest finds and runs them.
#   If a function raises an assertion error → test FAILS
#   If a function completes without errors → test PASSES
#
# WHY WRITE TESTS?
#   1. Confidence: know your code works correctly
#   2. Regression prevention: when you change code, tests catch if you broke something
#   3. Documentation: tests show EXACTLY how functions are supposed to work
#   4. Learning: writing tests forces you to think about edge cases
#
# HOW TO RUN:
#   cd backend
#   pytest tests/ -v
#   (-v = verbose, shows each test name and pass/fail)
# =============================================================================

import pytest
from services.comparator import reconcile, _values_differ, _compare_fields


# =============================================================================
# Test Data Fixtures
# =============================================================================
# In pytest, a "fixture" is reusable test data.
# The @pytest.fixture decorator marks a function as a fixture.
# Other test functions can request it by adding it as a parameter.

@pytest.fixture
def sample_parent_companies():
    """A list of parent (benchmark) company records."""
    return [
        {
            "company_name": "Abbvie Inc.",
            "sector": "Health care",
            "exchange": "ABBV",
            "avg_weight": 1.29,
            "ending_weight": 1.35,
            "return_pct": -0.6,
            "contrib": -0.01
        },
        {
            "company_name": "Natera, Inc.",
            "sector": "Health care",
            "exchange": "NTRA",
            "avg_weight": 0.09,
            "ending_weight": 0.1,
            "return_pct": 42.32,
            "contrib": 0.03
        },
        {
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "exchange": "AAPL",
            "avg_weight": 5.5,
            "ending_weight": 5.8,
            "return_pct": 12.5,
            "contrib": 0.65
        }
    ]


@pytest.fixture
def sample_child_companies():
    """A list of child (portfolio) company records — some data differs from parent."""
    return [
        {
            "company_name": "Abbvie Inc.",   # Exact match with parent
            "sector": "Health care",
            "exchange": "ABBV",
            "avg_weight": 0.0,              # Different! Parent has 1.29
            "ending_weight": 0.0,           # Different! Parent has 1.35
            "return_pct": 0.0,              # Different! Parent has -0.6
            "contrib": 0.0,                 # Different! Parent has -0.01
        },
        {
            "company_name": "Natera Inc",   # Slightly different! (missing comma after "Natera")
            "sector": "Health care",
            "exchange": "NTRA",
            "avg_weight": 0.96,             # Close to parent's 0.09
            "ending_weight": 1.01,
            "return_pct": 42.32,            # Same as parent!
            "contrib": 0.03
        },
        {
            "company_name": "XYZ Corp",     # No match in parent
            "sector": "Utilities",
            "exchange": "XYZ",
            "avg_weight": 2.0,
            "ending_weight": 2.1,
            "return_pct": -5.0,
            "contrib": -0.1
        }
    ]


# =============================================================================
# TEST 1: Basic Reconciliation
# =============================================================================
def test_reconcile_basic(sample_child_companies, sample_parent_companies):
    """
    Tests that the reconcile function:
    - Matches companies correctly
    - Detects differences
    - Reports unmatched companies
    """
    result = reconcile(
        child_companies=sample_child_companies,
        parent_companies=sample_parent_companies,
        threshold=80.0
    )
    
    # Check stats
    assert result["stats"]["total"] == 3
    assert result["stats"]["matched"] == 2          # Abbvie and Natera matched
    assert result["stats"]["unmatched"] == 1        # XYZ Corp has no match
    assert result["stats"]["with_differences"] >= 1 # Abbvie has differences
    
    # Check results list length
    assert len(result["results"]) == 3


# =============================================================================
# TEST 2: Exact Name Match
# =============================================================================
def test_reconcile_exact_match(sample_child_companies, sample_parent_companies):
    """Tests that an exactly matching company name gets a 100% score."""
    result = reconcile(
        child_companies=sample_child_companies,
        parent_companies=sample_parent_companies,
        threshold=85.0
    )
    
    # Find Abbvie in results
    abbvie_result = next(
        r for r in result["results"] if r["company_name"] == "Abbvie Inc."
    )
    
    assert abbvie_result["match_score"] == 100.0
    assert abbvie_result["matched_parent_name"] == "Abbvie Inc."
    assert abbvie_result["status"] == "matched_with_diff"  # Abbvie has differences


# =============================================================================
# TEST 3: Fuzzy Name Match
# =============================================================================
def test_reconcile_fuzzy_match(sample_child_companies, sample_parent_companies):
    """
    Tests that 'Natera Inc' (no comma) matches 'Natera, Inc.' (with comma).
    This is the core fuzzy matching feature.
    """
    result = reconcile(
        child_companies=sample_child_companies,
        parent_companies=sample_parent_companies,
        threshold=80.0
    )
    
    natera_result = next(
        r for r in result["results"] if "Natera" in r["company_name"]
    )
    
    # Should match even though names are slightly different
    assert natera_result["matched_parent_name"] == "Natera, Inc."
    assert natera_result["match_score"] >= 80.0  # Above our threshold


# =============================================================================
# TEST 4: Unmatched Company
# =============================================================================
def test_reconcile_unmatched(sample_child_companies, sample_parent_companies):
    """Tests that a company with no close match is marked as unmatched."""
    result = reconcile(
        child_companies=sample_child_companies,
        parent_companies=sample_parent_companies,
        threshold=85.0
    )
    
    xyz_result = next(
        r for r in result["results"] if r["company_name"] == "XYZ Corp"
    )
    
    assert xyz_result["status"] == "unmatched"
    assert xyz_result["matched_parent_name"] is None
    assert xyz_result["match_score"] is None


# =============================================================================
# TEST 5: High Threshold Rejects Fuzzy Match
# =============================================================================
def test_reconcile_high_threshold():
    """
    Tests that a very high threshold (100%) rejects fuzzy matches.
    'Natera Inc' vs 'Natera, Inc.' should NOT match at 100% threshold.
    """
    child = [{"company_name": "Natera Inc", "sector": "HC", "exchange": "NTRA",
              "avg_weight": 1.0, "ending_weight": 1.0, "return_pct": 1.0, "contrib": 0.1}]
    parent = [{"company_name": "Natera, Inc.", "sector": "HC", "exchange": "NTRA",
               "avg_weight": 1.0, "ending_weight": 1.0, "return_pct": 1.0, "contrib": 0.1}]
    
    result = reconcile(child, parent, threshold=100.0)
    
    assert result["stats"]["unmatched"] == 1   # Should not match at 100% threshold


# =============================================================================
# TEST 6: Values Differ Helper — Numeric Tolerance
# =============================================================================
def test_values_differ_numeric_tolerance():
    """
    Tests that values within 0.001 of each other are considered EQUAL.
    This is important for floating-point precision issues.
    """
    # These should be considered equal (within tolerance)
    assert _values_differ(2.5000001, 2.5) == False
    assert _values_differ(0.0, 0.0) == False
    assert _values_differ(1.29, 1.29) == False
    
    # These should be considered different
    assert _values_differ(1.29, 0.0) == True
    assert _values_differ(-0.6, 0.0) == True


# =============================================================================
# TEST 7: Values Differ Helper — Both None
# =============================================================================
def test_values_differ_both_none():
    """Both values being None means they AGREE (both are missing = no difference)."""
    assert _values_differ(None, None) == False


# =============================================================================
# TEST 8: Values Differ Helper — One None
# =============================================================================
def test_values_differ_one_none():
    """If one value exists and the other doesn't, that's a difference."""
    assert _values_differ(None, 1.29) == True
    assert _values_differ(1.29, None) == True


# =============================================================================
# TEST 9: Empty Input
# =============================================================================
def test_reconcile_empty_inputs():
    """Tests that empty inputs don't crash the function."""
    result = reconcile([], [], threshold=85.0)
    assert result["stats"]["total"] == 0
    assert result["results"] == []


# =============================================================================
# TEST 10: All Fields Match (No Differences)
# =============================================================================
def test_reconcile_no_differences():
    """Tests the case where child and parent data are identical."""
    company = {
        "company_name": "Test Corp",
        "sector": "Technology",
        "exchange": "TC",
        "avg_weight": 2.5,
        "ending_weight": 2.7,
        "return_pct": 5.0,
        "contrib": 0.12
    }
    
    result = reconcile([company], [company], threshold=85.0)
    
    assert result["stats"]["with_differences"] == 0
    assert result["results"][0]["status"] == "matched_ok"
