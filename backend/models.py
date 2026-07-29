# =============================================================================
# models.py — Database Table Definitions (SQLAlchemy ORM Models)
# =============================================================================
# WHAT IS AN ORM MODEL?
#   ORM = Object-Relational Mapper
#   Instead of writing SQL like:
#     CREATE TABLE jobs (id INTEGER PRIMARY KEY, status TEXT, ...)
#   We write Python classes, and SQLAlchemy creates the SQL for us.
#
#   Each Python class = one database TABLE
#   Each class attribute = one database COLUMN
# =============================================================================

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base  # Import the Base class we created in database.py


# =============================================================================
# TABLE 1: Job
# =============================================================================
# A "Job" represents one reconciliation task:
#   "I uploaded parent.xlsx, child.xlsx, and template.docx → compare them"
# Each job gets a unique ID and tracks what files were used.
# =============================================================================
class Job(Base):
    # __tablename__ tells SQLAlchemy what to name this table in the database
    __tablename__ = "jobs"

    # ---------- Columns ----------
    # Integer, primary_key=True → auto-incrementing ID (1, 2, 3, ...)
    id = Column(Integer, primary_key=True, index=True)

    # String(255) → text column, max 255 characters
    # nullable=True means this column can be empty (NULL in SQL)
    parent_filename = Column(String(255), nullable=True)
    child_filename = Column(String(255), nullable=True)
    template_filename = Column(String(255), nullable=True)

    # Status of the job: "pending", "processing", "completed", "error"
    status = Column(String(50), default="pending")

    # Text = unlimited length string (for storing error messages)
    error_message = Column(Text, nullable=True)

    # Fuzzy match threshold used for this job (0.0 to 100.0)
    match_threshold = Column(Float, default=85.0)

    # DateTime → stores date and time
    # default=datetime.utcnow → auto-sets to current time when job is created
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ---------- Relationships ----------
    # "relationship" tells SQLAlchemy that one Job has MANY DiffRecords
    # This is called a "one-to-many" relationship
    # back_populates="job" → the DiffRecord model has a "job" attribute pointing back here
    diff_records = relationship("DiffRecord", back_populates="job", cascade="all, delete-orphan")
    generated_files = relationship("GeneratedFile", back_populates="job", cascade="all, delete-orphan")


# =============================================================================
# TABLE 2: DiffRecord
# =============================================================================
# A DiffRecord stores ONE field comparison for ONE company.
# Example: "For Abbvie Inc., the 'Return %' column differs:
#           child=0.0, parent=-0.6, is_different=True"
#
# One Job → Many DiffRecords (one per company per field)
# =============================================================================
class DiffRecord(Base):
    __tablename__ = "diff_records"

    id = Column(Integer, primary_key=True, index=True)

    # ForeignKey links this record to a specific Job
    # "jobs.id" means "the 'id' column of the 'jobs' table"
    # ondelete="CASCADE" means: if the Job is deleted, delete all its DiffRecords too
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    # Which company is this comparison for?
    company_name = Column(String(255), nullable=False)

    # What sector does this company belong to? (e.g., "Health care")
    sector = Column(String(255), nullable=True)

    # Stock ticker (e.g., "ABBV")
    exchange = Column(String(50), nullable=True)

    # Which field/column was compared?
    field_name = Column(String(100), nullable=False)  # e.g., "return_pct", "avg_weight"

    # The values in child and parent files
    child_value = Column(String(500), nullable=True)   # Store as string to handle any type
    parent_value = Column(String(500), nullable=True)

    # True if values differ, False if they match
    is_different = Column(Boolean, default=False)

    # How similar were the company names? (rapidfuzz score, 0-100)
    match_score = Column(Float, nullable=True)

    # Relationship back to the Job (many-to-one)
    job = relationship("Job", back_populates="diff_records")


# =============================================================================
# TABLE 3: GeneratedFile
# =============================================================================
# Tracks which Word files were generated for each job.
# One Job → Many GeneratedFiles (one per account/company section)
# =============================================================================
class GeneratedFile(Base):
    __tablename__ = "generated_files"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    # Name of the generated file (e.g., "Healthcare_Sector.docx")
    filename = Column(String(255), nullable=False)

    # The account/sector this file represents
    account_name = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="generated_files")
