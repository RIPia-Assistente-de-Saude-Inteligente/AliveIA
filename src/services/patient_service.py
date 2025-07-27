"""
Service layer for patient-related operations.
"""
import aiosqlite
from typing import List, Optional
from database.models.schemas import PacienteCreate, PacienteUpdate, PacienteResponse

async def create_patient(db: aiosqlite.Connection, patient: PacienteCreate) -> PacienteResponse:
    """Creates a new patient in the database."""
    cursor = await db.execute(
        """
        INSERT INTO Pacientes (nome, cpf, data_nascimento, sexo)
        VALUES (?, ?, ?, ?)
        """,
        (patient.nome, patient.cpf, patient.data_nascimento, patient.sexo.value)
    )
    await db.commit()
    patient_id = cursor.lastrowid
    return PacienteResponse(id_paciente=patient_id, **patient.model_dump())

async def get_patient_by_id(db: aiosqlite.Connection, patient_id: int) -> Optional[PacienteResponse]:
    """Retrieves a patient by their ID."""
    cursor = await db.execute("SELECT * FROM Pacientes WHERE id_paciente = ?", (patient_id,))
    row = await cursor.fetchone()
    if row:
        return PacienteResponse(**dict(row))
    return None

async def get_all_patients(db: aiosqlite.Connection, skip: int = 0, limit: int = 100) -> List[dict]:
    cursor = await db.execute("SELECT * FROM Pacientes LIMIT ? OFFSET ?", (limit, skip))
    rows = await cursor.fetchall()
    return [PacienteResponse(**dict(row)) for row in rows]

async def update_patient(db: aiosqlite.Connection, patient_id: int, patient: PacienteUpdate) -> Optional[PacienteResponse]:
    """Updates a patient's information."""
    update_data = patient.model_dump(exclude_unset=True)
    if not update_data:
        return await get_patient_by_id(db, patient_id)

    fields = ", ".join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values())
    values.append(patient_id)

    cursor = await db.execute(f"UPDATE Pacientes SET {fields} WHERE id_paciente = ?", tuple(values))
    await db.commit()

    if cursor.rowcount > 0:
        return await get_patient_by_id(db, patient_id)
    return None

async def delete_patient(db: aiosqlite.Connection, patient_id: int) -> bool:
    """Deletes a patient from the database."""
    cursor = await db.execute("DELETE FROM Pacientes WHERE id_paciente = ?", (patient_id,))
    await db.commit()
    return cursor.rowcount > 0
