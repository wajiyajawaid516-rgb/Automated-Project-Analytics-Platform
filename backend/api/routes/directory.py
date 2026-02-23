"""
Project Directory API Routes.

Manages the relationship between Projects and Contacts.
This is the junction layer — it answers "who is involved in which project?"

Demonstrates:
    - Many-to-many relationship management via junction table
    - Idempotent operations (adding the same contact twice is safely handled)
    - Separation of global contacts from project-specific roles
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.models.database import (
    get_db, ProjectDirectory, Project, Contact
)
from backend.api.models.schemas import DirectoryEntryCreate, DirectoryEntryResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/directory — List all contacts for a project
# ---------------------------------------------------------------------------
@router.get(
    "/projects/{project_id}/directory",
    response_model=List[DirectoryEntryResponse],
)
def get_project_directory(
    project_id: int,
    role: Optional[str] = Query(None, description="Filter by role"),
    db: Session = Depends(get_db),
):
    """
    Retrieve all contacts assigned to a specific project.

    Design Decision:
        This endpoint returns directory entries (which include role
        and notes) along with the full contact details. This means
        the frontend gets everything it needs in a single API call,
        rather than making separate requests for contacts and roles.

    Real-world lesson learned:
        Initially, we filtered using the wrong comparison operator
        (equivalent to 'link_row_contains' instead of 'link_row_has'),
        which caused contacts from other projects to appear.
        The fix was to use exact matching on project_id.
    """
    # Validate project exists
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_active == True
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    query = db.query(ProjectDirectory).filter(
        ProjectDirectory.project_id == project_id,
        ProjectDirectory.is_active == True,
    )

    if role:
        query = query.filter(ProjectDirectory.role == role)

    return query.all()


# ---------------------------------------------------------------------------
# POST /projects/{project_id}/directory — Add contact to project
# ---------------------------------------------------------------------------
@router.post(
    "/projects/{project_id}/directory",
    response_model=DirectoryEntryResponse,
    status_code=201,
)
def add_contact_to_project(
    project_id: int,
    entry_data: DirectoryEntryCreate,
    db: Session = Depends(get_db),
):
    """
    Add a contact to a project's directory with a specific role.

    Design Decision (Idempotency):
        Before creating a new entry, we check if this contact already
        exists in this project's directory with the same role. If so,
        we return the existing entry rather than creating a duplicate.

        This prevents:
        - Double-clicking the "Add" button from creating duplicates
        - Re-running data imports from creating duplicates
        - Race conditions in multi-user environments

        This is a critical pattern in production systems where data
        integrity matters more than strict REST semantics.
    """
    # Validate project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_active == True
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    # Validate contact
    contact = db.query(Contact).filter(
        Contact.id == entry_data.contact_id,
        Contact.is_active == True
    ).first()
    if not contact:
        raise HTTPException(
            status_code=404,
            detail=f"Contact with ID {entry_data.contact_id} not found"
        )

    # Idempotency check — prevent duplicates
    existing = db.query(ProjectDirectory).filter(
        ProjectDirectory.project_id == project_id,
        ProjectDirectory.contact_id == entry_data.contact_id,
        ProjectDirectory.role == entry_data.role,
        ProjectDirectory.is_active == True,
    ).first()

    if existing:
        return existing  # Return existing entry instead of creating duplicate

    # Create new directory entry
    entry = ProjectDirectory(
        project_id=project_id,
        contact_id=entry_data.contact_id,
        role=entry_data.role,
        notes=entry_data.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ---------------------------------------------------------------------------
# DELETE /projects/{project_id}/directory/{entry_id} — Remove from project
# ---------------------------------------------------------------------------
@router.delete("/projects/{project_id}/directory/{entry_id}")
def remove_contact_from_project(
    project_id: int,
    entry_id: int,
    db: Session = Depends(get_db),
):
    """
    Remove a contact from a project's directory (soft delete).

    Design Decision:
        Removing a contact from a project directory does NOT delete
        the contact themselves. It only removes the link. The contact
        remains available to be added to other projects.

        This is because contacts are a global resource, not owned
        by any single project.
    """
    entry = db.query(ProjectDirectory).filter(
        ProjectDirectory.id == entry_id,
        ProjectDirectory.project_id == project_id,
        ProjectDirectory.is_active == True,
    ).first()

    if not entry:
        raise HTTPException(
            status_code=404,
            detail=f"Directory entry {entry_id} not found in project {project_id}"
        )

    entry.is_active = False
    db.commit()
    return {"message": "Contact removed from project directory"}


# ---------------------------------------------------------------------------
# GET /contacts/{contact_id}/projects — Find all projects for a contact
# ---------------------------------------------------------------------------
@router.get("/contacts/{contact_id}/projects")
def get_contact_projects(contact_id: int, db: Session = Depends(get_db)):
    """
    Find all projects a specific contact is involved in.

    This is the reverse lookup — useful for answering questions like:
    "What projects is David Patel working on?"

    Design Decision:
        This query is efficient because of the junction table design.
        We don't need to scan all projects — we just query the
        ProjectDirectory table filtered by contact_id.
    """
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.is_active == True
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail=f"Contact with ID {contact_id} not found")

    entries = db.query(ProjectDirectory).filter(
        ProjectDirectory.contact_id == contact_id,
        ProjectDirectory.is_active == True,
    ).all()

    return {
        "contact": f"{contact.first_name} {contact.last_name}",
        "projects": [
            {
                "project_id": e.project_id,
                "project_name": e.project.name if e.project else "Unknown",
                "job_number": e.project.job_number if e.project else "Unknown",
                "role": e.role.value if hasattr(e.role, 'value') else e.role,
            }
            for e in entries
        ],
    }
