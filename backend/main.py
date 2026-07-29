# =============================================================================
# main.py — FastAPI Application Entry Point
# =============================================================================
# THIS IS WHERE EVERYTHING COMES TOGETHER.
#
# WHAT IS FastAPI?
#   FastAPI is a modern Python web framework for building APIs.
#   - "API" = Application Programming Interface (a way for programs to talk to each other)
#   - Our React frontend calls our FastAPI backend via HTTP requests
#   - FastAPI handles routing, validation, serialization automatically
#
# HOW AN API REQUEST FLOWS:
#   Browser (React) → HTTP Request → FastAPI (main.py) → Router → Service → Database
#                                                                          ↓
#   Browser (React) ← HTTP Response ← FastAPI (serializes to JSON) ← Return value
#
# KEY FastAPI FEATURES USED:
#   1. @app.get, @app.post → Route decorators (map URLs to functions)
#   2. Depends()           → Dependency injection (auto-provide DB sessions, etc.)
#   3. response_model=     → Auto-serialize response to correct JSON shape
#   4. CORSMiddleware      → Allow the React frontend to talk to this backend
#
# HOW TO RUN:
#   uvicorn main:app --reload
#   - 'main'   = the file name (main.py)
#   - 'app'    = the FastAPI() instance variable name
#   - --reload = auto-restart when you save changes (great for development!)
#
# LIVE DOCS:
#   Once running, visit http://localhost:8000/docs
#   FastAPI automatically generates an interactive API documentation page!
#   You can test all endpoints directly in the browser — no Postman needed.
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our database setup
from database import engine, Base

# Import our routers (groups of related endpoints)
from routers import upload, jobs, generate

# =============================================================================
# Step 1: Create the FastAPI Application Instance
# =============================================================================
app = FastAPI(
    title="Financial Account Reconciler",
    description="""
    ## What this API does
    - Upload parent (benchmark) and child (portfolio) Excel files
    - Fuzzy-match company names between the two files
    - Compare financial data fields (weights, returns, contributions)
    - Generate Word document reports from a template
    - Track all reconciliation jobs in a SQLite database
    
    ## How to use
    1. POST /upload/parent → upload parent Excel
    2. POST /upload/child  → upload child Excel
    3. POST /upload/template → upload Word template
    4. POST /jobs/ → create job and run comparison
    5. GET /jobs/{id}/diff → view results
    6. POST /generate/{id} → generate Word files
    7. GET /generate/download/{filename} → download files
    """,
    version="1.0.0"
)

# =============================================================================
# Step 2: Create Database Tables
# =============================================================================
# Base.metadata.create_all() reads all our SQLAlchemy models (Job, DiffRecord, etc.)
# and creates the corresponding tables in SQLite if they don't exist yet.
#
# This is safe to call every time the app starts — it uses "CREATE TABLE IF NOT EXISTS"
# so it won't destroy existing data.
Base.metadata.create_all(bind=engine)

# =============================================================================
# Step 3: Add CORS Middleware
# =============================================================================
# WHAT IS CORS?
#   CORS = Cross-Origin Resource Sharing
#   By default, web browsers BLOCK JavaScript from making requests to a different
#   "origin" (domain + port) for security reasons.
#
#   Our setup:
#   - React frontend runs at: http://localhost:5173  (Vite's default port)
#   - FastAPI backend runs at: http://localhost:8000
#
#   These are different origins (different ports), so the browser would block
#   all API calls from React to FastAPI!
#
#   Adding CORSMiddleware tells the browser: "It's okay for localhost:5173
#   to make requests to this server."
#
# WARNING: In production, change "*" to your actual frontend domain!
import os

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins_env.split(",")] if allowed_origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],       # Allow GET, POST, PUT, DELETE, PATCH, OPTIONS
    allow_headers=["*"],       # Allow all HTTP headers
)

# =============================================================================
# Step 4: Register Routers
# =============================================================================
# include_router() attaches all routes from a Router to the main app.
# 'prefix' adds a URL prefix to all routes in that router.
# 'tags'   groups the routes together in the auto-generated /docs page.
#
# Result:
#   /upload/parent       (from routers/upload.py: @router.post("/parent"))
#   /upload/child        (from routers/upload.py: @router.post("/child"))
#   /jobs/               (from routers/jobs.py: @router.get("/"))
#   /jobs/{id}/diff      (from routers/jobs.py: @router.get("/{id}/diff"))
#   /generate/{id}       (from routers/generate.py: @router.post("/{id}"))
#   /generate/download/  (from routers/generate.py: @router.get("/download/{f}"))

app.include_router(upload.router,   prefix="/upload",   tags=["📁 File Upload"])
app.include_router(jobs.router,     prefix="/jobs",     tags=["⚙️  Jobs"])
app.include_router(generate.router, prefix="/generate", tags=["📄 Word Generation"])

# =============================================================================
# Step 5: Mount Frontend Static Files & Health Endpoints
# =============================================================================
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Path to the compiled frontend dist directory
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

@app.get("/health", tags=["Health"])
def health_check():
    """Detailed health check with database connectivity test."""
    from database import SessionLocal
    try:
        db = SessionLocal()
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    
    return {
        "api": "running",
        "database": db_status
    }

# If the frontend has been built (frontend/dist exists), serve the React application!
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
else:
    @app.get("/", tags=["Health"])
    def root():
        """Fallback health check endpoint when frontend is not built."""
        return {
            "status": "✅ Financial Reconciler API is running",
            "docs": "Visit /docs for interactive API documentation",
            "version": "1.0.0"
        }
