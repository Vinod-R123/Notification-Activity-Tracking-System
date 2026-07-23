from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import get_db, get_current_user
from app.crud.project import (
    get_project, get_user_projects, create_project, update_project, 
    delete_project, add_project_member, remove_project_member, is_project_member
)
from app.crud.user import get_user
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut, ProjectDetailOut, ProjectMemberAdd
from app.models.user import User
from app.services.event_system import publish_event

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_new_project(
    project_in: ProjectCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = create_project(db, project_in, current_user.id)
    
    # Trigger background activity log
    publish_event("PROJECT_CREATED", {
        "project_id": project.id,
        "user_id": current_user.id,
        "title": project.title
    }, background_tasks)
    
    return project

@router.get("", response_model=List[ProjectOut])
def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    projects = get_user_projects(db, current_user.id, skip=skip, limit=limit)
    return projects

@router.get("/{id}", response_model=ProjectDetailOut)
def read_project(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_project(db, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Authorize: user must be member or creator
    if not is_project_member(db, project.id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this project")
        
    return project

@router.put("/{id}", response_model=ProjectOut)
def update_existing_project(
    id: int,
    project_in: ProjectUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_project(db, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the project creator can edit it")

    # Capture old values for differential auditing
    old_values = {}
    for field in ["title", "description", "deadline"]:
        old_values[field] = getattr(project, field)

    update_project(db, project, project_in)

    # Capture new values and check diffs
    changed_fields = {}
    new_values = {}
    for field in ["title", "description", "deadline"]:
        new_val = getattr(project, field)
        if old_values[field] != new_val:
            changed_fields[field] = old_values[field]
            new_values[field] = new_val

    # Trigger update audit event only if fields changed
    if changed_fields:
        publish_event("PROJECT_UPDATED", {
            "project_id": project.id,
            "user_id": current_user.id,
            "title": project.title,
            "old_values": changed_fields,
            "new_values": new_values
        }, background_tasks)

    return project

@router.delete("/{id}", response_model=ProjectOut)
def delete_existing_project(
    id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_project(db, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the project creator can delete it")

    delete_project(db, project)

    # Trigger background delete activity
    publish_event("PROJECT_DELETED", {
        "project_id": id,
        "user_id": current_user.id,
        "title": project.title
    }, background_tasks)

    return project

# --- Member Management ---

@router.post("/{id}/members", status_code=status.HTTP_200_OK)
def add_member(
    id: int,
    member_in: ProjectMemberAdd,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_project(db, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the project creator can add members")

    # Check if user to add exists
    user_to_add = get_user(db, member_in.user_id)
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User to add not found")

    add_project_member(db, id, member_in.user_id)

    # Trigger member added background event
    publish_event("MEMBER_ADDED", {
        "project_id": id,
        "user_id": current_user.id,
        "member_id": member_in.user_id
    }, background_tasks)

    return {"message": f"Successfully added user {user_to_add.email} to project"}

@router.delete("/{id}/members/{user_id}", status_code=status.HTTP_200_OK)
def remove_member(
    id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_project(db, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the project creator can remove members")

    removed = remove_project_member(db, id, user_id)
    if not removed:
        raise HTTPException(status_code=400, detail="User is not a member of this project")

    # Simple activity could be added, or keep it light.
    return {"message": "Successfully removed member from project"}
