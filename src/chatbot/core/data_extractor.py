"""
Extrator de dados para agendamento de consultas usando API do Gemini
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import google.generativeai as genai


load_dotenv()
logger = logging.getLogger(__name__)

class ConsultationDataExtractor:
    """Extrai dados necessários para agendamento de consultas usando Gemini"""
    
    def __init__(self):
        """Inicializa o extrator com configurações do Gemini"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no arquivo .env")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Template para extração de dados
        self.extraction_prompt = """
        Você é um assistente médico especializado em extrair informações para agendamento de consultas.
        
        Analise a mensagem do paciente e extraia APENAS as informações fornecidas explicitamente.
        Não invente ou suponha dados que não foram mencionados.
        
        RESPONDA APENAS EM FORMATO JSON VÁLIDO, exatamente como mostrado abaixo:

        {{
          "paciente": {{
            "nome": "nome completo ou null",
            "cpf": "apenas números ou null",
            "data_nascimento": "DD/MM/AAAA ou null",
            "sexo": "M, F, O ou null"
          }},
          "agendamento_info": {{
            "tipo_agendamento": "consulta, exame ou null",
            "tipo_consulta": "Primeira Consulta, Retorno, Telemedicina ou null",
            "nome_exame": "nome do exame ou null",
            "especialidade": "especialidade médica ou null",
            "tem_convenio": true, false ou null,
            "nome_convenio": "nome do convênio ou null"
          }},
          "preferencias": {{
            "data_preferencia": "DD/MM/AAAA ou null",
            "horario_preferencia": "HH:MM ou null",
            "periodo_preferencia": "manha, tarde, noite ou null",
            "local_preferencia": "local desejado ou null",
            "observacoes": "sintomas e observações ou null"
          }}
        }}

        Mensagem do paciente: "{mensagem}"
        """

    def analyze_user_response(self, chatbot_question: str, user_message: str, target_field: str,
                              valid_options: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analisa a resposta do usuário para uma pergunta do chatbot e extrai informações úteis.

        Etapas:
        - Verifica cache para evitar recomputação
        - Tenta processar localmente para casos simples
        - Se necessário, usa IA com prompt otimizado
        - Retorna dicionário com: intent, is_valid, extracted_value e error_message
        """

        # 🔍 1. Verificação de cache
        cache_key = self._generate_cache_key(user_message, target_field, valid_options)
        if cache_key in self._cache:
            self._cache_hits += 1
            logging.info(f"✅ Cache HIT para '{user_message}' (hits: {self._cache_hits})")
            return self._cache[cache_key]

        # ⚡ 2. Tentativa de processamento local (mais rápido e econômico)
        local_result = self._try_local_processing(user_message, target_field, valid_options)
        if local_result:
            logging.info(f"⚡ Processamento LOCAL para '{user_message}'")
            self._cache[cache_key] = local_result
            return local_result

        # ⚠️ 3. Verificação de modelo IA
        if not self.model:
            logging.error("❌ Modelo da IA não foi configurado corretamente.")
            result = self._error_result(user_message, "Modelo da IA não configurado.")
            self._cache[cache_key] = result
            return result

        # 🧠 4. Criação do prompt dinâmico
        validation_text = f"Opções válidas: {valid_options}" if valid_options else "Sem validação específica"
        prompt = f"""Analise rapidamente:
    Pergunta: "{chatbot_question}"
    Resposta: "{user_message}"
    Campo: {target_field}
    {validation_text}

    Retorne JSON:
    - "intent": "PROVIDE_INFO" ou "ASK_QUESTION"
    - "is_valid": true/false
    - "extracted_value": valor principal ou null
    - "error_message": mensagem de erro ou null

    JSON:"""

        try:
            self._api_calls += 1
            logging.info(f"🔄 API call #{self._api_calls} para '{user_message[:30]}...'")

            # ⚙️ 5. Configurações para resposta mais rápida e previsível
            generation_config = {
                "temperature": 0.1,
                "max_output_tokens": 200,
                "top_p": 0.8,
                "top_k": 10
            }

            response = self.model.generate_content(prompt, generation_config=generation_config)
            raw_response_text = response.text.strip()
            logging.info(f"✅ IA respondeu ({len(raw_response_text)} chars)")

            # 🧹 6. Limpeza do texto retornado
            clean_response = (
                raw_response_text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            analysis = json.loads(clean_response)

            # 💾 7. Armazena no cache
            self._cache[cache_key] = analysis
            logging.info(f"💾 Resultado salvo no cache (total: {len(self._cache)} entradas)")
            return analysis

        except json.JSONDecodeError as e:
            logging.error(f"❌ JSON inválido: {e}")
            result = self._error_result(user_message, "Erro de processamento.")
            self._cache[cache_key] = result
            return result

        except Exception as e:
            logging.error(f"❌ Erro na IA: {e}")
            result = self._error_result(user_message, "Erro de comunicação.")
            self._cache[cache_key] = result
            return result

    def _error_result(self, user_message: str, msg: str) -> Dict[str, Any]:
        """Gera resposta padrão de erro para falhas de processamento ou IA"""
        return {
            "intent": "PROVIDE_INFO",
            "is_valid": False,
            "extracted_value": user_message,
            "error_message": msg
        }

    def extract_consultation_data(self, message: str) -> Dict[str, Any]:
        """
        Extrai dados de consulta da mensagem do paciente
        
        Args:
            message: Mensagem do paciente
            
        Returns:
            Dict com dados extraídos estruturados
        """
        try:
            # Preparar prompt com a mensagem
            prompt = self.extraction_prompt.format(mensagem=message)
            
            # Gerar resposta
            response = self.model.generate_content(prompt)
            
            # Parsear JSON da resposta
            data = self._parse_json_response(response.text)
            
            # Processar e validar dados extraídos
            processed_data = self._process_extracted_data(data)
            
            logger.info(f"Dados extraídos: {len(processed_data['dados_extraidos'])} campos")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados: {e}")
            return self._get_empty_response()
    
    def generate_missing_data_questions(self, extracted_data: Dict[str, Any]) -> str:
        """
        Gera perguntas para completar dados faltantes (pode perguntar mais de um campo por vez)
        Sempre inclui o CPF se estiver faltando.
        """
        try:
            if not extracted_data or not isinstance(extracted_data, dict):
                extracted_data = self._get_empty_response()
            for section in ['paciente', 'agendamento_info', 'preferencias']:
                if section not in extracted_data or not isinstance(extracted_data[section], dict):
                    extracted_data[section] = {}
            missing_fields = extracted_data.get('dados_faltantes', [])
            if not missing_fields:
                return "Perfeito! Tenho todas as informações necessárias para o agendamento."
            perguntas = []
            # Mapeamento para nomes amigáveis
            nomes_amigaveis = {
                'paciente.nome': 'Nome completo do paciente',
                'paciente.cpf': 'CPF do paciente (apenas números, 11 dígitos)',
                'agendamento.tipo_agendamento': 'Tipo de agendamento (consulta ou exame)',
                'agendamento.especialidade': 'Especialidade médica desejada',
                'paciente.data_nascimento': 'Data de nascimento do paciente (DD/MM/AAAA)',
                'paciente.sexo': 'Sexo do paciente (M/F/O)',
                'agendamento.tem_convenio': 'Possui convênio médico? (Sim/Não)',
                'preferencias.data_preferencia': 'Data preferencial para o agendamento',
                'preferencias.observacoes': 'Observações ou sintomas'
            }
            # Perguntas principais
            for campo in ['paciente.nome','paciente.cpf','agendamento.tipo_agendamento','agendamento.especialidade']:
                if campo in missing_fields:
                    perguntas.append(f'<b>{nomes_amigaveis[campo]}</b>')
            # Extras formatados em lista
            extras = [campo for campo in missing_fields if campo not in ['paciente.nome','paciente.cpf','agendamento.tipo_agendamento','agendamento.especialidade']]
            if extras:
                perguntas.append('<b>Outros dados:</b><ul>' + ''.join(f'<li>{nomes_amigaveis.get(campo, campo.replace(".", " "))}</li>' for campo in extras) + '</ul>')
            return (
                'Por favor, informe os seguintes dados para prosseguir com o agendamento:<br>' +
                '<ul>' + ''.join(f'<li>{p}</li>' for p in perguntas) + '</ul>'
            )
        except Exception as e:
            logger.error(f"Erro ao gerar perguntas para dados faltantes: {e}\nDados extraídos: {extracted_data}")
            return "Desculpe, ocorreu um erro ao gerar a próxima pergunta. Por favor, tente novamente."

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse da resposta JSON do Gemini"""
        try:
            # Limpar resposta (remover markdown se houver)
            clean_response = response_text.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            return json.loads(clean_response.strip())
        
        except Exception as e:
            logger.error(f"Erro ao fazer parse do JSON da resposta do Gemini: {e}\nResposta recebida: {response_text}")
            # Retorna resposta vazia para evitar erro 500
            return self._get_empty_response()

    def _process_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa e valida os dados extraídos"""
        dados_extraidos = []
        dados_faltantes = []
        # Verificar dados do paciente
        paciente = data.get('paciente', {})
        for campo in ['nome', 'cpf', 'data_nascimento', 'sexo']:
            valor = paciente.get(campo)
            if isinstance(valor, str) and valor.strip() == '':
                paciente[campo] = None
            if paciente.get(campo):
                dados_extraidos.append(f"paciente.{campo}")
            else:
                dados_faltantes.append(f"paciente.{campo}")
        # Verificar dados do agendamento
        agendamento_info = data.get('agendamento_info', {})
        for campo in ['tipo_agendamento', 'especialidade', 'tem_convenio']:
            valor = agendamento_info.get(campo)
            if isinstance(valor, str) and valor.strip() == '':
                agendamento_info[campo] = None
            if agendamento_info.get(campo) is not None:
                dados_extraidos.append(f"agendamento.{campo}")
            else:
                dados_faltantes.append(f"agendamento.{campo}")
        # Verificar preferências
        preferencias = data.get('preferencias', {})
        for campo in ['data_preferencia', 'observacoes']:
            valor = preferencias.get(campo)
            if isinstance(valor, str) and valor.strip() == '':
                preferencias[campo] = None
            if preferencias.get(campo):
                dados_extraidos.append(f"preferencias.{campo}")
            else:
                dados_faltantes.append(f"preferencias.{campo}")
        # Atualizar listas no resultado
        data['dados_extraidos'] = dados_extraidos
        data['dados_faltantes'] = dados_faltantes
        return data
    
    def _get_empty_response(self) -> Dict[str, Any]:
        """Retorna resposta vazia em caso de erro"""
        return {
            "paciente": {
                "nome": None,
                "cpf": None,
                "data_nascimento": None,
                "sexo": None
            },
            "agendamento_info": {
                "tipo_agendamento": None,
                "tipo_consulta": None,
                "nome_exame": None,
                "especialidade": None,
                "tem_convenio": None,
                "nome_convenio": None
            },
            "preferencias": {
                "data_preferencia": None,
                "horario_preferencia": None,
                "periodo_preferencia": None,
                "local_preferencia": None,
                "observacoes": None
            },
            "dados_extraidos": [],
            "dados_faltantes": [
                "paciente.nome", "paciente.cpf", "agendamento.tipo_agendamento",
                "agendamento.especialidade", "preferencias.data_preferencia"
            ]
        }
    
    def validate_essential_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida se os dados essenciais foram coletados
        
        Args:
            extracted_data: Dados extraídos
            
        Returns:
            Dict com status de validação
        """
        essential_fields = [
            "paciente.nome",
            "agendamento.tipo_agendamento", 
            "agendamento.especialidade"
        ]
        
        missing_essential = []
        for field in essential_fields:
            if field not in extracted_data.get('dados_extraidos', []):
                missing_essential.append(field)
        
        return {
            "is_valid": len(missing_essential) == 0,
            "missing_essential": missing_essential,
            "can_proceed": len(missing_essential) <= 1,  # Pode prosseguir se faltar apenas 1 campo essencial
            "completion_percentage": (len(essential_fields) - len(missing_essential)) / len(essential_fields) * 100
        }

    def merge_extracted_data(self, previous: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mescla os dados já coletados com os novos dados extraídos da mensagem atual.
        Sempre prioriza valores não nulos do novo dado.
        """
        result = previous.copy() if previous else {}
        for section in ['paciente', 'agendamento_info', 'preferencias']:
            if section not in result or not isinstance(result[section], dict):
                result[section] = {}
            for key, value in new.get(section, {}).items():
                if value not in [None, '', []]:
                    result[section][key] = value
                elif key not in result[section]:
                    result[section][key] = None
        # Atualiza listas de extraídos/faltantes
        return self._process_extracted_data(result)
