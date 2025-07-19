"""
FastAPI main application for the medical appointment system.
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from pathlib import Path

# Import configuration and database
from config.settings import settings
from database.connection import db_manager

# Import routers
from routes import patients

app = FastAPI(
    title="Sistema de Agendamento Médico",
    description="API para gerenciamento de consultas médicas e exames",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await db_manager.initialize_database()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Sistema de Agendamento Médico API", "status": "running"}

@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "service": "medical-appointment-system",
        "version": "1.0.0"
    }

# Include routers
app.include_router(patients.router, prefix="/api/v1/patients", tags=["patients"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
