# =============================================================================
# routers/generate.py — Word Document Generation Endpoints
# =============================================================================
# WHAT THIS ROUTER DOES:
#   After a job is completed (parent vs child comparison done),
#   the user can trigger Word file generation.
#
#   POST /generate/{job_id}        → Generate Word files for a job
#   GET  /generate/{job_id}/files  → List generated files for a job
#   GET  /generate/download/{fname} → Download a specific generated file
# =============================================================================

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Job, GeneratedFile
from services.excel_parser import parse_excel
from services.comparator import reconcile
from services.doc_generator import generate_word_files

UPLOAD_DIR  = Path(__file__).parent.parent / "uploads"
OUTPUT_DIR  = Path(__file__).parent.parent / "outputs"

router = APIRouter()


# =============================================================================
# ENDPOINT: Generate Word Files for a Job
# =============================================================================
@router.post("/{job_id}")
def generate_for_job(job_id: int, db: Session = Depends(get_db)):
    """
    Triggers Word document generation for a completed job.
    
    Flow:
    1. Load the job from DB
    2. Verify it's completed and has a template
    3. Re-run reconciliation to get fresh data
    4. Call doc_generator to create one .docx per sector
    5. Save GeneratedFile records to DB
    6. Return list of generated filenames
    """
    # Find the job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    
    if job.status != "completed":
        raise HTTPException(400, f"Job must be completed before generating files. Current status: {job.status}")
    
    if not job.template_filename:
        raise HTTPException(400, "No template file associated with this job. Upload a template first.")
    
    template_path = UPLOAD_DIR / job.template_filename
    if not template_path.exists():
        raise HTTPException(404, f"Template file '{job.template_filename}' not found")
    
    try:
        # Re-run reconciliation to get the data
        parent_data = parse_excel(str(UPLOAD_DIR / job.parent_filename))
        child_data  = parse_excel(str(UPLOAD_DIR / job.child_filename))
        
        reconciliation = reconcile(
            child_companies=child_data["companies"],
            parent_companies=parent_data["companies"],
            threshold=job.match_threshold
        )
        
        # Generate Word files
        generated = generate_word_files(
            template_path=str(template_path),
            reconciliation_results=reconciliation,
            metadata={**parent_data["metadata"], **child_data["metadata"]},
            job_id=job_id
        )
        
        # Save GeneratedFile records to DB
        # First delete any old generated files for this job
        db.query(GeneratedFile).filter(GeneratedFile.job_id == job_id).delete()
        
        for gen_file in generated:
            gf = GeneratedFile(
                job_id=job_id,
                filename=gen_file["filename"],
                account_name=gen_file["account_name"]
            )
            db.add(gf)
        
        db.commit()
        
        return {
            "message": f"Generated {len(generated)} Word files",
            "files": generated
        }
        
    except Exception as e:
        raise HTTPException(500, f"File generation failed: {str(e)}")


# =============================================================================
# ENDPOINT: List Generated Files for a Job
# =============================================================================
@router.get("/{job_id}/files")
def list_generated_files(job_id: int, db: Session = Depends(get_db)):
    """Returns all generated Word files for a specific job."""
    files = db.query(GeneratedFile).filter(GeneratedFile.job_id == job_id).all()
    return {
        "job_id": job_id,
        "files": [{"id": f.id, "filename": f.filename, "account_name": f.account_name} for f in files]
    }


# =============================================================================
# ENDPOINT: Download a Generated File
# =============================================================================
@router.get("/download/{filename}")
def download_file(filename: str):
    """
    Stream a generated Word file back to the client for download.
    
    Security note: We validate the filename to prevent path traversal.
    FileResponse is FastAPI's way to return files for download.
    It streams the file in chunks (good for large files).
    """
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, f"File '{filename}' not found")
    
    # FileResponse sets the right Content-Disposition header
    # so the browser knows to download (not display) the file
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


# =============================================================================
# ENDPOINT: Update Template for Existing Job
# =============================================================================
@router.patch("/{job_id}/template")
def update_job_template(job_id: int, template_filename: str, db: Session = Depends(get_db)):
    """
    Attach a different template to an existing job.
    Useful when user uploads a new template and wants to re-generate.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    
    template_path = UPLOAD_DIR / template_filename
    if not template_path.exists():
        raise HTTPException(404, f"Template '{template_filename}' not found. Upload it first.")
    
    job.template_filename = template_filename
    db.commit()
    
    return {"message": f"Template updated for job {job_id}", "template": template_filename}
