from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.project import Project
from app.models.user import User, ProjectMember
from app.schemas.project import ProjectCreate, ProjectUpdate
from datetime import datetime
from typing import List

def get_project(db: Session, project_id: int):
    return db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()

def get_user_projects(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Project]:
    return db.query(Project).filter(
        Project.deleted_at.is_(None)
    ).filter(
        or_(
            Project.creator_id == user_id,
            Project.members.any(id=user_id)
        )
    ).offset(skip).limit(limit).all()

def create_project(db: Session, project: ProjectCreate, creator_id: int) -> Project:
    db_project = Project(
        title=project.title,
        description=project.description,
        deadline=project.deadline,
        creator_id=creator_id
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def update_project(db: Session, db_project: Project, project_update: ProjectUpdate) -> Project:
    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)
    db.commit()
    db.refresh(db_project)
    return db_project

def delete_project(db: Session, db_project: Project) -> Project:
    db_project.deleted_at = datetime.utcnow()
    # We should also soft-delete all tasks in the project
    for task in db_project.tasks:
        task.deleted_at = datetime.utcnow()
    db.commit()
    return db_project

def add_project_member(db: Session, project_id: int, user_id: int) -> bool:
    # Check if user is already a member
    exists = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    if exists:
        return True
    
    db_member = ProjectMember(project_id=project_id, user_id=user_id)
    db.add(db_member)
    db.commit()
    return True

def remove_project_member(db: Session, project_id: int, user_id: int) -> bool:
    db_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    if db_member:
        db.delete(db_member)
        db.commit()
        return True
    return False

def is_project_member(db: Session, project_id: int, user_id: int) -> bool:
    project = get_project(db, project_id)
    if not project:
        return False
    if project.creator_id == user_id:
        return True
    # Check project_members table
    exists = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    return exists is not None
