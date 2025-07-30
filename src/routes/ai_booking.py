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


@router.get("/exames")
async def get_available_exams(db: aiosqlite.Connection = Depends(get_db)):
    """
    Retorna todos os exames disponíveis no banco de dados.
    """
    try:
        async with db.execute("SELECT id_exame, nome, instrucoes_preparo, duracao_padrao_minutos FROM Exames ORDER BY nome") as cursor:
            exams = await cursor.fetchall()
            
        exams_list = []
        for exam in exams:
            exams_list.append({
                "id": exam[0],
                "nome": exam[1],
                "instrucoes_preparo": exam[2],
                "duracao_minutos": exam[3]
            })
            
        return {
            "success": True,
            "exames": exams_list,
            "total": len(exams_list)
        }
        
    except Exception as e:
        logging.error(f"Erro ao buscar exames: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar exames")


@router.get("/locais")
async def get_available_locations(db: aiosqlite.Connection = Depends(get_db)):
    """
    Retorna todos os locais de atendimento disponíveis no banco de dados.
    """
    try:
        async with db.execute("SELECT id_local, nome, endereco FROM Locais_Atendimento ORDER BY nome") as cursor:
            locations = await cursor.fetchall()
            
        locations_list = []
        for location in locations:
            locations_list.append({
                "id": location[0],
                "nome": location[1],
                "endereco": location[2]
            })
            
        return {
            "success": True,
            "locais": locations_list,
            "total": len(locations_list)
        }
        
    except Exception as e:
        logging.error(f"Erro ao buscar locais: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar locais")


@router.get("/exames/{exame_id}/locais")
async def get_locations_for_exam(exame_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """
    Retorna os locais onde um exame específico pode ser realizado.
    """
    try:
        query = """
        SELECT l.id_local, l.nome, l.endereco, e.nome as exame_nome
        FROM Locais_Atendimento l
        JOIN Local_Exames le ON l.id_local = le.id_local
        JOIN Exames e ON le.id_exame = e.id_exame
        WHERE e.id_exame = ?
        ORDER BY l.nome
        """
        
        async with db.execute(query, (exame_id,)) as cursor:
            results = await cursor.fetchall()
            
        if not results:
            return {
                "success": False,
                "message": "Exame não encontrado ou não disponível em nenhum local",
                "locais": []
            }
        
        locations_list = []
        exame_nome = results[0][3]  # Nome do exame do primeiro resultado
        
        for result in results:
            locations_list.append({
                "id": result[0],
                "nome": result[1],
                "endereco": result[2]
            })
            
        return {
            "success": True,
            "exame_nome": exame_nome,
            "exame_id": exame_id,
            "locais": locations_list,
            "total": len(locations_list)
        }
        
    except Exception as e:
        logging.error(f"Erro ao buscar locais para exame {exame_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar locais para o exame")


@router.get("/locais/{local_id}/exames")
async def get_exams_for_location(local_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """
    Retorna os exames que podem ser realizados em um local específico.
    """
    try:
        query = """
        SELECT e.id_exame, e.nome, e.instrucoes_preparo, e.duracao_padrao_minutos, l.nome as local_nome
        FROM Exames e
        JOIN Local_Exames le ON e.id_exame = le.id_exame
        JOIN Locais_Atendimento l ON le.id_local = l.id_local
        WHERE l.id_local = ?
        ORDER BY e.nome
        """
        
        async with db.execute(query, (local_id,)) as cursor:
            results = await cursor.fetchall()
            
        if not results:
            return {
                "success": False,
                "message": "Local não encontrado ou não oferece exames",
                "exames": []
            }
        
        exams_list = []
        local_nome = results[0][4]  # Nome do local do primeiro resultado
        
        for result in results:
            exams_list.append({
                "id": result[0],
                "nome": result[1],
                "instrucoes_preparo": result[2],
                "duracao_minutos": result[3]
            })
            
        return {
            "success": True,
            "local_nome": local_nome,
            "local_id": local_id,
            "exames": exams_list,
            "total": len(exams_list)
        }
        
    except Exception as e:
        logging.error(f"Erro ao buscar exames para local {local_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar exames para o local")


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


@router.get("/sugestoes-inteligentes")
async def get_intelligent_suggestions(
        exame_nome: str = None,
        local_preferencia: str = None,
        db: aiosqlite.Connection = Depends(get_db)
):
    """
    Fornece sugestões inteligentes baseadas nos dados do banco.
    Se um exame for informado, sugere locais onde pode ser feito.
    Se um local for informado, sugere exames disponíveis.
    """
    try:
        suggestions = {
            "success": True,
            "exames_sugeridos": [],
            "locais_sugeridos": [],
            "informacoes_adicionais": {}
        }
        
        # Se um exame foi informado, busca locais onde pode ser feito
        if exame_nome:
            # Busca exame por nome (busca flexível)
            exame_query = """
            SELECT id_exame, nome, instrucoes_preparo, duracao_padrao_minutos 
            FROM Exames 
            WHERE LOWER(nome) LIKE LOWER(?) 
            ORDER BY nome
            LIMIT 5
            """
            
            async with db.execute(exame_query, (f"%{exame_nome}%",)) as cursor:
                exames = await cursor.fetchall()
                
            if exames:
                # Para cada exame encontrado, busca os locais
                for exame in exames:
                    exame_id = exame[0]
                    
                    locais_query = """
                    SELECT l.id_local, l.nome, l.endereco
                    FROM Locais_Atendimento l
                    JOIN Local_Exames le ON l.id_local = le.id_local
                    WHERE le.id_exame = ?
                    ORDER BY l.nome
                    """
                    
                    async with db.execute(locais_query, (exame_id,)) as cursor:
                        locais = await cursor.fetchall()
                    
                    locais_list = []
                    for local in locais:
                        locais_list.append({
                            "id": local[0],
                            "nome": local[1],
                            "endereco": local[2]
                        })
                    
                    suggestions["exames_sugeridos"].append({
                        "id": exame[0],
                        "nome": exame[1],
                        "instrucoes_preparo": exame[2],
                        "duracao_minutos": exame[3],
                        "locais_disponiveis": locais_list
                    })
                    
                    suggestions["informacoes_adicionais"]["exame_encontrado"] = True
        
        # Se um local foi informado, busca exames disponíveis
        if local_preferencia:
            local_query = """
            SELECT id_local, nome, endereco 
            FROM Locais_Atendimento 
            WHERE LOWER(nome) LIKE LOWER(?) 
            ORDER BY nome
            LIMIT 3
            """
            
            async with db.execute(local_query, (f"%{local_preferencia}%",)) as cursor:
                locais = await cursor.fetchall()
                
            if locais:
                # Para cada local encontrado, busca os exames
                for local in locais:
                    local_id = local[0]
                    
                    exames_query = """
                    SELECT e.id_exame, e.nome, e.instrucoes_preparo, e.duracao_padrao_minutos
                    FROM Exames e
                    JOIN Local_Exames le ON e.id_exame = le.id_exame
                    WHERE le.id_local = ?
                    ORDER BY e.nome
                    """
                    
                    async with db.execute(exames_query, (local_id,)) as cursor:
                        exames = await cursor.fetchall()
                    
                    exames_list = []
                    for exame in exames:
                        exames_list.append({
                            "id": exame[0],
                            "nome": exame[1],
                            "instrucoes_preparo": exame[2],
                            "duracao_minutos": exame[3]
                        })
                    
                    suggestions["locais_sugeridos"].append({
                        "id": local[0],
                        "nome": local[1],
                        "endereco": local[2],
                        "exames_disponiveis": exames_list
                    })
                    
                    suggestions["informacoes_adicionais"]["local_encontrado"] = True
        
        # Se nenhum parâmetro foi informado, retorna sugestões gerais
        if not exame_nome and not local_preferencia:
            # Busca os 5 exames mais comuns (por simplicidade, vamos pegar os primeiros)
            async with db.execute("SELECT id_exame, nome FROM Exames ORDER BY nome LIMIT 5") as cursor:
                exames_comuns = await cursor.fetchall()
                
            # Busca todos os locais
            async with db.execute("SELECT id_local, nome, endereco FROM Locais_Atendimento ORDER BY nome") as cursor:
                todos_locais = await cursor.fetchall()
            
            suggestions["exames_sugeridos"] = [
                {"id": exame[0], "nome": exame[1]} for exame in exames_comuns
            ]
            
            suggestions["locais_sugeridos"] = [
                {"id": local[0], "nome": local[1], "endereco": local[2]} 
                for local in todos_locais
            ]
            
            suggestions["informacoes_adicionais"]["sugestoes_gerais"] = True
        
        return suggestions
        
    except Exception as e:
        logging.error(f"Erro ao buscar sugestões inteligentes: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar sugestões")


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

        # Para consultas: seleciona médico baseado na especialidade
        # Para exames: busca o exame pelo nome
        especialidade_solicitada = agendamento_data.get("especialidade", "")
        nome_exame_solicitado = agendamento_data.get("nome_exame", "")
        selected_doctor_id = None
        selected_doctor_name = "Aguardando confirmação"
        selected_exam_id = None
        
        if agendamento_data.get("tipo") == "consulta" and especialidade_solicitada:
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
                
        elif agendamento_data.get("tipo") == "exame" and nome_exame_solicitado:
            try:
                # Busca o exame pelo nome (busca mais flexível)
                query = "SELECT id_exame, nome FROM Exames WHERE LOWER(nome) LIKE LOWER(?) LIMIT 1"
                
                async with db.execute(query, (f"%{nome_exame_solicitado}%",)) as cursor:
                    exam_row = await cursor.fetchone()
                    if exam_row:
                        selected_exam_id = exam_row[0]
                        logging.info(f"Exame selecionado: {exam_row[1]} (ID: {selected_exam_id})")
                    else:
                        # Tenta busca ainda mais flexível, palavra por palavra
                        words = nome_exame_solicitado.lower().split()
                        for word in words:
                            if len(word) > 2:  # Ignora palavras muito pequenas
                                query = "SELECT id_exame, nome FROM Exames WHERE LOWER(nome) LIKE LOWER(?) LIMIT 1"
                                async with db.execute(query, (f"%{word}%",)) as cursor:
                                    exam_row = await cursor.fetchone()
                                    if exam_row:
                                        selected_exam_id = exam_row[0]
                                        logging.info(f"Exame encontrado por palavra-chave '{word}': {exam_row[1]} (ID: {selected_exam_id})")
                                        break
                        
                        if not selected_exam_id:
                            logging.warning(f"Nenhum exame encontrado com o nome: {nome_exame_solicitado}")
                            # Se não encontrar, usa o primeiro exame disponível como fallback
                            selected_exam_id = 1
                        
            except Exception as e:
                logging.error(f"Erro ao buscar exame: {e}")
                selected_exam_id = 1

        # Cria o agendamento diretamente no banco sem usar o schema problemático
        cursor = await db.execute(
            """
            INSERT INTO Agendamentos (id_paciente, id_local, id_convenio, id_tipo_consulta, id_exame, id_medico, 
                                      data_hora_inicio, data_hora_fim, status, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (patient_id, 1, None, 
             1 if agendamento_data.get("tipo") == "consulta" else None,
             selected_exam_id if agendamento_data.get("tipo") == "exame" else None, 
             selected_doctor_id,
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

        # Determina a especialidade ou exame e o nome do médico baseado no tipo
        if agendamento_data.get("tipo") == "consulta":
            especialidade_valor = agendamento_data.get("especialidade") or "Não informado"
            medico_display = selected_doctor_name
        else:  # exame
            especialidade_valor = agendamento_data.get("nome_exame") or "Não informado"
            medico_display = "Não aplicável (Exame)"

        return {
            "success": True,
            "message": "Agendamento criado com sucesso!",
            "appointment_data": {
                "id_agendamento": appointment_id,
                "nome_paciente": paciente_data.get("nome", "Não informado"),
                "nome_medico": medico_display,
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