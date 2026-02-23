"""
Contact & Organisation API Routes.

Manages stakeholder information independently of projects.
Contacts are linked to projects via the ProjectDirectory junction table,
not duplicated per project.

Demonstrates:
    - Separation of concerns (contacts exist independently)
    - Global vs project-level data management
    - Idempotent operations (prevents duplicates)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.models.database import get_db, Organisation, Contact
from backend.api.models.schemas import (
    OrganisationCreate, OrganisationUpdate, OrganisationResponse,
    ContactCreate, ContactUpdate, ContactResponse,
)

router = APIRouter()


# ===========================================================================
# Organisation Endpoints
# ===========================================================================

@router.get("/organisations", response_model=List[OrganisationResponse])
def list_organisations(
    search: Optional[str] = Query(None, description="Search by organisation name"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """List all organisations with optional name search."""
    query = db.query(Organisation)

    if active_only:
        query = query.filter(Organisation.is_active == True)

    if search:
        query = query.filter(Organisation.name.ilike(f"%{search}%"))

    return query.order_by(Organisation.name).all()


@router.get("/organisations/{org_id}", response_model=OrganisationResponse)
def get_organisation(org_id: int, db: Session = Depends(get_db)):
    """Retrieve a single organisation by ID."""
    org = db.query(Organisation).filter(
        Organisation.id == org_id,
        Organisation.is_active == True
    ).first()

    if not org:
        raise HTTPException(status_code=404, detail=f"Organisation with ID {org_id} not found")
    return org


@router.post("/organisations", response_model=OrganisationResponse, status_code=201)
def create_organisation(org_data: OrganisationCreate, db: Session = Depends(get_db)):
    """
    Create a new organisation.

    Design Decision:
        We check for duplicate names (case-insensitive) to prevent
        the same company from being entered multiple times with
        slightly different formatting (e.g., "Acme Ltd" vs "ACME LTD").
    """
    existing = db.query(Organisation).filter(
        Organisation.name.ilike(org_data.name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Organisation '{org_data.name}' already exists (ID: {existing.id})"
        )

    org = Organisation(**org_data.model_dump())
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.patch("/organisations/{org_id}", response_model=OrganisationResponse)
def update_organisation(
    org_id: int,
    updates: OrganisationUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing organisation.

    Design Decision:
        Updates to organisation details (e.g., phone number, address)
        automatically propagate to all projects where this organisation
        appears, because projects reference the organisation by ID,
        not by copied data. This is the power of relational modelling.
    """
    org = db.query(Organisation).filter(
        Organisation.id == org_id,
        Organisation.is_active == True
    ).first()

    if not org:
        raise HTTPException(status_code=404, detail=f"Organisation with ID {org_id} not found")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)

    db.commit()
    db.refresh(org)
    return org


@router.delete("/organisations/{org_id}")
def delete_organisation(org_id: int, db: Session = Depends(get_db)):
    """Soft-delete an organisation."""
    org = db.query(Organisation).filter(
        Organisation.id == org_id,
        Organisation.is_active == True
    ).first()

    if not org:
        raise HTTPException(status_code=404, detail=f"Organisation with ID {org_id} not found")

    org.is_active = False
    db.commit()
    return {"message": f"Organisation '{org.name}' has been archived"}


# ===========================================================================
# Contact Endpoints
# ===========================================================================

@router.get("/contacts", response_model=List[ContactResponse])
def list_contacts(
    search: Optional[str] = Query(None, description="Search by name or email"),
    organisation_id: Optional[int] = Query(None, description="Filter by organisation"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    List all contacts with optional filtering.

    Design Decision:
        Contacts are queried independently of projects. This means
        the contacts list shows ALL contacts in the system, not just
        those assigned to a specific project. Project-specific views
        are handled by the /directory endpoints.
    """
    query = db.query(Contact)

    if active_only:
        query = query.filter(Contact.is_active == True)

    if organisation_id:
        query = query.filter(Contact.organisation_id == organisation_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Contact.first_name.ilike(search_term)) |
            (Contact.last_name.ilike(search_term)) |
            (Contact.email.ilike(search_term))
        )

    return query.order_by(Contact.last_name, Contact.first_name).all()


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """Retrieve a single contact by ID."""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.is_active == True
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail=f"Contact with ID {contact_id} not found")
    return contact


@router.post("/contacts", response_model=ContactResponse, status_code=201)
def create_contact(contact_data: ContactCreate, db: Session = Depends(get_db)):
    """
    Create a new contact.

    Design Decision:
        If organisation_id is provided, we validate that the organisation
        exists before creating the contact. This prevents orphaned
        references — a common data integrity issue in systems that
        don't validate foreign keys at the API level.
    """
    if contact_data.organisation_id:
        org = db.query(Organisation).filter(
            Organisation.id == contact_data.organisation_id,
            Organisation.is_active == True
        ).first()
        if not org:
            raise HTTPException(
                status_code=404,
                detail=f"Organisation with ID {contact_data.organisation_id} not found"
            )

    contact = Contact(**contact_data.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.patch("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    updates: ContactUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing contact.

    Design Decision:
        Like organisations, contact updates are global. Changing a
        contact's phone number here updates it across all projects
        they're assigned to. This eliminates the "stale data" problem
        where one project has an old phone number and another has the new one.
    """
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.is_active == True
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail=f"Contact with ID {contact_id} not found")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    """Soft-delete a contact."""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.is_active == True
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail=f"Contact with ID {contact_id} not found")

    contact.is_active = False
    db.commit()
    return {"message": f"Contact '{contact.first_name} {contact.last_name}' has been archived"}
