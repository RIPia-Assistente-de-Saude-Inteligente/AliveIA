"""
API routes for AI-powered booking using Gemini integration.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from typing import Dict, Any
import aiosqlite
from datetime import datetime, timedelta

from database.connection import get_db
from database.models.schemas import PacienteCreate, AgendamentoCreate, StatusAgendamentoEnum
from services import patient_service, booking_service

# Import Data Extractor
from chatbot.core.data_extractor import ConsultationDataExtractor

router = APIRouter()

# Initialize Data Extractor
extractor = ConsultationDataExtractor()

@router.post("/process-message")
async def process_booking_message(
    message_data: Dict[str, str],
    db: aiosqlite.Connection = Depends(get_db)
):
    """
    Process natural language message for booking using Gemini AI.
    
    Args:
        message_data: {"message": "user message text"}
        db: Database connection
        
    Returns:
        Processed data and next steps
    """
    try:
        message = message_data.get("message", "").strip()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message is required"
            )
        
        # Extract data using Gemini
        extracted_data = extractor.extract_consultation_data(message)
        print(extracted_data)
        # Validate essential data
        validation = extractor.validate_essential_data(extracted_data)
        
        response = {
            "success": True,
            "extracted_data": extracted_data,
            "validation": validation,
            "can_proceed": validation["is_valid"]
        }
        
        # If data is insufficient, generate next question
        if not validation["is_valid"]:
            next_question = extractor.generate_missing_data_questions(extracted_data)
            response["next_question"] = next_question
            response["status"] = "need_more_info"
        else:
            response["status"] = "ready_to_book"
            response["message"] = "Dados suficientes para agendamento!"
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )

@router.post("/create-from-ai")
async def create_booking_from_ai(
    ai_data: Dict[str, Any],
    db: aiosqlite.Connection = Depends(get_db)
):
    """
    Create a complete booking from AI-extracted data.
    
    Args:
        ai_data: Extracted data from AI processing
        db: Database connection
        
    Returns:
        Created appointment details
    """
    try:
        extracted_data = ai_data.get("extracted_data", {})

        if "dados_extraidos" not in extracted_data:
            extracted_data = extractor._process_extracted_data(extracted_data)
        
        # Validate data completeness
        validation = extractor.validate_essential_data(extracted_data)
        
        if not validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient data: {validation['missing_essential']}"
            )
        
        # Extract patient data
        paciente_data = extracted_data.get("paciente", {})
        agendamento_info = extracted_data.get("agendamento_info", {})
        preferencias = extracted_data.get("preferencias", {})
        
        # Create or get patient using patient_service
        patient_id = await _create_or_get_patient_via_service(db, paciente_data)
        
        if not patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create or find patient"
            )
        
        # Get IDs for related entities using booking services
        specialty_id = await _get_specialty_id_via_service(db, agendamento_info.get("especialidade"))
        doctor_id = await _get_doctor_by_specialty_via_service(db, specialty_id) if specialty_id else None
        location_id = await _get_default_location_via_service(db)
        appointment_type_id = await _get_appointment_type_id_via_service(db, agendamento_info.get("tipo_consulta", "Primeira Consulta"))
        convenio_id = await _get_convenio_id(db, agendamento_info.get("nome_convenio")) if agendamento_info.get("tem_convenio") else None
        
        # Parse date and time
        data_agendamento = _parse_appointment_datetime(
            preferencias.get("data_preferencia"),
            preferencias.get("horario_preferencia", "09:00")
        )
        
        # Calculate end time (default 60 minutes)
        data_fim = data_agendamento + timedelta(minutes=60)
        
        # Create appointment using booking_service
        appointment_data = AgendamentoCreate(
            id_paciente=patient_id,
            id_local=location_id,
            id_convenio=convenio_id,
            id_tipo_consulta=appointment_type_id,
            id_exame=None,
            id_medico=doctor_id,
            data_hora_inicio=data_agendamento.isoformat(),
            data_hora_fim=data_fim.isoformat(),
            status=StatusAgendamentoEnum.AGENDADO,
            observacoes=preferencias.get("observacoes")
        )
        
        # Use booking service to create appointment
        created_appointment = await booking_service.create_appointment(db, appointment_data)
        
        # Get complete appointment details
        appointment_details = await _get_appointment_details(db, created_appointment.id_agendamento)
        
        return {
            "success": True,
            "message": "Agendamento criado com sucesso!",
            "appointment_id": created_appointment.id_agendamento,
            "appointment_data": appointment_details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating appointment: {str(e)}"
        )

async def _create_or_get_patient_via_service(db: aiosqlite.Connection, paciente_data: Dict[str, Any]) -> int:
    """Create or get existing patient using patient_service."""
    nome = paciente_data.get("nome")
    cpf = paciente_data.get("cpf")
    
    if not nome:
        return None
    
    # Check if patient exists by CPF
    if cpf:
        cursor = await db.execute("SELECT id_paciente FROM Pacientes WHERE cpf = ?", (cpf,))
        result = await cursor.fetchone()
        if result:
            return result[0]
    
    # Check by name
    cursor = await db.execute("SELECT id_paciente FROM Pacientes WHERE nome = ?", (nome,))
    result = await cursor.fetchone()
    if result:
        return result[0]
    
    # Create new patient using service
    patient_create = PacienteCreate(
        nome=nome,
        cpf=cpf or "",
        data_nascimento=_parse_date(paciente_data.get("data_nascimento")) or "1990-01-01",
        sexo=paciente_data.get("sexo") or "O",
        telefone="",
        email="",
        endereco=""
    )
    
    created_patient = await patient_service.create_patient(db, patient_create)
    return created_patient.id_paciente

async def _get_specialty_id_via_service(db: aiosqlite.Connection, specialty_name: str) -> int:
    """Get specialty ID by name using booking_service."""
    if not specialty_name:
        return None
    
    specialties = await booking_service.get_all_specialties(db)
    for specialty in specialties:
        if specialty_name.lower() in specialty.nome.lower():
            return specialty.id_especialidade
    return None

async def _get_doctor_by_specialty_via_service(db: aiosqlite.Connection, specialty_id: int) -> int:
    """Get first available doctor for specialty using booking_service."""
    if not specialty_id:
        return None
    
    doctors = await booking_service.get_all_doctors(db)
    # Get doctors by specialty (simplified - would need a service method for this)
    cursor = await db.execute(
        """
        SELECT m.id_medico FROM Medicos m
        JOIN Medico_Especialidades me ON m.id_medico = me.id_medico
        WHERE me.id_especialidade = ?
        LIMIT 1
        """,
        (specialty_id,)
    )
    result = await cursor.fetchone()
    return result[0] if result else None

async def _get_default_location_via_service(db: aiosqlite.Connection) -> int:
    """Get default location using booking_service."""
    locations = await booking_service.get_all_locations(db)
    return locations[0].id_local if locations else 1

async def _get_appointment_type_id_via_service(db: aiosqlite.Connection, type_desc: str) -> int:
    """Get appointment type ID using booking_service."""
    if not type_desc:
        type_desc = "Primeira Consulta"
    
    appointment_types = await booking_service.get_all_appointment_types(db)
    for appt_type in appointment_types:
        if type_desc.lower() in appt_type.descricao.lower():
            return appt_type.id_tipo_consulta
    
    # Return first type as default
    return appointment_types[0].id_tipo_consulta if appointment_types else 1

async def _get_convenio_id(db: aiosqlite.Connection, convenio_name: str) -> int:
    """Get convenio ID by name."""
    if not convenio_name:
        return None
    
    cursor = await db.execute(
        "SELECT id_convenio FROM Convenios WHERE nome LIKE ?",
        (f"%{convenio_name}%",)
    )
    result = await cursor.fetchone()
    return result[0] if result else None

def _parse_date(date_str: str) -> str:
    """Parse date from DD/MM/YYYY to YYYY-MM-DD."""
    if not date_str:
        return None
    
    try:
        if "/" in date_str:
            day, month, year = date_str.split("/")
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return date_str
    except:
        return None

def _parse_appointment_datetime(date_str: str, time_str: str = "09:00") -> datetime:
    """Parse appointment date and time."""
    
    if not date_str:
        # Default to tomorrow
        date_str = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    parsed_date = _parse_date(date_str)
    if not parsed_date:
        parsed_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if not time_str:
        time_str = "09:00"
    
    return datetime.strptime(f"{parsed_date} {time_str}", "%Y-%m-%d %H:%M")

async def _get_appointment_details(db: aiosqlite.Connection, appointment_id: int) -> Dict[str, Any]:
    """Get complete appointment details."""
    cursor = await db.execute(
        """
        SELECT 
            a.*,
            p.nome as paciente_nome,
            p.cpf as paciente_cpf,
            e.nome as especialidade_nome,
            m.nome as medico_nome,
            l.nome as local_nome,
            tc.descricao as tipo_consulta,
            c.nome as convenio_nome
        FROM Agendamentos a
        JOIN Pacientes p ON a.id_paciente = p.id_paciente
        LEFT JOIN Medicos m ON a.id_medico = m.id_medico
        LEFT JOIN Medico_Especialidades me ON m.id_medico = me.id_medico
        LEFT JOIN Especialidades e ON me.id_especialidade = e.id_especialidade
        LEFT JOIN Locais_Atendimento l ON a.id_local = l.id_local
        LEFT JOIN Tipos_Consulta tc ON a.id_tipo_consulta = tc.id_tipo_consulta
        LEFT JOIN Convenios c ON a.id_convenio = c.id_convenio
        WHERE a.id_agendamento = ?
        """,
        (appointment_id,)
    )
    
    result = await cursor.fetchone()
    if result:
        return dict(result)
    return None
