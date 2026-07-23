from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import get_db, get_current_user
from app.crud.project import get_project, is_project_member
from app.crud.task import get_task, get_project_tasks, create_task, update_task, delete_task
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut
from app.models.user import User
from app.services.event_system import publish_event

# Note: Prefix is not set on router globally because we have project-nested creation and flat modification endpoints
router = APIRouter(tags=["Tasks"])

@router.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_new_task(
    project_id: int,
    task_in: TaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if not is_project_member(db, project_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to add tasks to this project")

    task = create_task(db, task_in, project_id, current_user.id)

    # Trigger background creation activity log
    publish_event("TASK_CREATED", {
        "task_id": task.id,
        "project_id": project_id,
        "user_id": current_user.id,
        "title": task.title
    }, background_tasks)

    return task

@router.get("/projects/{project_id}/tasks", response_model=List[TaskOut])
def list_tasks_for_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if not is_project_member(db, project_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view tasks for this project")

    tasks = get_project_tasks(db, project_id)
    return tasks

@router.get("/tasks/{id}", response_model=TaskOut)
def read_task(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = get_task(db, id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if not is_project_member(db, task.project_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this task")

    return task

@router.put("/tasks/{id}", response_model=TaskOut)
def update_existing_task(
    id: int,
    task_in: TaskUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = get_task(db, id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if not is_project_member(db, task.project_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to edit this task")

    # Capture old values
    old_values = {}
    fields_to_track = ["title", "description", "status", "assignee_id", "deadline"]
    for field in fields_to_track:
        old_values[field] = getattr(task, field)

    update_task(db, task, task_in)

    # Capture new values and check diffs
    changed_fields = {}
    new_values = {}
    for field in fields_to_track:
        new_val = getattr(task, field)
        if old_values[field] != new_val:
            changed_fields[field] = old_values[field]
            new_values[field] = new_val

    # Trigger background logs only if values changed
    if changed_fields:
        publish_event("TASK_UPDATED", {
            "task_id": task.id,
            "project_id": task.project_id,
            "user_id": current_user.id,
            "title": task.title,
            "old_values": changed_fields,
            "new_values": new_values
        }, background_tasks)

    return task

@router.delete("/tasks/{id}", response_model=TaskOut)
def delete_existing_task(
    id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = get_task(db, id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if not is_project_member(db, task.project_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")

    delete_task(db, task)

    # Trigger background delete activity
    publish_event("TASK_DELETED", {
        "task_id": id,
        "project_id": task.project_id,
        "user_id": current_user.id,
        "title": task.title
    }, background_tasks)

    return task
