import logging
import os
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.config import settings
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.log import ActivityLog, AuditLog, Notification
from app.services.websocket import manager

logger = logging.getLogger("event_system")

# Mock email helper
def send_mock_email(to_email: str, subject: str, body: str):
    email_content = f"""
================================================================================
DATE: {datetime.utcnow().isoformat()}
TO: {to_email}
SUBJECT: {subject}
BODY: 
{body}
================================================================================
"""
    logger.info(f"Mock email sent to {to_email}: {subject}")
    try:
        with open(settings.EMAIL_MOCK_FILE, "a", encoding="utf-8") as f:
            f.write(email_content)
    except Exception as e:
        logger.error(f"Failed to write mock email to file: {e}")

async def create_notification_and_notify(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    preference_key: str,
    trigger_email: bool = False,
    email_subject: str = "",
    email_body: str = ""
):
    # Check user preferences
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
    
    prefs = user.notification_preferences or {}
    if not prefs.get(preference_key, True):
        logger.info(f"Skipping notification for User {user_id} due to preferences for key '{preference_key}'")
        return

    # Write to database
    db_notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        is_read=False
    )
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)

    # Real-time WebSocket notify
    websocket_payload = {
        "event": "notification",
        "id": db_notif.id,
        "title": db_notif.title,
        "message": db_notif.message,
        "created_at": db_notif.created_at.isoformat(),
        "is_read": db_notif.is_read
    }
    await manager.send_personal_message(websocket_payload, user_id)

    # Email notification (mocked)
    if trigger_email and user.email:
        send_mock_email(
            to_email=user.email,
            subject=email_subject or title,
            body=email_body or message
        )


async def handle_event(event_type: str, payload: Dict[str, Any]):
    db = SessionLocal()
    try:
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first() if user_id else None
        username = user.full_name or user.email if user else "System"

        if event_type == "USER_LOGIN":
            # Activity Log
            activity = ActivityLog(
                user_id=user_id,
                action="User Login",
                entity_type="User",
                entity_id=user_id,
                description=f"User {username} logged in."
            )
            db.add(activity)
            db.commit()

        elif event_type == "USER_LOGOUT":
            # Activity Log
            activity = ActivityLog(
                user_id=user_id,
                action="User Logout",
                entity_type="User",
                entity_id=user_id,
                description=f"User {username} logged out."
            )
            db.add(activity)
            db.commit()

        elif event_type == "PROJECT_CREATED":
            project_id = payload["project_id"]
            proj_title = payload["title"]
            activity = ActivityLog(
                user_id=user_id,
                action="Project Creation",
                entity_type="Project",
                entity_id=project_id,
                description=f"Project '{proj_title}' created by {username}."
            )
            db.add(activity)
            db.commit()

        elif event_type == "PROJECT_UPDATED":
            project_id = payload["project_id"]
            proj_title = payload["title"]
            old_values = payload.get("old_values", {})
            new_values = payload.get("new_values", {})

            # Log Activity
            activity = ActivityLog(
                user_id=user_id,
                action="Project Update",
                entity_type="Project",
                entity_id=project_id,
                description=f"Project '{proj_title}' was updated by {username}."
            )
            db.add(activity)

            # Audit Trail
            for field, old_val in old_values.items():
                new_val = new_values.get(field)
                audit = AuditLog(
                    entity_type="Project",
                    entity_id=project_id,
                    field_name=field,
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val) if new_val is not None else None,
                    changed_by=user_id,
                )
                db.add(audit)
            db.commit()

            # Notify Members
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                for member in project.members:
                    if member.id != user_id:
                        await create_notification_and_notify(
                            db=db,
                            user_id=member.id,
                            title="Project Updated",
                            message=f"The project '{proj_title}' has been updated by {username}.",
                            preference_key="project_updated"
                        )

        elif event_type == "PROJECT_DELETED":
            project_id = payload["project_id"]
            proj_title = payload["title"]
            activity = ActivityLog(
                user_id=user_id,
                action="Project Deletion",
                entity_type="Project",
                entity_id=project_id,
                description=f"Project '{proj_title}' was deleted by {username}."
            )
            db.add(activity)
            db.commit()

        elif event_type == "MEMBER_ADDED":
            project_id = payload["project_id"]
            member_id = payload["member_id"]
            
            project = db.query(Project).filter(Project.id == project_id).first()
            new_member = db.query(User).filter(User.id == member_id).first()
            
            if project and new_member:
                member_name = new_member.full_name or new_member.email
                # Log Activity
                activity = ActivityLog(
                    user_id=user_id,
                    action="Member Added to Project",
                    entity_type="Project",
                    entity_id=project_id,
                    description=f"Member '{member_name}' added to project '{project.title}' by {username}."
                )
                db.add(activity)

                # Log Audit
                audit = AuditLog(
                    entity_type="Project",
                    entity_id=project_id,
                    field_name="member_added",
                    old_value=None,
                    new_value=member_name,
                    changed_by=user_id
                )
                db.add(audit)
                db.commit()

                # Notify User (Project Invitation)
                await create_notification_and_notify(
                    db=db,
                    user_id=member_id,
                    title="Project Invitation",
                    message=f"You have been added as a member to the project '{project.title}' by {username}.",
                    preference_key="new_project_member_added",
                    trigger_email=True,
                    email_subject=f"Project Invitation: {project.title}",
                    email_body=f"Hi {member_name},\n\nYou have been added as a member to the project '{project.title}' by {username}."
                )

        elif event_type == "TASK_CREATED":
            task_id = payload["task_id"]
            task_title = payload["title"]
            proj_id = payload["project_id"]
            
            activity = ActivityLog(
                user_id=user_id,
                action="Task Creation",
                entity_type="Task",
                entity_id=task_id,
                description=f"Task '{task_title}' created by {username}."
            )
            db.add(activity)
            db.commit()

            # If task was created with an assignee, let's trigger a task assigned event too!
            task = db.query(Task).filter(Task.id == task_id).first()
            if task and task.assignee_id:
                # Trigger task assignment notification
                assignee = db.query(User).filter(User.id == task.assignee_id).first()
                if assignee:
                    assignee_name = assignee.full_name or assignee.email
                    await create_notification_and_notify(
                        db=db,
                        user_id=task.assignee_id,
                        title="Task Assigned",
                        message=f"You have been assigned to the task '{task.title}' by {username}.",
                        preference_key="task_assigned",
                        trigger_email=True,
                        email_subject=f"New Task Assigned: {task.title}",
                        email_body=f"Hi {assignee_name},\n\nYou have been assigned to the task '{task.title}' in the project by {username}."
                    )

        elif event_type == "TASK_UPDATED":
            task_id = payload["task_id"]
            task_title = payload["title"]
            old_values = payload.get("old_values", {})
            new_values = payload.get("new_values", {})

            # 1. Log Activity
            activity = ActivityLog(
                user_id=user_id,
                action="Task Update",
                entity_type="Task",
                entity_id=task_id,
                description=f"Task '{task_title}' updated by {username}."
            )
            db.add(activity)

            # 2. Write Audit Trails for changed fields
            for field, old_val in old_values.items():
                new_val = new_values.get(field)
                audit = AuditLog(
                    entity_type="Task",
                    entity_id=task_id,
                    field_name=field,
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val) if new_val is not None else None,
                    changed_by=user_id,
                )
                db.add(audit)
            
            db.commit()

            # Refresh task to get details
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return

            # 3. Handle specific changes: status, assignee, deadline
            # A. Status change (e.g., Pending -> In Progress -> Completed)
            if "status" in old_values:
                old_status = old_values["status"]
                new_status = new_values["status"]

                # Log specific status change activity
                status_activity = ActivityLog(
                    user_id=user_id,
                    action="Task Status Change",
                    entity_type="Task",
                    entity_id=task_id,
                    description=f"Task '{task.title}' status changed from '{old_status}' to '{new_status}' by {username}."
                )
                db.add(status_activity)
                db.commit()

                # If completed, notify assignee and creator
                if new_status.lower() == "completed":
                    # Notify Assignee (if not the person who completed it)
                    if task.assignee_id and task.assignee_id != user_id:
                        await create_notification_and_notify(
                            db=db,
                            user_id=task.assignee_id,
                            title="Task Completed",
                            message=f"The task '{task.title}' has been marked as Completed.",
                            preference_key="task_completed"
                        )
                    # Notify Creator (if not the person who completed it)
                    if task.creator_id and task.creator_id != user_id:
                        await create_notification_and_notify(
                            db=db,
                            user_id=task.creator_id,
                            title="Task Completed",
                            message=f"The task '{task.title}' has been marked as Completed by {username}.",
                            preference_key="task_completed"
                        )

            # B. Assignee change (Task Assigned / Task Reassigned)
            if "assignee_id" in old_values:
                old_assignee_id = old_values["assignee_id"]
                new_assignee_id = new_values["assignee_id"]

                # Check if newly assigned
                if new_assignee_id:
                    new_assignee = db.query(User).filter(User.id == new_assignee_id).first()
                    new_name = new_assignee.full_name or new_assignee.email if new_assignee else ""
                    
                    if old_assignee_id:
                        # Reassigned
                        # Notify old assignee
                        await create_notification_and_notify(
                            db=db,
                            user_id=old_assignee_id,
                            title="Task Reassigned",
                            message=f"The task '{task.title}' you were working on has been reassigned to another member.",
                            preference_key="task_reassigned"
                        )
                        # Notify new assignee
                        await create_notification_and_notify(
                            db=db,
                            user_id=new_assignee_id,
                            title="Task Assigned (Reassignment)",
                            message=f"You have been assigned to the task '{task.title}' (previously assigned to someone else).",
                            preference_key="task_assigned",
                            trigger_email=True,
                            email_subject=f"Task Assigned: {task.title}",
                            email_body=f"Hi {new_name},\n\nYou have been assigned to the task '{task.title}' in project."
                        )
                    else:
                        # First assignment
                        await create_notification_and_notify(
                            db=db,
                            user_id=new_assignee_id,
                            title="Task Assigned",
                            message=f"You have been assigned to the task '{task.title}' by {username}.",
                            preference_key="task_assigned",
                            trigger_email=True,
                            email_subject=f"Task Assigned: {task.title}",
                            email_body=f"Hi {new_name},\n\nYou have been assigned to the task '{task.title}' by {username}."
                        )

                    # Log Activity
                    assign_activity = ActivityLog(
                        user_id=user_id,
                        action="Task Assignment",
                        entity_type="Task",
                        entity_id=task_id,
                        description=f"Task '{task.title}' assigned to {new_name} by {username}."
                    )
                    db.add(assign_activity)
                    db.commit()

            # C. Deadline updated
            if "deadline" in old_values:
                old_deadline = old_values["deadline"]
                new_deadline = new_values["deadline"]

                # Notify assignee if set
                if task.assignee_id and task.assignee_id != user_id:
                    assignee = db.query(User).filter(User.id == task.assignee_id).first()
                    assignee_name = assignee.full_name or assignee.email if assignee else ""
                    
                    old_date_str = str(old_deadline)[:10] if old_deadline else "None"
                    new_date_str = str(new_deadline)[:10] if new_deadline else "None"
                    
                    await create_notification_and_notify(
                        db=db,
                        user_id=task.assignee_id,
                        title="Task Deadline Updated",
                        message=f"The deadline for task '{task.title}' was changed from '{old_date_str}' to '{new_date_str}' by {username}.",
                        preference_key="task_deadline_updated",
                        trigger_email=True,
                        email_subject=f"Task Deadline Updated: {task.title}",
                        email_body=f"Hi {assignee_name},\n\nThe deadline for task '{task.title}' has been changed from '{old_date_str}' to '{new_date_str}' by {username}."
                    )

        elif event_type == "TASK_DELETED":
            task_id = payload["task_id"]
            task_title = payload["title"]
            
            activity = ActivityLog(
                user_id=user_id,
                action="Task Deletion",
                entity_type="Task",
                entity_id=task_id,
                description=f"Task '{task_title}' deleted by {username}."
            )
            db.add(activity)
            db.commit()

    except Exception as e:
        logger.error(f"Error handling background event {event_type}: {e}", exc_info=True)
    finally:
        db.close()

def publish_event(event_type: str, payload: Dict[str, Any], background_tasks: Any):
    """
    Publish an event to the background task executor.
    Takes background_tasks from FastAPI request context.
    """
    background_tasks.add_task(handle_event, event_type, payload)
