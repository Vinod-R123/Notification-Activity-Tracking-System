from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.user import UserOut

class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None

class ProjectOut(ProjectBase):
    id: int
    creator_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class ProjectDetailOut(ProjectOut):
    creator: Optional[UserOut] = None
    members: List[UserOut] = []

    class Config:
        from_attributes = True

class ProjectMemberAdd(BaseModel):
    user_id: int
