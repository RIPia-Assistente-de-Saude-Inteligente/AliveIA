# src/routes/ai_booking.py
from fastapi import APIRouter, status, HTTPException, Depends, UploadFile, File
from typing import Dict
import os
from dotenv import load_dotenv
import google.generativeai as genai
from src.chatbot.flows.flow_manager import FlowManager
import logging
from datetime import datetime, time
from src.database.connection import get_db
from src.database.models.schemas import PacienteCreate, AgendamentoCreate, SexoEnum, StatusAgendamentoEnum
from src.services.patient_service import get_patient_by_cpf, create_patient
from src.services.booking_service import create_appointment
import aiosqlite
import json

# Carregue as variáveis do arquivo .env
load_dotenv()

# Configuração do modelo e do FlowManager
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
ai_model = genai.GenerativeModel('gemini-1.5-flash-latest')
flow_manager = FlowManager(model=ai_model)

router = APIRouter()


@router.post("/process-message")
async def process_booking_message(
        message_data: Dict[str, str],
        user_id: str = "session_123",
        db: aiosqlite.Connection = Depends(get_db)
):
    """
    Processa a mensagem do usuário e retorna o estado completo da conversa.
    """
    try:
        message = message_data.get("message", "").strip()
        logging.info(f"Recebida requisição para user_id='{user_id}' com a mensagem: '{message}'")

        if not message:
            logging.warning("Mensagem recebida está vazia.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A mensagem é obrigatória")

        conversation_update = flow_manager.process_user_response(user_id, message)

        # --- PONTO DE LOG CRÍTICO ---
        logging.info(f"PACOTE DE DADOS A SER ENVIADO: {conversation_update}")
        # -----------------------------

        # Se o usuário chegou ao estado END após confirmar, cria automaticamente o agendamento
        if conversation_update.get("current_state") == "END":
            try:
                # LOG CRÍTICO: Dados que serão enviados para criação
                logging.info(f"🔍 DADOS CONVERSATION_DATA: {conversation_update.get('conversation_data')}")
                
                # Cria o agendamento automaticamente
                appointment_result = await create_appointment_from_ai({
                    "extracted_data": conversation_update.get("conversation_data")
                }, db)
                
                # LOG CRÍTICO: Resultado da criação
                logging.info(f"🔍 APPOINTMENT_RESULT: {appointment_result}")
                
                # Atualiza a mensagem para incluir os detalhes do agendamento
                appointment_data = appointment_result['appointment_data']
                logging.info(f"🔍 APPOINTMENT_DATA EXTRAÍDO: {appointment_data}")
                success_message = f"""✅ {conversation_update.get("next_question")}

🎉 **Agendamento criado com sucesso!**

📋 **Detalhes do Agendamento:**
• **ID:** {appointment_data['id_agendamento']}
• **Paciente:** {appointment_data['nome_paciente']}
• **Médico:** {appointment_data['nome_medico']}
• **Especialidade:** {appointment_data['especialidade']}
• **Data/Hora:** {appointment_data['data_agendamento']}
• **Local:** {appointment_data['local']}
• **Convênio:** {appointment_data['convenio']}"""

                response = {
                    "success": True,
                    "next_question": success_message,
                    "conversation_data": conversation_update.get("conversation_data"),
                    "current_state": conversation_update.get("current_state"),
                    "extracted_data": conversation_update.get("conversation_data"),
                    "status": "appointment_created",
                    "can_proceed": False,
                    "validation": {"is_valid": True},
                    "appointment_data": appointment_result['appointment_data']
                }
                
                return response
                
            except Exception as e:
                logging.error(f"Erro ao criar agendamento automaticamente: {e}")
                response = {
                    "success": True,
                    "next_question": f"❌ Erro ao criar agendamento. {str(e)}",
                    "conversation_data": conversation_update.get("conversation_data"),
                    "current_state": "ERROR",
                    "extracted_data": conversation_update.get("conversation_data"),
                    "status": "error",
                    "can_proceed": False,
                    "validation": {"is_valid": False}
                }
                return response

        # Calcula progresso baseado nos dados coletados
        conversation_data = conversation_update.get("conversation_data", {})
        total_fields = 11  # Total de campos necessários
        collected_fields = 0
        
        # Conta campos do paciente
        paciente = conversation_data.get("paciente", {})
        collected_fields += sum(1 for v in [paciente.get("nome"), paciente.get("cpf"), 
                                          paciente.get("data_nascimento"), paciente.get("sexo")] if v)
        
        # Conta campos do agendamento
        agendamento = conversation_data.get("agendamento_info", {})
        collected_fields += sum(1 for v in [agendamento.get("tipo"), 
                                          agendamento.get("especialidade") or agendamento.get("nome_exame"),
                                          agendamento.get("local"), agendamento.get("convenio")] if v)
        
        # Conta campos de contato
        contato = conversation_data.get("contato", {})
        collected_fields += sum(1 for v in [contato.get("telefone"), contato.get("email")] if v)
        
        # Conta campos de preferências
        preferencias = conversation_data.get("preferencias", {})
        collected_fields += sum(1 for v in [preferencias.get("data_preferencia"), 
                                          preferencias.get("horario_preferencia")] if v)
        
        completion_percentage = (collected_fields / total_fields) * 100

        response = {
            "success": True,
            "next_question": conversation_update.get("next_question"),
            "conversation_data": conversation_update.get("conversation_data"),
            "current_state": conversation_update.get("current_state"),
            # Campos que o frontend espera:
            "extracted_data": conversation_update.get("conversation_data"),
            "status": "ready_to_book" if conversation_update.get(
                "current_state") == "CONFIRMATION" else "need_more_info",
            "can_proceed": conversation_update.get("current_state") == "CONFIRMATION",
            "validation": {
                "is_valid": True,
                "completion_percentage": completion_percentage,
                "collected_fields": collected_fields,
                "total_fields": total_fields
            }
        }

        return response

    except Exception as e:
        logging.error(f"ERRO CRÍTICO NA ROTA DA API: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar a mensagem: {str(e)}"
        )

@router.post("/process-pdf")
async def process_pdf_file(pdf_file: UploadFile = File(...), db: aiosqlite.Connection = Depends(get_db)):
   try:
       content = await pdf_file.read()

       from PyPDF2 import PdfReader
       from io import BytesIO

       reader = PdfReader(BytesIO(content))
       full_text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())

       if not full_text.strip():
           raise HTTPException(status_code=400, detail="Não foi possível extrair texto do PDF.")

       # Prompt estruturado para resposta em JSON
       prompt = f"""
Você receberá o conteúdo extraído de um PDF. Extraia todos os dados relevantes para agendamento de consulta médica.
Se algum dado não estiver presente, coloque o valor como null.
Responda SOMENTE com um JSON no seguinte formato:
Se um campo não estiver presente no texto, **tente inferir** ou preencha com null (sem aspas).
Nunca retorne campos vazios ("").


{{
 "paciente": {{
   "nome": "...",
   "cpf": "...",
   "data_nascimento": "YYYY-MM-DD",
   "sexo": "M", "F" ou "O"
 }},
 "contato": {{
   "telefone": "...",
   "email": "..."
 }},
 "agendamento_info": {{
   "tipo": "consulta" ou "exame",
   "especialidade": "...",
   "nome_exame": "..."
 }},
 "preferencias": {{
   "data_preferencia": "YYYY-MM-DD",
   "horario_preferencia": "HH:MM" ou "manhã" ou "tarde" ou "noite"
 }}
}}

Conteúdo do PDF:
{full_text}
"""

       logging.info("🔎 Enviando texto para o Gemini...")
       result = ai_model.generate_content(prompt, generation_config={"temperature": 0.3})
       extracted_json = result.text.strip()

       logging.info(f"📥 Resposta bruta do Gemini: {extracted_json[:300]}...")

       # Limpeza para garantir que seja JSON válido
       extracted_clean = extracted_json.replace("```json", "").replace("```", "").strip()
       conversation_data = json.loads(extracted_clean)

       # Validação básica do JSON
       if "paciente" not in conversation_data or not conversation_data["paciente"].get("cpf"):
           raise HTTPException(status_code=400, detail="Os dados extraídos estão incompletos ou inválidos.")

       # Opcional: já cria o agendamento automaticamente (remova se quiser controle manual)
       agendamento_result = await create_appointment_from_ai({"extracted_data": conversation_data}, db)

       return {
           "success": True,
           "message": "PDF processado com sucesso",
           "extracted_data": conversation_data,
           "agendamento": agendamento_result
       }

   except json.JSONDecodeError as e:
       logging.error(f"❌ Erro ao decodificar JSON: {e}")
       raise HTTPException(status_code=500, detail="Erro ao interpretar a resposta da IA.")
   except Exception as e:
       logging.error(f"❌ Erro ao processar PDF: {e}", exc_info=True)
       raise HTTPException(status_code=500, detail="Erro ao processar PDF.")


@router.post("/create-from-ai", status_code=status.HTTP_201_CREATED)
async def create_appointment_from_ai(
        conversation_data: Dict,
        db: aiosqlite.Connection = Depends(get_db)
):
    """
    Cria um agendamento completo baseado nos dados coletados pelo chatbot.
    """
    # A PRIMEIRA LINHA DEVE SER ESTA:
    logging.info(f"PAYLOAD RECEBIDO PARA CRIAÇÃO: {conversation_data}")

    try:
        logging.info(f"Recebendo dados do chatbot: {conversation_data}")

        # CORREÇÃO: Extrai dados da estrutura aninhada 'extracted_data'
        extracted_data = conversation_data.get("extracted_data", {})
        paciente_data = extracted_data.get("paciente", {})
        contato_data = extracted_data.get("contato", {})
        agendamento_data = extracted_data.get("agendamento_info", {})
        preferencias_data = extracted_data.get("preferencias", {})

        # Validação dos dados obrigatórios
        required_patient_fields = ["nome", "cpf", "data_nascimento", "sexo"]
        for field in required_patient_fields:
            if not paciente_data.get(field):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Campo obrigatório ausente: paciente.{field}"
                )

        # Validação dos dados de agendamento
        if not preferencias_data.get("data_preferencia"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data de preferência é obrigatória"
            )

        # Converte sexo para enum
        sexo_map = {"M": SexoEnum.MASCULINO, "F": SexoEnum.FEMININO, "O": SexoEnum.OUTRO}
        sexo_enum = sexo_map.get(paciente_data["sexo"])
        if not sexo_enum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sexo inválido: {paciente_data['sexo']}"
            )

        # Verifica se paciente já existe pelo CPF
        existing_patient = await get_patient_by_cpf(db, paciente_data["cpf"])

        if existing_patient:
            logging.info(f"Paciente já existe com CPF {paciente_data['cpf']}: {existing_patient.id_paciente}")
            patient_id = existing_patient.id_paciente
        else:
            # Cria novo paciente
            patient_create = PacienteCreate(
                nome=paciente_data["nome"],
                cpf=paciente_data["cpf"],
                data_nascimento=paciente_data["data_nascimento"],
                sexo=sexo_enum
            )

            new_patient = await create_patient(db, patient_create)
            patient_id = new_patient.id_paciente
            logging.info(f"Novo paciente criado com ID: {patient_id}")

        # Processa data e horário do agendamento
        data_agendamento = preferencias_data["data_preferencia"]  # formato YYYY-MM-DD
        horario_preferencia = preferencias_data.get("horario_preferencia", "09:00")

        # Converte horário para time object
        try:
            if ":" in horario_preferencia:
                hora, minuto = map(int, horario_preferencia.split(":"))
            else:
                # Se for texto como "manhã", "tarde", usa horários padrão
                hora_map = {
                    "manhã": 9, "manha": 9,
                    "tarde": 14,
                    "noite": 19
                }
                hora = hora_map.get(horario_preferencia.lower(), 9)
                minuto = 0

            hora_inicio = time(hora, minuto)
            hora_fim = time(hora + 1 if hora < 23 else 23, minuto)  # 1 hora de duração

        except (ValueError, TypeError):
            # Horário padrão se houver erro
            hora_inicio = time(9, 0)
            hora_fim = time(10, 0)

        # Combina data e hora
        data_inicio = datetime.strptime(data_agendamento, "%Y-%m-%d").replace(
            hour=hora_inicio.hour, minute=hora_inicio.minute
        )
        data_fim = datetime.strptime(data_agendamento, "%Y-%m-%d").replace(
            hour=hora_fim.hour, minute=hora_fim.minute
        )

        # Seleciona um médico baseado na especialidade
        especialidade_solicitada = agendamento_data.get("especialidade", "")
        selected_doctor_id = None
        selected_doctor_name = "Aguardando confirmação"
        
        if especialidade_solicitada:
            try:
                # Busca médicos que atendem a especialidade solicitada
                query = """
                SELECT m.id_medico, m.nome 
                FROM Medicos m
                JOIN Medico_Especialidades me ON m.id_medico = me.id_medico
                JOIN Especialidades e ON me.id_especialidade = e.id_especialidade
                WHERE e.nome = ?
                LIMIT 1
                """
                
                async with db.execute(query, (especialidade_solicitada,)) as cursor:
                    doctor_row = await cursor.fetchone()
                    if doctor_row:
                        selected_doctor_id = doctor_row[0]
                        selected_doctor_name = doctor_row[1]
                        logging.info(f"Médico selecionado: {selected_doctor_name} (ID: {selected_doctor_id}) para especialidade: {especialidade_solicitada}")
                    else:
                        logging.warning(f"Nenhum médico encontrado para a especialidade: {especialidade_solicitada}")
                        
            except Exception as e:
                logging.error(f"Erro ao buscar médico por especialidade: {e}")

        # Cria o agendamento diretamente no banco sem usar o schema problemático
        cursor = await db.execute(
            """
            INSERT INTO Agendamentos (id_paciente, id_local, id_convenio, id_tipo_consulta, id_exame, id_medico, 
                                      data_hora_inicio, data_hora_fim, status, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (patient_id, 1, None, 1 if agendamento_data.get("tipo") == "consulta" else None,
             1 if agendamento_data.get("tipo") == "exame" else None, selected_doctor_id,
             data_inicio, data_fim, StatusAgendamentoEnum.AGENDADO.value,
             f"Agendamento criado via chatbot. Tipo: {agendamento_data.get('tipo', 'N/A')}, Especialidade/Exame: {agendamento_data.get('especialidade', '')}{agendamento_data.get('nome_exame', '')}, Contato: {contato_data.get('telefone', 'N/A')}")
        )
        await db.commit()
        appointment_id = cursor.lastrowid

        logging.info(f"Agendamento criado com sucesso - ID: {appointment_id}")

        # Pega os dados que já foram coletados anteriormente no fluxo
        data_agendamento = preferencias_data.get("data_preferencia")
        horario_preferencia = preferencias_data.get("horario_preferencia")

        # Monta a string de data e hora para exibição
        data_hora_str = f"{data_agendamento} às {horario_preferencia}" if data_agendamento and horario_preferencia else "Não informado"

        # Determina a especialidade ou exame
        especialidade_valor = agendamento_data.get("especialidade") or agendamento_data.get("nome_exame") or "Não informado"

        return {
            "success": True,
            "message": "Agendamento criado com sucesso!",
            "appointment_data": {
                "id_agendamento": appointment_id,
                "nome_paciente": paciente_data.get("nome", "Não informado"),
                "nome_medico": selected_doctor_name,  # Agora usa o médico selecionado
                "especialidade": especialidade_valor,
                "data_agendamento": data_hora_str,  # Enviando data e hora combinadas
                "local": agendamento_data.get("local", "Não informado"),
                "convenio": agendamento_data.get("convenio", "Particular"),
                "observacoes": "Agendamento criado via chatbot"
            }
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logging.error(f"Erro ao criar agendamento via chatbot: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao criar agendamento: {str(e)}"
        )