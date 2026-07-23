from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.user import UserOut

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "Pending"
    assignee_id: Optional[int] = None
    deadline: Optional[datetime] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[int] = None
    deadline: Optional[datetime] = None

class TaskOut(TaskBase):
    id: int
    project_id: int
    creator_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    assignee: Optional[UserOut] = None

    class Config:
        from_attributes = True
