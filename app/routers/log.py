from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.dependencies import get_db, get_current_user
from app.crud.log import (
    get_notifications, mark_notification_read, mark_all_notifications_read,
    delete_notification, get_activities, get_audit_logs
)
from app.crud.project import is_project_member
from app.schemas.log import NotificationOut, ActivityLogOut, AuditLogOut
from app.models.user import User
from app.services.export import (
    generate_activities_csv, generate_activities_pdf,
    generate_audit_csv, generate_audit_pdf
)

# Root-level router for logs, activities and audits
router = APIRouter(tags=["Logs & Notifications"])

# --- Notifications Endpoints ---

@router.get("/notifications", response_model=List[NotificationOut])
def read_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_notifications(db, user_id=current_user.id, unread_only=False)

@router.get("/notifications/unread", response_model=List[NotificationOut])
def read_unread_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_notifications(db, user_id=current_user.id, unread_only=True)

@router.put("/notifications/{id}/read", response_model=NotificationOut)
def read_notification(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notif = mark_notification_read(db, user_id=current_user.id, notification_id=id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif

@router.put("/notifications/read-all", status_code=status.HTTP_200_OK)
def read_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = mark_all_notifications_read(db, user_id=current_user.id)
    return {"message": f"Marked {count} notifications as read"}

@router.delete("/notifications/{id}", status_code=status.HTTP_200_OK)
def delete_user_notification(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    deleted = delete_notification(db, user_id=current_user.id, notification_id=id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted successfully"}


# --- Activity Log Endpoints ---

@router.get("/activities", response_model=List[ActivityLogOut])
def read_activities(
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    action_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Authorization checks: if project_id is filtered, user must be a member
    if project_id and not is_project_member(db, project_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access logs for this project")
    return get_activities(
        db, user_id=user_id, project_id=project_id,
        start_date=start_date, end_date=end_date, action_type=action_type,
        skip=skip, limit=limit
    )

@router.get("/activities/user/{id}", response_model=List[ActivityLogOut])
def read_user_activities(
    id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    action_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # View user logs - optionally restrict to self or admins, but here open for logged in members
    return get_activities(
        db, user_id=id, start_date=start_date, end_date=end_date,
        action_type=action_type, skip=skip, limit=limit
    )

@router.get("/activities/project/{id}", response_model=List[ActivityLogOut])
def read_project_activities(
    id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    action_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not is_project_member(db, id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access logs for this project")
    return get_activities(
        db, project_id=id, start_date=start_date, end_date=end_date,
        action_type=action_type, skip=skip, limit=limit
    )


# --- Audit Log Endpoints ---

@router.get("/audit-logs", response_model=List[AuditLogOut])
def read_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Audit log lists (usually admin or project leads, accessible to authenticated users here)
    return get_audit_logs(db, entity_type=entity_type, entity_id=entity_id, skip=skip, limit=limit)

@router.get("/audit-logs/{entity_type}/{entity_id}", response_model=List[AuditLogOut])
def read_specific_audit_logs(
    entity_type: str,
    entity_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_audit_logs(db, entity_type=entity_type, entity_id=entity_id, skip=skip, limit=limit)


# --- Export Endpoints ---

@router.get("/activities/export")
def export_activities(
    format: str = "csv",  # csv or pdf
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    action_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if project_id and not is_project_member(db, project_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to export logs for this project")

    activities = get_activities(
        db, user_id=user_id, project_id=project_id,
        start_date=start_date, end_date=end_date, action_type=action_type,
        skip=0, limit=1000
    )

    if format.lower() == "csv":
        csv_data = generate_activities_csv(activities)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=activities_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"}
        )
    elif format.lower() == "pdf":
        pdf_bytes = generate_activities_pdf(activities)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=activities_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"}
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Specify 'csv' or 'pdf'.")
