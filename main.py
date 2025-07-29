from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.routes import ai_booking, patients, booking
import os

app = FastAPI(
    title="Sistema de Agendamento Médico",
    description="API para gerenciamento de consultas médicas e exames",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar origins específicas
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

# Include routers
app.include_router(ai_booking.router, prefix="/api/v1/ai-booking", tags=["AI Booking"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patients"])
app.include_router(booking.router, prefix="/api/v1/booking", tags=["Booking"])
