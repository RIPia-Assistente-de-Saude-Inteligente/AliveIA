# chatbot/flows/flow_manager.py
import json
import logging
from pathlib import Path
from datetime import datetime
from dateutil.parser import parse, ParserError
from src.chatbot.core.data_extractor import ConsultationDataExtractor
import sqlite3
import aiosqlite

class FlowManager:
    def __init__(self, flow_file='booking_flow.json', model=None):
        flow_path = Path(__file__).parent / flow_file
        with open(flow_path, 'r', encoding='utf-8') as f:
            self.flow = json.load(f)
        self.user_conversations = {}
        self.data_extractor = ConsultationDataExtractor()
        self.db_path = 'src/database/medical_system.db'
        
        logging.info("✅ FlowManager inicializado com validação local de datas")

    def get_specialties(self) -> list[str]:
        """Busca especialidades diretamente do banco de dados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT nome FROM Especialidades ORDER BY nome")
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar especialidades: {e}")
            return ["Cardiologia", "Dermatologia", "Ortopedia", "Ginecologia", "Pediatria", "Neurologia"]

    def get_exams(self) -> list[str]:
        """Busca exames diretamente do banco de dados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT nome FROM Exames ORDER BY nome")
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar exames: {e}")
            return ["Hemograma Completo", "Raio-X Tórax", "Ultrassonografia Abdominal", "Eletrocardiograma"]

    def get_locations_by_specialty(self, specialty_name: str) -> list[dict]:
        """Busca locais por especialidade diretamente do banco de dados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Busca locais através dos médicos que atendem a especialidade
                query = """
                SELECT DISTINCT l.id_local, l.nome, l.endereco 
                FROM Locais_Atendimento l
                JOIN Medico_Especialidades me ON 1=1
                JOIN Especialidades e ON me.id_especialidade = e.id_especialidade
                WHERE LOWER(e.nome) = LOWER(?)
                ORDER BY l.nome
                """
                cursor = conn.execute(query, (specialty_name,))
                rows = cursor.fetchall()
                locations = [{"id": row[0], "nome": row[1], "endereco": row[2]} for row in rows]
                
                # Se não encontrar, retorna todos os locais
                if not locations:
                    locations = self.get_all_locations()
                    
                return locations
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar locais por especialidade: {e}")
            return self.get_all_locations()

    def get_locations_for_exam(self, exam_name: str) -> list[dict]:
        """Busca locais por exame diretamente do banco de dados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                SELECT l.id_local, l.nome, l.endereco
                FROM Locais_Atendimento l
                JOIN Local_Exames le ON l.id_local = le.id_local
                JOIN Exames e ON le.id_exame = e.id_exame
                WHERE LOWER(e.nome) LIKE LOWER(?)
                ORDER BY l.nome
                """
                cursor = conn.execute(query, (f"%{exam_name}%",))
                rows = cursor.fetchall()
                locations = [{"id": row[0], "nome": row[1], "endereco": row[2]} for row in rows]
                
                # Se não encontrar locais específicos, retorna todos os locais
                if not locations:
                    return self.get_all_locations()
                    
                return locations
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar locais por exame: {e}")
            return self.get_all_locations()

    def get_all_locations(self) -> list[dict]:
        """Busca todos os locais de atendimento do banco de dados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT id_local, nome, endereco FROM Locais_Atendimento ORDER BY nome")
                rows = cursor.fetchall()
                return [{"id": row[0], "nome": row[1], "endereco": row[2]} for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar todos os locais: {e}")
            return []

    def validar_data_agendamento_local(self, entrada_usuario: str) -> dict:
        """
        Valida a data do usuário com lógica local, simples e correta.
        Retorna um dicionário com o status e o resultado.
        """
        hoje = datetime.now()
        
        try:
            # 1. Tenta converter a entrada do usuário em um objeto de data.
            #    dayfirst=True ajuda a entender formatos como DD/MM/AAAA.
            data_agendamento = parse(entrada_usuario, dayfirst=True)

            # 2. Lógica de Validação CORRETA:
            #    a. Rejeita se a data for no passado.
            if data_agendamento.date() < hoje.date():
                return {
                    "valido": False,
                    "mensagem_erro": "Não é possível agendar para uma data no passado. Por favor, escolha uma data futura."
                }

            #    b. Rejeita se a data for mais de 1 ano no futuro (365 dias).
            if (data_agendamento.date() - hoje.date()).days > 365:
                return {
                    "valido": False,
                    "mensagem_erro": "Agendamentos só podem ser feitos para os próximos 365 dias."
                }

            # 3. Se passou em todas as validações, a data é válida.
            return {
                "valido": True,
                "data_formatada": data_agendamento.strftime('%Y-%m-%d')
            }

        except ParserError:
            # Se a biblioteca não conseguiu entender o formato da data.
            return {
                "valido": False,
                "mensagem_erro": f"Não consegui entender '{entrada_usuario}' como uma data. Por favor, use um formato claro como DD/MM/AAAA."
            }

    def _save_data(self, user_id: str, data_key: str, value: any):
        """Salva um dado na estrutura aninhada da conversa do usuário."""
        if not data_key:
            return
            
        keys = data_key.split('.')
        d = self.user_conversations[user_id]['data']
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    def _get_current_state_response(self, user_id: str, message: str) -> dict:
        """Constrói o dicionário de resposta padrão com o estado atualizado."""
        state = self.user_conversations.get(user_id, {})
        return {
            "next_question": message,
            "conversation_data": state.get('data', {}),
            "current_state": state.get('current_state', 'GREETING')
        }

    def get_initial_message(self, user_id: str) -> dict:
        """Inicia uma nova conversa e retorna o estado inicial completo."""
        initial_state_key = self.flow['initial_state']
        self.user_conversations[user_id] = {
            'current_state': initial_state_key,
            'data': {}
        }
        
        # Para o estado inicial, apenas retorna a mensagem sem modificações
        initial_state_info = self.flow['states'][initial_state_key]
        message = initial_state_info['message']
        
        return self._get_current_state_response(user_id, message)

    def _handle_user_question(self, user_id: str, current_state_info: dict) -> dict:
        """Gera uma resposta quando o usuário faz uma pergunta sobre as opções."""
        target_field = current_state_info.get("extract", "")
        current_state = self.user_conversations[user_id]['current_state']

        if "especialidade" in target_field:
            try:
                specialties = self.get_specialties()
                specialty_list = ", ".join(specialties)
                message = f"As especialidades disponíveis são: {specialty_list}. Qual delas você gostaria?"
            except Exception as e:
                logging.error(f"Erro ao buscar especialidades: {e}")
                message = "Houve um erro ao buscar as especialidades. Por favor, me informe qual especialidade você precisa."
        elif "local" in target_field:
            # Para o estado de local, mostra TODOS os locais do banco de dados
            try:
                locations = self.get_all_locations()
                if locations:
                    location_list = ", ".join([loc['nome'] for loc in locations])
                    message = f"Os locais disponíveis são: {location_list}. Qual você escolhe?"
                else:
                    message = "Não encontrei locais disponíveis. Por favor, me informe um local de sua preferência."
            except Exception as e:
                logging.error(f"Erro ao buscar locais: {e}")
                message = "Houve um erro ao buscar os locais. Por favor, me informe qual local você prefere."
        else:
            message = "Não tenho uma lista de opções para esta pergunta. Por favor, me informe o que você precisa."
        
        return self._get_current_state_response(user_id, message)

    def process_user_response(self, user_id: str, user_message: str) -> dict:
        """Processa a resposta e retorna um dicionário completo com o novo estado."""
        if user_id not in self.user_conversations:
            return self.get_initial_message(user_id)

        conversation = self.user_conversations[user_id]
        current_state_key = conversation['current_state']
        current_state_info = self.flow['states'][current_state_key]

        logging.info(f"--- INÍCIO DA DEPURAÇÃO ---")
        logging.info(f"Estado Atual Recebido: '{current_state_key}'")
        logging.info(f"Processando a mensagem do usuário: '{user_message}'")

        # --- INÍCIO DA IMPLEMENTAÇÃO OBRIGATÓRIA ---
        # Verificação especial para o estado de data, ANTES de qualquer outra coisa.
        if current_state_key == 'GET_PREFERRED_DATE':
            # Chama a função de validação LOCAL que foi fornecida anteriormente.
            resultado_validacao = self.validar_data_agendamento_local(user_message)

            if resultado_validacao["valido"]:
                # Se a data for válida, salve-a e avance para o próximo estado.
                self._save_data(user_id, "preferencias.data_preferencia", resultado_validacao["data_formatada"])
                
                # Lógica para encontrar o próximo estado
                current_state_info = self.flow['states'][current_state_key]
                next_state = current_state_info.get('next_state')  # Deve ser 'GET_PREFERRED_TIME'
                
                if next_state:
                    conversation['current_state'] = next_state
                    next_state_info = self.flow['states'][next_state]
                    return self._get_current_state_response(user_id, next_state_info['message'])
                else:
                    # ERRO NO ARQUIVO JSON DO FLUXO
                    return self._get_current_state_response(user_id, "Erro de configuração: próximo estado não definido.")

            else:
                # Se a data for INVÁLIDA, retorne a mensagem de erro e NÃO avance.
                return self._get_current_state_response(user_id, resultado_validacao["mensagem_erro"])

        # O resto do processamento, que inclui a chamada à IA, só deve ser executado
        # para os OUTROS estados. A lógica acima intercepta e resolve o estado da data.
        # --- FIM DA IMPLEMENTAÇÃO OBRIGATÓRIA ---

        target_field_key = current_state_info.get("extract", "none").split('.')[-1]
        
        # Define opções válidas baseadas no estado atual
        valid_options = None
        if target_field_key == "especialidade":
            try:
                valid_options = self.get_specialties()
            except Exception as e:
                logging.error(f"Erro ao buscar especialidades: {e}")
                valid_options = []
        elif target_field_key == "nome_exame":
            try:
                valid_options = self.get_exams()
            except Exception as e:
                logging.error(f"Erro ao buscar exames: {e}")
                valid_options = []
        elif target_field_key == "local":
            try:
                # Sempre mostra TODOS os locais do banco de dados
                locations = self.get_all_locations()
                valid_options = [loc['nome'] for loc in locations] if locations else []
            except Exception as e:
                logging.error(f"Erro ao buscar locais: {e}")
                valid_options = []

        analysis = self.data_extractor.analyze_user_response(
            chatbot_question=current_state_info['message'],
            user_message=user_message,
            target_field=target_field_key,
            valid_options=valid_options
        )

        if analysis['intent'] == 'ASK_QUESTION':
            return self._handle_user_question(user_id, current_state_info)

        if not analysis['is_valid']:
            error_message = analysis.get('error_message', "A informação fornecida não é válida.")
            return self._get_current_state_response(user_id, error_message)

        # Extrai o valor da análise (para todos os estados EXCETO data_preferencia)
        extracted_value = analysis['extracted_value']

        self._save_data(user_id, current_state_info.get('extract'), extracted_value)
        logging.info(f"Dados salvos. Conteúdo de conversation['data']: {conversation['data']}")

        # Lógica de transição - PONTO MAIS CRÍTICO
        next_state = current_state_info.get('next_state')
        logging.info(f"Próximo estado definido no JSON: '{next_state}'")
        
        if 'transitions' in current_state_info:
            logging.info(f"Transitions encontradas: {current_state_info['transitions']}")
            for keyword, state in current_state_info['transitions'].items():
                if keyword in user_message.lower():
                    next_state = state
                    logging.info(f"Keyword '{keyword}' encontrada! Redirecionando para estado: '{state}'")
                    break
        
        if next_state:
            conversation['current_state'] = next_state
            logging.info(f"TRANSIÇÃO APLICADA. Novo estado será: '{conversation['current_state']}'")
            next_state_info = self.flow['states'][next_state]
            
            message = next_state_info['message']
            
            # Personaliza mensagens baseadas no estado
            if next_state == 'GET_SPECIALTY':
                # Adiciona lista de especialidades disponíveis
                try:
                    specialties = self.get_specialties()
                    if specialties:
                        specialty_list = ", ".join(specialties)
                        message += f"\n\nEspecialidades disponíveis: {specialty_list}"
                except Exception as e:
                    logging.error(f"Erro ao buscar especialidades: {e}")
            elif next_state == 'GET_EXAM_TYPE':
                # Adiciona lista de exames disponíveis
                try:
                    exams = self.get_exams()
                    if exams:
                        exam_list = ", ".join(exams)
                        message += f"\n\nExames disponíveis: {exam_list}"
                except Exception as e:
                    logging.error(f"Erro ao buscar exames: {e}")
            elif next_state == 'GET_LOCATION':
                # Sempre mostra TODOS os locais do banco de dados
                try:
                    all_locations = self.get_all_locations()
                    if all_locations:
                        location_names = [loc['nome'] for loc in all_locations]
                        location_list = ", ".join(location_names)
                        message += f"\n\nLocais disponíveis: {location_list}"
                    else:
                        message += f"\n\nErro ao carregar locais do banco de dados."
                except Exception as e:
                    logging.error(f"Erro ao buscar locais: {e}")
                    message += f"\n\nErro ao carregar locais. Por favor, informe um local de sua preferência."
            elif next_state == 'CONFIRMATION':
                message = self._format_confirmation_message(user_id, message)
            elif next_state == 'END':
                message = self._format_end_message(user_id, message)
                # LOG CRÍTICO: Mostra dados quando usuário atinge estado END
                logging.info(f"🎯 USUÁRIO ATINGIU ESTADO END - DADOS COLETADOS: {conversation['data']}")

            logging.info(f"--- FIM DA DEPURAÇÃO ---")
            return self._get_current_state_response(user_id, message)
        else:
            logging.error("FALHA CRÍTICA: NENHUM 'next_state' FOI DETERMINADO. O FLUXO ESTÁ QUEBRADO.")
            logging.info(f"--- FIM DA DEPURAÇÃO ---")
        
        return self._get_current_state_response(user_id, "Desculpe, não entendi. Pode repetir?")

    def _format_confirmation_message(self, user_id: str, message_template: str) -> str:
        """Formata a mensagem de confirmação com todos os dados coletados."""
        data = self.user_conversations[user_id]['data']
        
        # Extrai dados aninhados com valores padrão
        paciente = data.get('paciente', {})
        contato = data.get('contato', {})
        agendamento = data.get('agendamento_info', {})
        preferencias = data.get('preferencias', {})
        
        # Determina se é especialidade ou exame
        tipo = agendamento.get('tipo', 'Não informado')
        if tipo.lower() == 'consulta':
            especialidade_ou_exame = "Especialidade"
            especialidade_valor = agendamento.get('especialidade', 'Não informado')
            nome_exame_valor = ''
        else:
            especialidade_ou_exame = "Exame"
            especialidade_valor = ''
            nome_exame_valor = agendamento.get('nome_exame', 'Não informado')
        
        # Valores de formatação - usando underscore em vez de pontos
        format_values = {
            'paciente_nome': paciente.get('nome', 'Não informado'),
            'paciente_cpf': paciente.get('cpf', 'Não informado'),
            'paciente_data_nascimento': paciente.get('data_nascimento', 'Não informado'),
            'paciente_sexo': paciente.get('sexo', 'Não informado'),
            'contato_telefone': contato.get('telefone', 'Não informado'),
            'contato_email': contato.get('email', 'Não informado'),
            'agendamento_info_tipo': tipo,
            'especialidade_ou_exame': especialidade_ou_exame,
            'agendamento_info_especialidade': especialidade_valor,
            'agendamento_info_nome_exame': nome_exame_valor,
            'agendamento_info_local': agendamento.get('local', 'Não informado'),
            'preferencias_data_preferencia': preferencias.get('data_preferencia', 'Não informado'),
            'preferencias_horario_preferencia': preferencias.get('horario_preferencia', 'Não informado'),
            'agendamento_info_convenio': agendamento.get('convenio', 'Não informado')
        }
        
        # Converte template para usar underscores
        template_fixed = message_template.replace('.', '_')
        
        try:
            return template_fixed.format(**format_values)
        except KeyError as e:
            logging.error(f"Erro ao formatar mensagem de confirmação: {e}")
            return "Erro ao gerar resumo dos dados. Vamos prosseguir com o agendamento?"

    def _format_end_message(self, user_id: str, message_template: str) -> str:
        """Formata a mensagem final com dados de contato."""
        data = self.user_conversations[user_id]['data']
        contato = data.get('contato', {})
        
        telefone = contato.get('telefone', 'seu telefone')
        email = contato.get('email', '')
        email_confirmation = f" e um email em {email}" if email and email.lower() not in ['não tenho', 'não', 'nenhum', 'não informado'] else ""
        
        format_values = {
            'contato_telefone': telefone,
            'email_confirmation': email_confirmation
        }
        
        # Converte template para usar underscores
        template_fixed = message_template.replace('.', '_')
        
        try:
            return template_fixed.format(**format_values)
        except KeyError as e:
            logging.error(f"Erro ao formatar mensagem final: {e}")
            return "Agendamento processado com sucesso! Obrigado por usar nosso sistema!"