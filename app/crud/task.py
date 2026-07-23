from sqlalchemy.orm import Session
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from datetime import datetime
from typing import List

def get_task(db: Session, task_id: int) -> Task:
    return db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()

def get_project_tasks(db: Session, project_id: int) -> List[Task]:
    return db.query(Task).filter(Task.project_id == project_id, Task.deleted_at.is_(None)).all()

def create_task(db: Session, task: TaskCreate, project_id: int, creator_id: int) -> Task:
    db_task = Task(
        project_id=project_id,
        title=task.title,
        description=task.description,
        status=task.status or "Pending",
        assignee_id=task.assignee_id,
        creator_id=creator_id,
        deadline=task.deadline
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(db: Session, db_task: Task, task_update: TaskUpdate) -> Task:
    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    db_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, db_task: Task) -> Task:
    db_task.deleted_at = datetime.utcnow()
    db.commit()
    return db_task
