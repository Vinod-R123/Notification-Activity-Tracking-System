from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.security import get_password_hash
from datetime import datetime
from typing import Dict

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first()

def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_preferences(db: Session, user_id: int, preferences: Dict[str, bool]):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        # Merge dicts
        current_prefs = dict(db_user.notification_preferences or {})
        current_prefs.update(preferences)
        db_user.notification_preferences = current_prefs
        db.commit()
        db.refresh(db_user)
    return db_user
