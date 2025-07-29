"""
Configuration settings for the FastAPI application.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # Database settings
    database_url: str = "sqlite:///./medical_system.db"
    
    # FastAPI settings
    app_name: str = "Sistema de Agendamento Médico"
    debug: bool = True
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security settings
    secret_key: str = "your-secret-key-change-this-in-production"
    access_token_expire_minutes: int = 30
    
    # CORS settings
    allowed_origins: list = ["http://localhost:3000", "http://localhost:8080"]
    
    # Google Gemini settings (if needed)
    google_api_key: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create settings instance
settings = Settings()

# Database file path
DATABASE_PATH = Path(__file__).parent.parent / "database" / "medical_system.db"
DATABASE_SCHEMA_PATH = Path(__file__).parent.parent / "database" / "database.sql"
