from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class UserPreferencesUpdate(BaseModel):
    notification_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "task_assigned": True,
            "task_reassigned": True,
            "task_deadline_updated": True,
            "new_project_member_added": True,
            "project_updated": True,
            "task_completed": True
        }
    )

class UserOut(UserBase):
    id: int
    created_at: datetime
    notification_preferences: Dict[str, bool]

    class Config:
        from_attributes = True
