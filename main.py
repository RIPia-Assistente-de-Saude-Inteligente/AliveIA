"""
FastAPI main application for the medical appointment system.
Entry point centralizado da aplicação.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.routes import ai_booking, patients, booking
from src.config.settings import settings
from src.database.connection import db_manager
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends
import os
import logging

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != settings.api_token:
        raise HTTPException(status_code=403, detail="Token inválido")

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    allow_origins=settings.allowed_origins if hasattr(settings, 'allowed_origins') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve arquivos estáticos da pasta frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    """Serve a página principal do chat."""
    return FileResponse("frontend/index.html")

@app.get("/chat")
async def chat_page():
    """Serve a página do chat (mesmo que root)."""
    return FileResponse("frontend/index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Sistema de Agendamento Médico API"}

# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks."""
    try:
        logger.info("Inicializando aplicação...")
        # Initialize database if needed
        # await db_manager.initialize()
        logger.info("✅ Aplicação inicializada com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
        raise HTTPException(status_code=500, detail="Falha na inicialização da aplicação")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup tasks."""
    logger.info("Finalizando aplicação...")

# Include routers com prefixos corretos
app.include_router(ai_booking.router, prefix="/api/v1/ai-booking", tags=["AI Booking"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patients"])
app.include_router(booking.router, prefix="/api/v1/booking", tags=["Booking"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    )
