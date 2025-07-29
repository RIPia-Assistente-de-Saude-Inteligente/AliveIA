"""
Service layer for the booking process.
"""
import aiosqlite
from typing import List
from database.models.schemas import AgendamentoCreate, AgendamentoResponse, MedicoResponse, EspecialidadeResponse, LocalAtendimentoResponse, TipoConsultaResponse, ExameResponse

# Since these are fixed, we can query them once and potentially cache them.

async def get_all_specialties(db: aiosqlite.Connection) -> List[EspecialidadeResponse]:
    cursor = await db.execute("SELECT * FROM Especialidades")
    rows = await cursor.fetchall()
    return [EspecialidadeResponse(**dict(row)) for row in rows]

async def get_all_doctors(db: aiosqlite.Connection) -> List[MedicoResponse]:
    cursor = await db.execute("SELECT * FROM Medicos")
    rows = await cursor.fetchall()
    return [MedicoResponse(**dict(row)) for row in rows]

async def get_all_locations(db: aiosqlite.Connection) -> List[LocalAtendimentoResponse]:
    cursor = await db.execute("SELECT * FROM Locais_Atendimento")
    rows = await cursor.fetchall()
    return [LocalAtendimentoResponse(**dict(row)) for row in rows]

async def get_all_appointment_types(db: aiosqlite.Connection) -> List[TipoConsultaResponse]:
    cursor = await db.execute("SELECT * FROM Tipos_Consulta")
    rows = await cursor.fetchall()
    return [TipoConsultaResponse(**dict(row)) for row in rows]

async def get_all_exams(db: aiosqlite.Connection) -> List[ExameResponse]:
    cursor = await db.execute("SELECT * FROM Exames")
    rows = await cursor.fetchall()
    return [ExameResponse(**dict(row)) for row in rows]

async def create_appointment(db: aiosqlite.Connection, appt: AgendamentoCreate) -> AgendamentoResponse:
    """Creates a new appointment in the database."""
    cursor = await db.execute(
        """
        INSERT INTO Agendamentos (id_paciente, id_local, id_convenio, id_tipo_consulta, id_exame, id_medico, 
                                  data_hora_inicio, data_hora_fim, status, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (appt.id_paciente, appt.id_local, appt.id_convenio, appt.id_tipo_consulta, appt.id_exame, appt.id_medico,
         appt.data_hora_inicio, appt.data_hora_fim, appt.status.value, appt.observacoes)
    )
    await db.commit()
    appt_id = cursor.lastrowid
    
    # Fetch the created record to return the full object
    cursor = await db.execute("SELECT * FROM Agendamentos WHERE id_agendamento = ?", (appt_id,))
    new_appt_row = await cursor.fetchone()
    return AgendamentoResponse(**dict(new_appt_row))
