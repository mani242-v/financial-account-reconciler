# =============================================================================
# routers/upload.py — File Upload Endpoints
# =============================================================================
# WHAT IS A ROUTER?
#   In FastAPI, a "Router" is a way to group related endpoints together.
#   Instead of putting ALL endpoints in main.py (which would get huge),
#   we split them into separate files by feature: upload, jobs, generate.
#
#   Then in main.py, we "include" each router:
#     app.include_router(upload_router, prefix="/upload")
#   This means all endpoints in this file will start with "/upload/..."
#
# WHAT ARE WE BUILDING HERE?
#   Three upload endpoints:
#   POST /upload/parent   → Upload the parent (benchmark) Excel file
#   POST /upload/child    → Upload the child (portfolio) Excel file
#   POST /upload/template → Upload the Word template file
#
# HOW FILE UPLOADS WORK IN FastAPI:
#   FastAPI uses "UploadFile" for file uploads.
#   Files are sent via HTTP multipart/form-data (the same way HTML forms work).
#   We read the file bytes and save them to the uploads/ directory.
# =============================================================================

import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

# Where uploaded files will be stored
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)  # Create the directory if it doesn't exist

# APIRouter is like a mini FastAPI app — it groups related routes
router = APIRouter()


# =============================================================================
# ENDPOINT: Upload Parent Excel File
# =============================================================================
@router.post("/parent")
async def upload_parent(file: UploadFile = File(...)):
    """
    Upload the parent/benchmark Excel file.
    
    HOW THIS ENDPOINT WORKS:
    1. Receive the uploaded file (FastAPI handles the HTTP parsing)
    2. Validate the file extension is .xlsx or .xls
    3. Generate a unique filename to avoid conflicts
    4. Save the file to the uploads/ directory
    5. Return the saved filename (so the client can reference it later)
    
    Args:
        file: UploadFile — FastAPI's file upload object
              - file.filename: original filename ("benchmark.xlsx")
              - file.content_type: MIME type ("application/vnd.openxmlformats...")
              - await file.read(): get file bytes
    
    The 'async def' and 'await' keywords:
    FastAPI is async (asynchronous) — it can handle multiple requests at once
    without waiting for one to finish before starting another.
    'await' means "pause here until this async operation completes".
    """
    return await _save_uploaded_file(file, allowed_extensions=[".xlsx", ".xls"])


# =============================================================================
# ENDPOINT: Upload Child Excel File
# =============================================================================
@router.post("/child")
async def upload_child(file: UploadFile = File(...)):
    """Upload the child/portfolio Excel file."""
    return await _save_uploaded_file(file, allowed_extensions=[".xlsx", ".xls"])


# =============================================================================
# ENDPOINT: Upload Word Template
# =============================================================================
@router.post("/template")
async def upload_template(file: UploadFile = File(...)):
    """
    Upload the Word template (.docx) file.
    
    The template should contain {{PLACEHOLDER}} syntax.
    We also provide a sample template download at GET /upload/sample-template
    """
    return await _save_uploaded_file(file, allowed_extensions=[".docx"])


# =============================================================================
# ENDPOINT: Download Sample Template
# =============================================================================
@router.get("/sample-template")
async def get_sample_template():
    """
    Generate and return a sample Word template.
    
    This helps users understand what placeholders to use.
    Uses FastAPI's FileResponse to return a file download.
    """
    from fastapi.responses import FileResponse
    from services.doc_generator import create_sample_template
    
    sample_path = str(UPLOAD_DIR / "sample_template.docx")
    create_sample_template(sample_path)
    
    return FileResponse(
        path=sample_path,
        filename="sample_template.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


# =============================================================================
# ENDPOINT: Preview Excel Contents
# =============================================================================
@router.get("/preview/{filename}")
async def preview_excel(filename: str):
    """
    Parse an uploaded Excel file and return its contents as JSON.
    Useful for showing users what was detected in their uploaded file.
    """
    # Security: only allow filenames without path separators
    # (prevents "directory traversal" attacks like "../../secret.txt")
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
    
    try:
        from services.excel_parser import parse_excel
        result = parse_excel(str(file_path))
        
        # Don't return raw data for huge files — limit to first 20 companies
        companies_preview = result["companies"][:20]
        
        return {
            "metadata": result["metadata"],
            "portfolio_name": result["portfolio_name"],
            "benchmark_name": result["benchmark_name"],
            "total_companies": len(result["companies"]),
            "companies_preview": companies_preview,
            "column_names": result["column_names"]
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse Excel file: {str(e)}")


# =============================================================================
# SHARED HELPER FUNCTION
# =============================================================================
async def _save_uploaded_file(file: UploadFile, allowed_extensions: list) -> dict:
    """
    Shared logic for saving any uploaded file.
    
    Steps:
    1. Validate file extension
    2. Generate a unique filename using UUID (Universally Unique ID)
    3. Read file bytes and write to disk
    4. Return info about the saved file
    
    WHY UUID FOR FILENAMES?
    If two users upload "report.xlsx" at the same time, they'd overwrite each other!
    UUID generates a random string like "a3f8b2c1-9e4d-..."
    Making the filename "a3f8b2c1_report.xlsx" — guaranteed to be unique.
    """
    original_name = file.filename or "upload"
    suffix = Path(original_name).suffix.lower()
    
    # Validate file type
    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{suffix}'. Allowed: {allowed_extensions}"
        )
    
    # Generate unique filename: uuid4 creates a random unique ID
    unique_id = str(uuid.uuid4())[:8]  # Use first 8 chars for brevity
    safe_original = re.sub(r'[^\w.-]', '_', Path(original_name).stem)
    saved_filename = f"{unique_id}_{safe_original}{suffix}"
    save_path = UPLOAD_DIR / saved_filename
    
    # Read file content and write to disk
    # 'rb'/'wb' = read/write in "binary" mode (for non-text files like Excel)
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)
    
    return {
        "message": "File uploaded successfully",
        "filename": saved_filename,
        "original_filename": original_name,
        "file_path": str(save_path),
        "size_bytes": len(content)
    }


# Fix: import re was missing from the helper
import re
