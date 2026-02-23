"""
Time Entry & Analytics API Routes.

Handles time tracking data and computes performance analytics
including burn rates, risk detection, and executive summaries.

Demonstrates:
    - Business logic in the API layer (not the UI)
    - Computed metrics derived from relational data
    - Risk detection with configurable thresholds
    - Separation of raw data from computed insights
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.api.models.database import (
    get_db, TimeEntry, StageAllocation, Project, RIBAStage, ProjectStatus
)
from backend.api.models.schemas import (
    TimeEntryCreate, TimeEntryResponse,
    StageAllocationCreate, StageAllocationResponse,
    StageBurnRate, ProjectPerformance, PortfolioSummary,
)

router = APIRouter()

# Risk threshold — projects exceeding this percentage are flagged
RISK_THRESHOLD = 80.0  # percent


# ===========================================================================
# Time Entry Endpoints
# ===========================================================================

@router.get("/time-entries", response_model=List[TimeEntryResponse])
def list_time_entries(
    project_id: Optional[int] = Query(None, description="Filter by project"),
    stage: Optional[str] = Query(None, description="Filter by RIBA stage"),
    db: Session = Depends(get_db),
):
    """List time entries with optional filtering."""
    query = db.query(TimeEntry).filter(TimeEntry.is_active == True)

    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)

    if stage:
        query = query.filter(TimeEntry.stage == stage)

    return query.order_by(TimeEntry.logged_date.desc()).all()


@router.post("/time-entries", response_model=TimeEntryResponse, status_code=201)
def create_time_entry(entry_data: TimeEntryCreate, db: Session = Depends(get_db)):
    """
    Log time against a project and RIBA stage.

    Design Decision:
        Each time entry records the stage AT THE TIME OF LOGGING,
        not the project's current stage. This is critical for accurate
        historical analysis — if a project moves from Stage 3 to Stage 4,
        we need to know how much time was spent in Stage 3 specifically.
    """
    # Validate project exists
    project = db.query(Project).filter(
        Project.id == entry_data.project_id,
        Project.is_active == True
    ).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {entry_data.project_id} not found"
        )

    entry = TimeEntry(**entry_data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ===========================================================================
# Stage Allocation Endpoints
# ===========================================================================

@router.get(
    "/projects/{project_id}/allocations",
    response_model=List[StageAllocationResponse],
)
def get_stage_allocations(project_id: int, db: Session = Depends(get_db)):
    """Get all stage hour allocations for a project."""
    return db.query(StageAllocation).filter(
        StageAllocation.project_id == project_id,
        StageAllocation.is_active == True,
    ).all()


@router.post("/allocations", response_model=StageAllocationResponse, status_code=201)
def create_stage_allocation(
    allocation_data: StageAllocationCreate,
    db: Session = Depends(get_db),
):
    """
    Set allocated hours for a project stage.

    Design Decision:
        Stage allocations are separate from the Project model to allow
        per-stage budgeting. This mirrors how real firms budget —
        each RIBA stage has its own hour budget, and overruns in one
        stage don't automatically consume another stage's budget.
    """
    allocation = StageAllocation(**allocation_data.model_dump())
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


# ===========================================================================
# Analytics Endpoints (read-only, computed)
# ===========================================================================

@router.get(
    "/analytics/project/{project_id}",
    response_model=ProjectPerformance,
)
def get_project_performance(project_id: int, db: Session = Depends(get_db)):
    """
    Compute stage-level performance metrics for a single project.

    This endpoint transforms raw time entries and allocations into
    actionable insights: burn rates, risk flags, and remaining budgets.

    Design Decision:
        Calculations happen in the API, NOT in the frontend. This ensures:
        - Consistency: all consumers get the same numbers
        - Testability: analytics logic can be unit tested
        - Performance: database aggregation is faster than UI-side processing

    Risk Logic:
        - >= 80% burn rate → "At Risk" (gives managers time to act)
        - > 100% burn rate → "Overrun" (budget exceeded)
        The 80% threshold is chosen because catching overruns at 100%
        is too late — this is how real construction cost control works.
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_active == True
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Get allocations and time entries
    allocations = db.query(StageAllocation).filter(
        StageAllocation.project_id == project_id,
        StageAllocation.is_active == True,
    ).all()

    time_entries = db.query(TimeEntry).filter(
        TimeEntry.project_id == project_id,
        TimeEntry.is_active == True,
    ).all()

    # Build allocation lookup
    allocation_map = {a.stage: a.allocated_hours for a in allocations}

    # Aggregate time by stage
    time_by_stage = {}
    for entry in time_entries:
        stage_key = entry.stage
        time_by_stage[stage_key] = time_by_stage.get(stage_key, 0) + entry.hours

    # Compute burn rates per stage
    stage_details = []
    all_stages = set(list(allocation_map.keys()) + list(time_by_stage.keys()))

    for stage in sorted(all_stages, key=lambda s: s.value if hasattr(s, 'value') else str(s)):
        allocated = allocation_map.get(stage, 0)
        used = time_by_stage.get(stage, 0)
        remaining = allocated - used
        burn_pct = (used / allocated * 100) if allocated > 0 else 0

        stage_details.append(StageBurnRate(
            stage=stage.value if hasattr(stage, 'value') else str(stage),
            allocated_hours=allocated,
            used_hours=used,
            remaining_hours=remaining,
            burn_percentage=round(burn_pct, 1),
            is_at_risk=burn_pct >= RISK_THRESHOLD,
            is_overrun=burn_pct > 100,
        ))

    total_allocated = sum(s.allocated_hours for s in stage_details)
    total_used = sum(s.used_hours for s in stage_details)
    overall_burn = (total_used / total_allocated * 100) if total_allocated > 0 else 0

    return ProjectPerformance(
        project_id=project.id,
        job_number=project.job_number,
        project_name=project.name,
        current_stage=project.current_stage.value if hasattr(project.current_stage, 'value') else str(project.current_stage),
        status=project.status.value if hasattr(project.status, 'value') else str(project.status),
        total_allocated_hours=total_allocated,
        total_used_hours=total_used,
        overall_burn_percentage=round(overall_burn, 1),
        stages_at_risk=sum(1 for s in stage_details if s.is_at_risk),
        stages_overrun=sum(1 for s in stage_details if s.is_overrun),
        stage_details=stage_details,
    )


@router.get("/analytics/portfolio", response_model=PortfolioSummary)
def get_portfolio_summary(db: Session = Depends(get_db)):
    """
    Executive-level portfolio overview.

    Shows which projects are at risk across the entire portfolio.
    Designed for directors and senior managers who need to see
    the big picture without drilling into individual stages.

    Design Decision:
        This endpoint exists because the people who make resource
        allocation decisions (directors) don't want to click through
        5 projects individually. They want ONE view that says:
        "3 projects on track, 1 at risk, 1 overrun — here are the names."
    """
    projects = db.query(Project).filter(
        Project.is_active == True,
        Project.status == ProjectStatus.ACTIVE,
    ).all()

    at_risk_names = []
    overrun_names = []
    total_allocated = 0
    total_used = 0

    for project in projects:
        allocations = db.query(StageAllocation).filter(
            StageAllocation.project_id == project.id,
            StageAllocation.is_active == True,
        ).all()

        time_entries = db.query(TimeEntry).filter(
            TimeEntry.project_id == project.id,
            TimeEntry.is_active == True,
        ).all()

        proj_allocated = sum(a.allocated_hours for a in allocations)
        proj_used = sum(e.hours for e in time_entries)

        total_allocated += proj_allocated
        total_used += proj_used

        if proj_allocated > 0:
            burn = (proj_used / proj_allocated) * 100
            if burn > 100:
                overrun_names.append(project.name)
            elif burn >= RISK_THRESHOLD:
                at_risk_names.append(project.name)

    overall_utilisation = (total_used / total_allocated * 100) if total_allocated > 0 else 0

    return PortfolioSummary(
        total_projects=db.query(Project).filter(Project.is_active == True).count(),
        active_projects=len(projects),
        projects_at_risk=len(at_risk_names),
        projects_overrun=len(overrun_names),
        total_hours_allocated=total_allocated,
        total_hours_used=total_used,
        overall_utilisation=round(overall_utilisation, 1),
        at_risk_project_names=at_risk_names,
        overrun_project_names=overrun_names,
    )
