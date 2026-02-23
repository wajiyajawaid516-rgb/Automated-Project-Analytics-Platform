"""
Document Automation Service.

Provides programmatic PDF and Word document generation
for professional business reporting.
"""

import io
from datetime import datetime
from typing import List, Dict, Optional


def generate_directory_pdf(
    project_name: str,
    job_number: str,
    directory_entries: List[Dict],
) -> bytes:
    """
    Generate a branded PDF of a project's stakeholder directory.

    Returns PDF as bytes for streaming via API response.
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph(f"Project Directory — {project_name}", styles['Heading1']))
    elements.append(Paragraph(f"Job Number: {job_number} | Generated: {datetime.now().strftime('%d %B %Y')}", styles['Normal']))
    elements.append(Spacer(1, 10*mm))

    # Table data
    headers = ["Name", "Organisation", "Role", "Email", "Phone"]
    table_data = [headers]
    for entry in directory_entries:
        table_data.append([
            entry.get("name", ""),
            entry.get("organisation", ""),
            entry.get("role", ""),
            entry.get("email", ""),
            entry.get("phone", ""),
        ])

    table = Table(table_data, colWidths=[120, 140, 100, 160, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.4)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
    ]))
    elements.append(table)

    doc.build(elements)
    return buffer.getvalue()
