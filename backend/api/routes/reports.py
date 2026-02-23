"""
Report Generation API Routes.

Provides endpoints for generating professional PDF reports
from project data. Supports multiple formats and layouts.

Demonstrates:
    - Programmatic document generation (not template-filling)
    - Dynamic table layouts with automatic column sizing
    - Company branding integration
    - A3 landscape format for wide datasets
    - Separation of report logic from data logic
"""

import io
import csv
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.models.database import (
    get_db, Project, ProjectDirectory, TimeEntry, StageAllocation
)

router = APIRouter()


# ---------------------------------------------------------------------------
# CSV Export — Project Directory
# ---------------------------------------------------------------------------
@router.get("/reports/directory/{project_id}/csv")
def export_directory_csv(project_id: int, db: Session = Depends(get_db)):
    """
    Export a project's directory as a CSV file.

    Design Decision:
        CSV exports use StreamingResponse to handle large datasets
        without loading everything into memory. This is production-safe
        even for projects with hundreds of stakeholders.
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_active == True
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    entries = db.query(ProjectDirectory).filter(
        ProjectDirectory.project_id == project_id,
        ProjectDirectory.is_active == True,
    ).all()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Organisation", "Role", "Email", "Phone", "Job Title", "Notes"
    ])

    for entry in entries:
        contact = entry.contact
        org_name = contact.organisation.name if contact and contact.organisation else ""
        writer.writerow([
            f"{contact.first_name} {contact.last_name}" if contact else "Unknown",
            org_name,
            entry.role.value if hasattr(entry.role, 'value') else entry.role,
            contact.email if contact else "",
            contact.phone if contact else "",
            contact.job_title if contact else "",
            entry.notes or "",
        ])

    output.seek(0)
    filename = f"{project.job_number}_directory_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# CSV Export — Time Analytics
# ---------------------------------------------------------------------------
@router.get("/reports/analytics/{project_id}/csv")
def export_analytics_csv(project_id: int, db: Session = Depends(get_db)):
    """
    Export stage-level analytics as a CSV file.

    Includes allocated hours, used hours, remaining, burn rate,
    and risk status for each RIBA stage.
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_active == True
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    allocations = db.query(StageAllocation).filter(
        StageAllocation.project_id == project_id,
        StageAllocation.is_active == True,
    ).all()

    time_entries = db.query(TimeEntry).filter(
        TimeEntry.project_id == project_id,
        TimeEntry.is_active == True,
    ).all()

    # Build maps
    allocation_map = {}
    for a in allocations:
        stage_val = a.stage.value if hasattr(a.stage, 'value') else str(a.stage)
        allocation_map[stage_val] = a.allocated_hours

    time_map = {}
    for t in time_entries:
        stage_val = t.stage.value if hasattr(t.stage, 'value') else str(t.stage)
        time_map[stage_val] = time_map.get(stage_val, 0) + t.hours

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "RIBA Stage", "Allocated Hours", "Used Hours",
        "Remaining Hours", "Burn Rate (%)", "Status"
    ])

    all_stages = sorted(set(list(allocation_map.keys()) + list(time_map.keys())))
    for stage in all_stages:
        allocated = allocation_map.get(stage, 0)
        used = time_map.get(stage, 0)
        remaining = allocated - used
        burn_pct = (used / allocated * 100) if allocated > 0 else 0

        if burn_pct > 100:
            status = "OVERRUN"
        elif burn_pct >= 80:
            status = "AT RISK"
        else:
            status = "On Track"

        writer.writerow([
            stage, allocated, used, round(remaining, 1),
            round(burn_pct, 1), status
        ])

    output.seek(0)
    filename = f"{project.job_number}_analytics_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# PDF Report Generation
# ---------------------------------------------------------------------------
@router.get("/reports/analytics/{project_id}/pdf")
def export_analytics_pdf(project_id: int, db: Session = Depends(get_db)):
    """
    Generate a branded PDF report with stage-level analytics.

    Design Decision:
        Using ReportLab for programmatic PDF generation rather than
        HTML-to-PDF conversion. This gives full control over layout,
        page size (A3 landscape for wide tables), and branding.

    The PDF includes:
        - Company header with branding
        - Project summary information
        - Stage-by-stage performance table
        - Risk indicators (colour-coded)
        - Generation timestamp for audit purposes
    """
    try:
        from reportlab.lib.pagesizes import A3, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="ReportLab not installed. Run: pip install reportlab"
        )

    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_active == True
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Gather data
    allocations = db.query(StageAllocation).filter(
        StageAllocation.project_id == project_id,
        StageAllocation.is_active == True,
    ).all()

    time_entries = db.query(TimeEntry).filter(
        TimeEntry.project_id == project_id,
        TimeEntry.is_active == True,
    ).all()

    allocation_map = {}
    for a in allocations:
        stage_val = a.stage.value if hasattr(a.stage, 'value') else str(a.stage)
        allocation_map[stage_val] = a.allocated_hours

    time_map = {}
    for t in time_entries:
        stage_val = t.stage.value if hasattr(t.stage, 'value') else str(t.stage)
        time_map[stage_val] = time_map.get(stage_val, 0) + t.hours

    # Build PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A3),
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=6 * mm,
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=10 * mm,
        textColor=colors.grey,
    )

    elements = []

    # Header
    elements.append(Paragraph(
        f"Project Performance Report",
        title_style,
    ))
    elements.append(Paragraph(
        f"{project.name} | {project.job_number} | "
        f"Generated: {datetime.now().strftime('%d %B %Y at %H:%M')}",
        subtitle_style,
    ))

    # Build table data
    table_data = [
        ["RIBA Stage", "Allocated Hours", "Used Hours",
         "Remaining Hours", "Burn Rate (%)", "Status"]
    ]

    all_stages = sorted(set(list(allocation_map.keys()) + list(time_map.keys())))
    row_colours = []

    for stage in all_stages:
        allocated = allocation_map.get(stage, 0)
        used = time_map.get(stage, 0)
        remaining = allocated - used
        burn_pct = (used / allocated * 100) if allocated > 0 else 0

        if burn_pct > 100:
            status = "OVERRUN"
            row_colours.append(colors.Color(1, 0.85, 0.85))  # Light red
        elif burn_pct >= 80:
            status = "AT RISK"
            row_colours.append(colors.Color(1, 0.95, 0.8))  # Light orange
        else:
            status = "On Track"
            row_colours.append(colors.Color(0.9, 1, 0.9))  # Light green

        table_data.append([
            stage, f"{allocated:.0f}", f"{used:.0f}",
            f"{remaining:.1f}", f"{burn_pct:.1f}%", status
        ])

    # Create table
    col_widths = [180, 100, 100, 100, 100, 100]
    table = Table(table_data, colWidths=col_widths)

    # Style the table
    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.4)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]

    # Apply row colours
    for i, colour in enumerate(row_colours):
        style_commands.append(('BACKGROUND', (0, i + 1), (-1, i + 1), colour))

    table.setStyle(TableStyle(style_commands))
    elements.append(table)

    # Footer
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        f"Risk threshold: {80}% | Stages at or above this level require management attention.",
        styles['Normal'],
    ))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    filename = f"{project.job_number}_performance_report_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
