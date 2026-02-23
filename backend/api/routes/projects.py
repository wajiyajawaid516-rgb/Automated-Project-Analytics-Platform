"""
Project Management API Routes.

Handles CRUD operations for construction projects.
Demonstrates:
    - RESTful endpoint design mapped to business actions
    - Defensive filtering and parameter validation
    - Soft deletes for production safety
    - Proper use of HTTP methods (GET, POST, PATCH, DELETE)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.models.database import get_db, Project, ProjectStatus, RIBAStage
from backend.api.models.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /projects — List all projects with optional filtering
# ---------------------------------------------------------------------------
@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(
    status: Optional[str] = Query(None, description="Filter by project status"),
    stage: Optional[str] = Query(None, description="Filter by current RIBA stage"),
    active_only: bool = Query(True, description="Only return active (non-deleted) projects"),
    db: Session = Depends(get_db),
):
    """
    Retrieve all projects with optional filtering.

    Design Decision:
        Default to active_only=True to prevent accidentally showing
        soft-deleted records in the UI. This is a production-safety
        pattern — deleted data stays in the database for audit purposes
        but is hidden from normal queries.
    """
    query = db.query(Project)

    if active_only:
        query = query.filter(Project.is_active == True)

    if status:
        try:
            status_enum = ProjectStatus(status)
            query = query.filter(Project.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid options: {[s.value for s in ProjectStatus]}"
            )

    if stage:
        try:
            stage_enum = RIBAStage(stage)
            query = query.filter(Project.current_stage == stage_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage '{stage}'. Valid options: {[s.value for s in RIBAStage]}"
            )

    return query.order_by(Project.job_number).all()


# ---------------------------------------------------------------------------
# GET /projects/{project_id} — Get a single project
# ---------------------------------------------------------------------------
@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Retrieve a single project by ID."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_active == True
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    return project


# ---------------------------------------------------------------------------
# POST /projects — Create a new project
# ---------------------------------------------------------------------------
@router.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new project.

    Design Decision:
        Check for duplicate job numbers before creating. Job numbers
        are business identifiers that must be unique — duplicates would
        cause confusion in reporting and time tracking.
    """
    # Check for duplicate job number
    existing = db.query(Project).filter(
        Project.job_number == project_data.job_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Project with job number '{project_data.job_number}' already exists"
        )

    project = Project(**project_data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


# ---------------------------------------------------------------------------
# PATCH /projects/{project_id} — Update a project
# ---------------------------------------------------------------------------
@router.patch("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    updates: ProjectUpdate,
    db: Session = Depends(get_db),
):
    """
    Update specific fields on an existing project.

    Design Decision:
        Using PATCH (not PUT) because we only update provided fields.
        This prevents accidentally nullifying fields that weren't
        included in the request — a common production bug.
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_active == True
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


# ---------------------------------------------------------------------------
# DELETE /projects/{project_id} — Soft delete a project
# ---------------------------------------------------------------------------
@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    Soft-delete a project (set is_active = False).

    Design Decision:
        NEVER hard-delete project data. Projects have linked time entries,
        directory entries, and potentially financial records. A hard delete
        would create orphaned records and break audit trails.

        Instead, we mark the project as inactive. It can be restored if
        the deletion was a mistake — this is standard in production systems.
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_active == True
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    project.is_active = False
    db.commit()

    return {"message": f"Project '{project.name}' (ID: {project_id}) has been archived"}
