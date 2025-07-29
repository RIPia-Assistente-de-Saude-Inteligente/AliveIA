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

    # Google Gemini settings
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    
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
    allowed_origins: list = ["http://localhost:3000", "http://localhost:8080", "http://localhost:8000"]
    
    class Config:
        # Caminho absoluto para o .env na raiz do projeto
        env_file = Path(__file__).parent.parent.parent / ".env"
        case_sensitive = False
        extra = "ignore"  # Permite campos extras no .env sem erro

# Create settings instance
settings = Settings()

# Database file path
DATABASE_PATH = Path(__file__).parent.parent / "database" / "medical_system.db"
DATABASE_SCHEMA_PATH = Path(__file__).parent.parent / "database" / "database.sql"
