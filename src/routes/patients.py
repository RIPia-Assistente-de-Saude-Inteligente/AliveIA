"""
API routes for managing patients.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import aiosqlite

from database.connection import get_db
from database.models.schemas import PacienteCreate, PacienteUpdate, PacienteResponse, PacientesListResponse
from services import patient_service

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PacienteResponse)
async def create_patient(patient: PacienteCreate, db: aiosqlite.Connection = Depends(get_db)):
    """Create a new patient."""
    return await patient_service.create_patient(db, patient)

@router.get("/{patient_id}", response_model=PacienteResponse)
async def get_patient(patient_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Get a specific patient by their ID."""
    db_patient = await patient_service.get_patient_by_id(db, patient_id)
    if db_patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return db_patient

@router.get("/", response_model=PacientesListResponse)
async def list_patients(skip: int = 0, limit: int = 10, db: aiosqlite.Connection = Depends(get_db)):
    """List all patients with pagination."""
    patients = await patient_service.get_all_patients(db, skip, limit)
    return {"data": patients, "total": len(patients)} # Simplified total for example

@router.put("/{patient_id}", response_model=PacienteResponse)
async def update_patient(patient_id: int, patient: PacienteUpdate, db: aiosqlite.Connection = Depends(get_db)):
    """Update a patient's information."""
    updated_patient = await patient_service.update_patient(db, patient_id, patient)
    if updated_patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return updated_patient

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Delete a patient."""
    success = await patient_service.delete_patient(db, patient_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return
