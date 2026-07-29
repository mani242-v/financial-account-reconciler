# =============================================================================
# schemas.py — Pydantic Schemas (Request & Response Shapes)
# =============================================================================
# WHAT IS PYDANTIC?
#   Pydantic is a Python library for data validation.
#   It ensures data coming IN to your API is the right shape,
#   and data going OUT is formatted correctly.
#
# WHAT IS A SCHEMA?
#   A schema defines the "shape" of data — which fields exist, their types,
#   whether they are optional or required, and default values.
#
# WHY SEPARATE FROM MODELS?
#   SQLAlchemy models = how data is stored in the DATABASE
#   Pydantic schemas  = how data looks in API requests/responses
#   They are often similar but serve different purposes.
#   Example: The DB model has a 'password_hash' column, but you'd NEVER
#   include that in an API response schema — you'd expose only safe fields.
# =============================================================================

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# =============================================================================
# JOB SCHEMAS
# =============================================================================

class JobCreate(BaseModel):
    """Schema for CREATING a new job. User must provide filenames."""
    parent_filename: str
    child_filename: str
    template_filename: Optional[str] = None
    match_threshold: float = 85.0  # Default 85% similarity


class JobResponse(BaseModel):
    """
    Schema for the API RESPONSE when returning job data.
    
    'model_config' with from_attributes=True allows Pydantic to read
    data directly from SQLAlchemy model objects (not just dicts).
    Without this, Pydantic wouldn't know how to convert a Job ORM object
    into a JSON-serializable response.
    """
    id: int
    parent_filename: Optional[str]
    child_filename: Optional[str]
    template_filename: Optional[str]
    status: str
    error_message: Optional[str]
    match_threshold: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}  # ← Pydantic v2 way to enable ORM mode


# =============================================================================
# DIFF RECORD SCHEMAS
# =============================================================================

class DiffRecordResponse(BaseModel):
    """Schema for returning one field comparison result."""
    id: int
    job_id: int
    company_name: str
    sector: Optional[str]
    exchange: Optional[str]
    field_name: str
    child_value: Optional[str]
    parent_value: Optional[str]
    is_different: bool
    match_score: Optional[float]

    model_config = {"from_attributes": True}


# =============================================================================
# UPLOAD RESPONSE SCHEMA
# =============================================================================

class UploadResponse(BaseModel):
    """Returned after a file upload succeeds."""
    message: str
    filename: str
    file_path: str


# =============================================================================
# COMPARISON RESULT SCHEMA
# =============================================================================
# This is a richer schema used internally and in API responses
# to show the full comparison result for one company.

class CompanyDiff(BaseModel):
    """
    Represents all field differences for one company.
    
    Example:
    {
        "company_name": "Abbvie Inc.",
        "sector": "Health care",
        "match_score": 100.0,
        "diffs": [
            {"field": "return_pct", "child": "0.0", "parent": "-0.6", "different": true},
            {"field": "avg_weight", "child": "0.0",  "parent": "1.29", "different": true}
        ]
    }
    """
    company_name: str
    matched_parent_name: Optional[str]
    sector: Optional[str]
    exchange: Optional[str]
    match_score: Optional[float]
    diffs: List[dict]  # List of {field, child_value, parent_value, is_different}


class ReconciliationResult(BaseModel):
    """The full result of running a reconciliation job."""
    job_id: int
    total_companies: int
    matched_companies: int
    unmatched_companies: int
    companies_with_differences: int
    results: List[CompanyDiff]


# =============================================================================
# GENERATED FILE SCHEMA
# =============================================================================

class GeneratedFileResponse(BaseModel):
    """Info about a generated Word file."""
    id: int
    job_id: int
    filename: str
    account_name: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
