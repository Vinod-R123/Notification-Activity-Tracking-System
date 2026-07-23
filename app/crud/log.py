from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.log import Notification, ActivityLog, AuditLog
from app.models.task import Task
from datetime import datetime
from typing import List, Optional

# --- Notification CRUD ---

def get_notifications(db: Session, user_id: int, unread_only: bool = False) -> List[Notification]:
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).all()

def mark_notification_read(db: Session, user_id: int, notification_id: int) -> Optional[Notification]:
    db_notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if db_notif:
        db_notif.is_read = True
        db.commit()
        db.refresh(db_notif)
    return db_notif

def mark_all_notifications_read(db: Session, user_id: int) -> int:
    result = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return result

def delete_notification(db: Session, user_id: int, notification_id: int) -> bool:
    db_notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if db_notif:
        db.delete(db_notif)
        db.commit()
        return True
    return False


# --- Activity Log CRUD ---

def get_activities(
    db: Session,
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    action_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[ActivityLog]:
    query = db.query(ActivityLog)

    if user_id is not None:
        query = query.filter(ActivityLog.user_id == user_id)

    if project_id is not None:
        # Get tasks in project to include task-related activities of that project
        subquery_task_ids = db.query(Task.id).filter(Task.project_id == project_id).all()
        task_ids = [t[0] for t in subquery_task_ids]
        query = query.filter(
            or_(
                and_(ActivityLog.entity_type == "Project", ActivityLog.entity_id == project_id),
                and_(ActivityLog.entity_type == "Task", ActivityLog.entity_id.in_(task_ids))
            )
        )

    if start_date is not None:
        query = query.filter(ActivityLog.created_at >= start_date)

    if end_date is not None:
        query = query.filter(ActivityLog.created_at <= end_date)

    if action_type is not None:
        query = query.filter(ActivityLog.action == action_type)

    return query.order_by(ActivityLog.created_at.desc()).offset(skip).limit(limit).all()


# --- Audit Log CRUD ---

def get_audit_logs(
    db: Session,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[AuditLog]:
    query = db.query(AuditLog)

    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.filter(AuditLog.entity_id == entity_id)

    return query.order_by(AuditLog.changed_at.desc()).offset(skip).limit(limit).all()
