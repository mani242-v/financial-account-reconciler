# =============================================================================
# database.py — SQLAlchemy Database Setup
# =============================================================================
# WHAT IS SQLAlchemy?
#   SQLAlchemy is a Python library that lets you talk to a database
#   using Python code instead of raw SQL queries.
#   Think of it as a "translator" between Python and SQL.
#
# WHAT IS SQLite?
#   SQLite is a database stored as a single file on disk.
#   Unlike MySQL or PostgreSQL, it needs no server — perfect for learning!
#
# FLOW: Your Python code → SQLAlchemy ORM → SQLite file (reconciler.db)
# =============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ---------------------------------------------------------------------------
# Step 1: Create the "engine" — the connection to the database
# ---------------------------------------------------------------------------
# "sqlite:///./reconciler.db" means:
#   - Use SQLite
#   - The file will be named "reconciler.db"
#   - "./" means "in the current directory"
# check_same_thread=False is needed because FastAPI uses multiple threads
DATABASE_URL = "sqlite:///./reconciler.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# ---------------------------------------------------------------------------
# Step 2: Create a "SessionLocal" factory
# ---------------------------------------------------------------------------
# A "session" is like a temporary workspace for your database operations.
# When you want to read/write data, you open a session, do your work,
# then close the session. Like opening a file, editing it, then closing it.
#
# autocommit=False → changes are NOT saved automatically, you must call .commit()
# autoflush=False  → changes are NOT sent to DB until you explicitly say so
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Step 3: Create the "Base" class for all our models
# ---------------------------------------------------------------------------
# Every database table we create will inherit from this Base class.
# It gives our models the ability to know about the database structure.
class Base(DeclarativeBase):
    pass

# ---------------------------------------------------------------------------
# Step 4: Dependency function for FastAPI
# ---------------------------------------------------------------------------
# FastAPI uses "dependency injection" — you declare what a function needs,
# and FastAPI provides it automatically.
# This function creates a new DB session for each request, then closes it.
def get_db():
    """
    This is a FastAPI dependency.
    
    How it works (using Python's 'yield'):
    1. Creates a new database session
    2. 'yields' it to the route function (like returning, but keeps the function alive)
    3. After the route finishes (or crashes), the 'finally' block runs and closes the session
    
    This ensures we never leave database connections open accidentally.
    """
    db = SessionLocal()
    try:
        yield db          # Give the session to whoever asked for it
    finally:
        db.close()        # Always close, even if an error happened
