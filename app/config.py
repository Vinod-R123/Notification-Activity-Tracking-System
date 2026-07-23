from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Notification & Activity Tracking System"
    DATABASE_URL: str = "sqlite:///./project_management.db"
    SECRET_KEY: str = "supersecretkeychangeinproductionjwtkeyhere123!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Optional SMTP configuration. If set, we can send actual emails, otherwise we log and mock write to file.
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = 587
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = "noreply@projectmgmt.com"
    EMAILS_FROM_NAME: str = "Project Management System"
    
    # Mock Email output path
    EMAIL_MOCK_FILE: str = "mock_emails.txt"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
