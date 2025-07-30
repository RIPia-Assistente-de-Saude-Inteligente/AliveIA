"""
API routes for the booking process.
"""
from fastapi import APIRouter, Depends, status
from typing import List
from database.models.schemas import BookingInput
import aiosqlite

from src.database.connection import get_db
from src.database.models.schemas import (
    AgendamentoCreate, AgendamentoResponse,
    MedicoResponse, EspecialidadeResponse, LocalAtendimentoResponse,
    TipoConsultaResponse, ExameResponse
)
from src.services import booking_service

router = APIRouter()

@router.get("/specialties", response_model=List[EspecialidadeResponse])
async def list_specialties(db: aiosqlite.Connection = Depends(get_db)):
    """List all available medical specialties."""
    return await booking_service.get_all_specialties(db)

@router.get("/doctors", response_model=List[MedicoResponse])
async def list_doctors(db: aiosqlite.Connection = Depends(get_db)):
    """List all available doctors."""
    return await booking_service.get_all_doctors(db)

@router.get("/locations", response_model=List[LocalAtendimentoResponse])
async def list_locations(db: aiosqlite.Connection = Depends(get_db)):
    """List all available locations."""
    return await booking_service.get_all_locations(db)

@router.get("/appointment-types", response_model=List[TipoConsultaResponse])
async def list_appointment_types(db: aiosqlite.Connection = Depends(get_db)):
    """List all available appointment types."""
    return await booking_service.get_all_appointment_types(db)

@router.get("/exams", response_model=List[ExameResponse])
async def list_exams(db: aiosqlite.Connection = Depends(get_db)):
    """List all available exams."""
    return await booking_service.get_all_exams(db)

@router.post("/appointments", status_code=status.HTTP_201_CREATED, response_model=AgendamentoResponse)
async def create_new_appointment(appt: AgendamentoCreate, db: aiosqlite.Connection = Depends(get_db)):
    """Create a new appointment for a patient."""
    return await booking_service.create_appointment(db, appt)
@router.post("/booking")
def create_booking(data: BookingInput):
    # use data.patient_id etc
    return {"msg": "Agendado com sucesso"}
