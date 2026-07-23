import io
import csv
from datetime import datetime
from typing import List
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.models.log import ActivityLog, AuditLog

def generate_activities_csv(activities: List[ActivityLog]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    # Write header
    writer.writerow(["ID", "User ID", "User Name", "Action", "Entity Type", "Entity ID", "Description", "Created At"])
    
    for act in activities:
        user_name = act.user.full_name or act.user.email if act.user else "System"
        writer.writerow([
            act.id,
            act.user_id or "",
            user_name,
            act.action,
            act.entity_type,
            act.entity_id,
            act.description or "",
            act.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    return output.getvalue()

def generate_activities_pdf(activities: List[ActivityLog]) -> bytes:
    buffer = io.BytesIO()
    # Landscape gives more horizontal room for logs
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(letter),
        rightMargin=36, 
        leftMargin=36,
        topMargin=36, 
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=15,
        textColor=colors.HexColor("#1A365D") # Navy blue
    )
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=9
    )
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=10,
        textColor=colors.whitesmoke,
        fontName='Helvetica-Bold'
    )
    
    story.append(Paragraph("Project Management System - Activity Log Export", title_style))
    story.append(Paragraph(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Table headers
    headers = [
        Paragraph("ID", header_style),
        Paragraph("User", header_style),
        Paragraph("Action", header_style),
        Paragraph("Entity", header_style),
        Paragraph("Entity ID", header_style),
        Paragraph("Description", header_style),
        Paragraph("Created At", header_style)
    ]
    data = [headers]
    
    for act in activities:
        user_str = act.user.full_name or act.user.email if act.user else f"User ID {act.user_id}" if act.user_id else "System"
        created_str = act.created_at.strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            Paragraph(str(act.id), cell_style),
            Paragraph(user_str, cell_style),
            Paragraph(act.action, cell_style),
            Paragraph(act.entity_type, cell_style),
            Paragraph(str(act.entity_id), cell_style),
            Paragraph(act.description or "", cell_style),
            Paragraph(created_str, cell_style)
        ]
        data.append(row)
        
    # Landscape Letter width is 792 pt. 792 - 72 (margins) = 720 printable width.
    # Distribute: ID (40), User (100), Action (120), Entity (70), Entity ID (50), Description (240), Created At (100)
    col_widths = [40, 100, 120, 70, 50, 240, 100]
    
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
        ('TOPPADDING', (0,1), (-1,-1), 4),
    ]))
    
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_audit_csv(audit_logs: List[AuditLog]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Entity Type", "Entity ID", "Field Name", "Old Value", "New Value", "Changed By", "Changed At"])
    
    for log in audit_logs:
        user_str = log.user.full_name or log.user.email if log.user else f"User ID {log.changed_by}" if log.changed_by else "System"
        writer.writerow([
            log.id,
            log.entity_type,
            log.entity_id,
            log.field_name,
            log.old_value or "",
            log.new_value or "",
            user_str,
            log.changed_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    return output.getvalue()


def generate_audit_pdf(audit_logs: List[AuditLog]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(letter),
        rightMargin=36, 
        leftMargin=36,
        topMargin=36, 
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=15,
        textColor=colors.HexColor("#0F766E") # Teal
    )
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=9
    )
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=10,
        textColor=colors.whitesmoke,
        fontName='Helvetica-Bold'
    )
    
    story.append(Paragraph("Project Management System - Audit Log Export", title_style))
    story.append(Paragraph(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", styles['Normal']))
    story.append(Spacer(1, 12))
    
    headers = [
        Paragraph("ID", header_style),
        Paragraph("Entity", header_style),
        Paragraph("Entity ID", header_style),
        Paragraph("Field Name", header_style),
        Paragraph("Old Value", header_style),
        Paragraph("New Value", header_style),
        Paragraph("Changed By", header_style),
        Paragraph("Changed At", header_style)
    ]
    data = [headers]
    
    for log in audit_logs:
        user_str = log.user.full_name or log.user.email if log.user else f"User ID {log.changed_by}" if log.changed_by else "System"
        changed_str = log.changed_at.strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            Paragraph(str(log.id), cell_style),
            Paragraph(log.entity_type, cell_style),
            Paragraph(str(log.entity_id), cell_style),
            Paragraph(log.field_name, cell_style),
            Paragraph(log.old_value or "", cell_style),
            Paragraph(log.new_value or "", cell_style),
            Paragraph(user_str, cell_style),
            Paragraph(changed_str, cell_style)
        ]
        data.append(row)
        
    # Printable area: 720 width.
    # Distribute: ID (40), Entity (70), Entity ID (50), Field Name (90), Old Value (140), New Value (140), Changed By (90), Changed At (100)
    col_widths = [40, 70, 50, 90, 140, 140, 90, 100]
    
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F766E")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F0FDFA")]),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
        ('TOPPADDING', (0,1), (-1,-1), 4),
    ]))
    
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
