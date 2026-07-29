# =============================================================================
# routers/jobs.py — Job Management Endpoints
# =============================================================================
# WHAT IS A "JOB" IN OUR APP?
#   A "Job" is a single reconciliation task. When a user:
#   1. Uploads parent + child Excel files
#   2. Clicks "Run Reconciliation"
#   We create a Job record in the database, run the comparison,
#   and store all the results linked to that Job.
#
# WHY STORE JOBS IN A DATABASE?
#   - History: user can come back later and see past comparisons
#   - Audit: "who compared what on which date?"
#   - Re-generate: user can re-download Word files without re-uploading
#
# ENDPOINTS IN THIS ROUTER:
#   POST /jobs/          → Create new job + run reconciliation
#   GET  /jobs/          → List all jobs
#   GET  /jobs/{id}      → Get one job's details
#   GET  /jobs/{id}/diff → Get the full diff results for a job
#   DELETE /jobs/{id}    → Delete a job and all its records
# =============================================================================

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Job, DiffRecord, GeneratedFile
from schemas import JobCreate, JobResponse, DiffRecordResponse, ReconciliationResult
from services.excel_parser import parse_excel
from services.comparator import reconcile

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"

router = APIRouter()


# =============================================================================
# ENDPOINT: Create a New Job (= Run Reconciliation)
# =============================================================================
@router.post("/", response_model=JobResponse)
def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
    """
    Creates a new job, runs the reconciliation, and stores results in DB.
    
    HOW DEPENDENCY INJECTION WORKS HERE:
    'db: Session = Depends(get_db)'
    
    FastAPI sees 'Depends(get_db)' and knows to:
    1. Call our get_db() function from database.py
    2. Get a SQLAlchemy Session from it
    3. Pass that session as the 'db' parameter to this function
    4. Close the session when this function is done
    
    You never have to manually create or close DB sessions — FastAPI does it!
    
    'response_model=JobResponse' tells FastAPI:
    "Convert the return value to a JobResponse Pydantic schema"
    This ensures the response has only the fields defined in JobResponse.
    """
    # ------------------------------------------------------------------
    # STEP 1: Verify uploaded files exist
    # ------------------------------------------------------------------
    parent_path = UPLOAD_DIR / job_data.parent_filename
    child_path  = UPLOAD_DIR / job_data.child_filename
    
    if not parent_path.exists():
        raise HTTPException(404, f"Parent file '{job_data.parent_filename}' not found. Upload it first.")
    if not child_path.exists():
        raise HTTPException(404, f"Child file '{job_data.child_filename}' not found. Upload it first.")
    
    # ------------------------------------------------------------------
    # STEP 2: Create the Job record in the database
    # ------------------------------------------------------------------
    # 'Job(**job_data.model_dump())' converts the Pydantic schema to a dict
    # and unpacks it as keyword arguments to the Job constructor.
    # Equivalent to: Job(parent_filename=..., child_filename=..., ...)
    new_job = Job(
        parent_filename=job_data.parent_filename,
        child_filename=job_data.child_filename,
        template_filename=job_data.template_filename,
        match_threshold=job_data.match_threshold,
        status="processing"
    )
    db.add(new_job)     # Stage the new record (not saved yet)
    db.commit()          # Actually write to the database
    db.refresh(new_job)  # Reload from DB to get the auto-generated 'id'
    
    try:
        # ------------------------------------------------------------------
        # STEP 3: Parse both Excel files
        # ------------------------------------------------------------------
        parent_data = parse_excel(str(parent_path))
        child_data  = parse_excel(str(child_path))
        
        # ------------------------------------------------------------------
        # STEP 4: Run the comparison
        # ------------------------------------------------------------------
        reconciliation = reconcile(
            child_companies=child_data["companies"],
            parent_companies=parent_data["companies"],
            threshold=job_data.match_threshold
        )
        
        # ------------------------------------------------------------------
        # STEP 5: Save all DiffRecords to the database
        # ------------------------------------------------------------------
        # For each company result, save one DiffRecord per field comparison
        for company_result in reconciliation["results"]:
            for diff in company_result["diffs"]:
                record = DiffRecord(
                    job_id=new_job.id,
                    company_name=company_result["company_name"],
                    sector=company_result.get("sector"),
                    exchange=company_result.get("exchange"),
                    field_name=diff["field"],
                    child_value=diff["child_value"],
                    parent_value=diff["parent_value"],
                    is_different=diff["is_different"],
                    match_score=company_result.get("match_score")
                )
                db.add(record)
        
        # Update job status to completed
        new_job.status = "completed"
        new_job.error_message = None
        db.commit()
        db.refresh(new_job)
        
        # Store reconciliation results temporarily in job's metadata
        # (We'll return them via /jobs/{id}/diff endpoint)
        
    except Exception as e:
        # If anything goes wrong, mark the job as failed
        new_job.status = "error"
        new_job.error_message = str(e)
        db.commit()
        raise HTTPException(500, f"Reconciliation failed: {str(e)}")
    
    return new_job


# =============================================================================
# ENDPOINT: List All Jobs
# =============================================================================
@router.get("/", response_model=List[JobResponse])
def list_jobs(
    skip: int = 0,      # For pagination: skip first N results
    limit: int = 50,    # For pagination: return max N results
    db: Session = Depends(get_db)
):
    """
    Returns all jobs, newest first.
    
    PAGINATION EXPLAINED:
    If you have 1000 jobs, you don't want to return all 1000 at once.
    Instead, you return them in "pages":
    - Page 1: skip=0,  limit=50 → jobs 1-50
    - Page 2: skip=50, limit=50 → jobs 51-100
    - etc.
    
    SQLAlchemy query syntax:
    db.query(Job)           → "SELECT * FROM jobs"
    .order_by(Job.id.desc()) → "ORDER BY id DESC"
    .offset(skip)            → "OFFSET N" (skip N rows)
    .limit(limit)            → "LIMIT N"  (return max N rows)
    .all()                   → Execute and return as Python list
    """
    jobs = (
        db.query(Job)
        .order_by(Job.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return jobs


# =============================================================================
# ENDPOINT: Get One Job
# =============================================================================
@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """
    Get details of a specific job by ID.
    
    Path parameters in FastAPI:
    The '{job_id}' in the URL becomes the 'job_id' parameter.
    FastAPI automatically converts it to an int (or returns 422 if not a number).
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return job


# =============================================================================
# ENDPOINT: Get Diff Results for a Job
# =============================================================================
@router.get("/{job_id}/diff")
def get_job_diff(job_id: int, db: Session = Depends(get_db)):
    """
    Returns the full reconciliation results for a job.
    Re-runs the comparison from the stored files (or reads from DB records).
    
    We RE-RUN the comparison here instead of storing the full result as JSON
    in the database, because:
    1. DB space is limited — the full result can be large
    2. Re-running is fast (usually < 1 second)
    3. It allows changing threshold without re-uploading files
    """
    # Find the job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    
    if job.status != "completed":
        raise HTTPException(400, f"Job {job_id} is in '{job.status}' status, not yet completed")
    
    UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
    parent_path = UPLOAD_DIR / job.parent_filename
    child_path  = UPLOAD_DIR / job.child_filename
    
    try:
        parent_data = parse_excel(str(parent_path))
        child_data  = parse_excel(str(child_path))
        
        reconciliation = reconcile(
            child_companies=child_data["companies"],
            parent_companies=parent_data["companies"],
            threshold=job.match_threshold
        )
        
        return {
            "job_id": job_id,
            "parent_metadata": parent_data["metadata"],
            "child_metadata": child_data["metadata"],
            "stats": reconciliation["stats"],
            "results": reconciliation["results"]
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to compute diff: {str(e)}")


# =============================================================================
# ENDPOINT: Delete a Job
# =============================================================================
@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """
    Delete a job and all its associated records.
    
    Because we set 'cascade="all, delete-orphan"' in our Job model's
    relationships, SQLAlchemy automatically deletes all linked
    DiffRecords and GeneratedFiles when we delete the Job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    
    db.delete(job)
    db.commit()
    
    return {"message": f"Job {job_id} deleted successfully"}
