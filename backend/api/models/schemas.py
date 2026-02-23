"""
Pydantic schemas for request/response validation.

Design Decision:
    Using Pydantic models for strict input validation and clear API contracts.
    This ensures the API rejects malformed data BEFORE it reaches the database,
    which is a production-safety pattern used in enterprise systems.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


# ---------------------------------------------------------------------------
# Organisation Schemas
# ---------------------------------------------------------------------------
class OrganisationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Organisation name")
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    country: str = "United Kingdom"
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class OrganisationCreate(OrganisationBase):
    """Schema for creating a new organisation."""
    pass


class OrganisationUpdate(BaseModel):
    """Schema for updating an organisation. All fields optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class OrganisationResponse(OrganisationBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Contact Schemas
# ---------------------------------------------------------------------------
class ContactBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    organisation_id: Optional[int] = None


class ContactCreate(ContactBase):
    """Schema for creating a new contact."""
    pass


class ContactUpdate(BaseModel):
    """Schema for updating a contact. All fields optional."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    organisation_id: Optional[int] = None


class ContactResponse(ContactBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    organisation: Optional[OrganisationResponse] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Project Schemas
# ---------------------------------------------------------------------------
class ProjectBase(BaseModel):
    job_number: str = Field(..., min_length=1, max_length=50, description="Unique job identifier")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    client_organisation_id: Optional[int] = None
    current_stage: str = "0 - Strategic Definition"
    status: str = "Active"
    start_date: Optional[datetime] = None
    target_completion: Optional[datetime] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project. All fields optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    client_organisation_id: Optional[int] = None
    current_stage: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    target_completion: Optional[datetime] = None


class ProjectResponse(ProjectBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Project Directory Schemas
# ---------------------------------------------------------------------------
class DirectoryEntryBase(BaseModel):
    project_id: int
    contact_id: int
    role: str = "Other"
    notes: Optional[str] = None


class DirectoryEntryCreate(DirectoryEntryBase):
    """
    Schema for adding a contact to a project directory.

    Design Decision:
        The create operation checks for existing entries to prevent
        duplicates (idempotent). A contact should only appear once
        per project with a given role.
    """
    pass


class DirectoryEntryResponse(DirectoryEntryBase):
    id: int
    is_active: bool
    added_at: datetime
    contact: Optional[ContactResponse] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Stage Allocation Schemas
# ---------------------------------------------------------------------------
class StageAllocationBase(BaseModel):
    project_id: int
    stage: str
    allocated_hours: float = Field(..., ge=0, description="Hours budgeted for this stage")


class StageAllocationCreate(StageAllocationBase):
    pass


class StageAllocationResponse(StageAllocationBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Time Entry Schemas
# ---------------------------------------------------------------------------
class TimeEntryBase(BaseModel):
    project_id: int
    stage: str
    hours: float = Field(..., gt=0, description="Hours worked (must be positive)")
    description: Optional[str] = None
    logged_by: Optional[str] = None


class TimeEntryCreate(TimeEntryBase):
    pass


class TimeEntryResponse(TimeEntryBase):
    id: int
    is_active: bool
    logged_date: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Analytics Schemas (read-only, computed)
# ---------------------------------------------------------------------------
class StageBurnRate(BaseModel):
    """Computed metric: how much of a stage's budget has been consumed."""
    stage: str
    allocated_hours: float
    used_hours: float
    remaining_hours: float
    burn_percentage: float = Field(..., description="Percentage of allocated hours used")
    is_at_risk: bool = Field(..., description="True if burn rate >= 80%")
    is_overrun: bool = Field(..., description="True if burn rate > 100%")


class ProjectPerformance(BaseModel):
    """Aggregated performance metrics for a single project."""
    project_id: int
    job_number: str
    project_name: str
    current_stage: str
    status: str
    total_allocated_hours: float
    total_used_hours: float
    overall_burn_percentage: float
    stages_at_risk: int
    stages_overrun: int
    stage_details: List[StageBurnRate]


class PortfolioSummary(BaseModel):
    """Executive-level overview across all projects."""
    total_projects: int
    active_projects: int
    projects_at_risk: int
    projects_overrun: int
    total_hours_allocated: float
    total_hours_used: float
    overall_utilisation: float
    at_risk_project_names: List[str]
    overrun_project_names: List[str]
