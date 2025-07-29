# chatbot/flows/flow_manager.py
import json
import logging
from pathlib import Path
from datetime import datetime
from dateutil.parser import parse, ParserError
from src.chatbot.core.data_extractor import ConsultationDataExtractor
from src.chatbot.data.medical_data import db

class FlowManager:
    def __init__(self, flow_file='booking_flow.json', model=None):
        flow_path = Path(__file__).parent / flow_file
        with open(flow_path, 'r', encoding='utf-8') as f:
            self.flow = json.load(f)
        self.user_conversations = {}
        self.data_extractor = ConsultationDataExtractor()
        
        logging.info("✅ FlowManager inicializado com validação local de datas")

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
        message = self.flow['states'][initial_state_key]['message']
        return self._get_current_state_response(user_id, message)

    def _handle_user_question(self, user_id: str, current_state_info: dict) -> dict:
        """Gera uma resposta quando o usuário faz uma pergunta sobre as opções."""
        target_field = current_state_info.get("extract", "") # CORREÇÃO: Garante que target_field seja sempre uma string

        if "especialidade" in target_field:
            specialties = ", ".join(db.get_specialties())
            message = f"As especialidades disponíveis são: {specialties}. Qual delas você gostaria?"
        else:
            message = "Não tenho uma lista de opções para esta pergunta. Por favor, me informe o que você precisa."
        
        return self._get_current_state_response(user_id, message)

    def process_user_response(self, user_id: str, user_message: str) -> dict:
        """Processa a resposta e retorna um dicionário completo com o novo estado."""
        if user_id not in self.user_conversations:
            initial_state_key = self.flow['initial_state']
            initial_state_info = self.flow['states'][initial_state_key]

            for keyword, next_state_key in initial_state_info['transitions'].items():
                if keyword in user_message.lower():
                    self.user_conversations[user_id] = {
                        'current_state': next_state_key,
                        'data': {}
                    }
                    # CORREÇÃO: Usa a função _save_data para garantir a consistência da estrutura
                    self._save_data(user_id, initial_state_info.get('extract'), keyword)
                    
                    next_state_info = self.flow['states'][next_state_key]
                    return self._get_current_state_response(user_id, next_state_info['message'])
            
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
        valid_options = db.get_specialties() if target_field_key == "especialidade" else None

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
        logging.info(f"Próximo estado definido no JSON: '{next_state}'")  # VERIFIQUE SE APARECE O NOME CORRETO AQUI
        
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
            if next_state == 'CONFIRMATION':
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
        especialidade_ou_exame = "Especialidade" if agendamento.get('especialidade') else "Exame"
        especialidade_valor = agendamento.get('especialidade', '') or agendamento.get('nome_exame', '')
        
        # Valores de formatação - usando underscore em vez de pontos
        format_values = {
            'paciente_nome': paciente.get('nome', 'Não informado'),
            'paciente_cpf': paciente.get('cpf', 'Não informado'),
            'paciente_data_nascimento': paciente.get('data_nascimento', 'Não informado'),
            'paciente_sexo': paciente.get('sexo', 'Não informado'),
            'contato_telefone': contato.get('telefone', 'Não informado'),
            'contato_email': contato.get('email', 'Não informado'),
            'agendamento_info_tipo': agendamento.get('tipo', 'Não informado'),
            'especialidade_ou_exame': especialidade_ou_exame,
            'agendamento_info_especialidade': especialidade_valor,
            'agendamento_info_nome_exame': '',  # Usado apenas quando é exame
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