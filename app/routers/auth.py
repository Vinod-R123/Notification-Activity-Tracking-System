from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.dependencies import get_db, get_current_user
from app.config import settings
from app.security import verify_password, create_access_token
from app.crud.user import get_user_by_email, create_user, update_user_preferences
from app.schemas.user import UserCreate, UserOut, UserPreferencesUpdate
from app.schemas.auth import Token
from app.models.user import User
from app.services.event_system import publish_event

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists."
        )
    user = create_user(db, user_in)
    return user

@router.post("/login", response_model=Token)
def login(
    background_tasks: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    # Trigger background event
    publish_event("USER_LOGIN", {"user_id": user.id}, background_tasks)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    # Trigger background event
    publish_event("USER_LOGOUT", {"user_id": current_user.id}, background_tasks)
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/preferences", response_model=UserOut)
def update_preferences(
    pref_in: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    updated_user = update_user_preferences(db, current_user.id, pref_in.notification_preferences)
    return updated_user
