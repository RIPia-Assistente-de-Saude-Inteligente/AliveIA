# src/chatbot/core/data_extractor.py

import os
import re
import json
import hashlib
import logging
import requests
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import google.generativeai as genai

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()


class ConsultationDataExtractor:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no arquivo .env")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        self._cache = {}
        self._cache_hits = 0
        self._api_calls = 0

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

    def call_llm(payload):
    try:
        response = requests.post(
            "https://api.llm.com/v1/query",
            json=payload,
            timeout=5  # 5 segundos
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return {"error": "timeout"}
    except requests.RequestException as e:
        return {"error": str(e)}
    
    def analyze_user_response(self, chatbot_question: str, user_message: str, target_field: str,
                              valid_options: Optional[List[str]] = None) -> Dict[str, Any]:

        cache_key = self._generate_cache_key(user_message, target_field, valid_options)
        if cache_key in self._cache:
            self._cache_hits += 1
            logging.info(f"✅ Cache HIT para '{user_message}' (hits: {self._cache_hits})")
            return self._cache[cache_key]

        local_result = self._try_local_processing(user_message, target_field, valid_options)
        if local_result:
            logging.info(f"⚡ Processamento LOCAL para '{user_message}'")
            self._cache[cache_key] = local_result
            return local_result

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

            generation_config = {
                "temperature": 0.1,
                "max_output_tokens": 200,
                "top_p": 0.8,
                "top_k": 10
            }

            response = self.model.generate_content(prompt, generation_config=generation_config)
            raw_response_text = response.text.strip()

            clean_response = raw_response_text.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(clean_response)

            self._cache[cache_key] = analysis
            logging.info(f"💾 Resultado salvo no cache (total: {len(self._cache)} entradas)")
            return analysis

        except json.JSONDecodeError as e:
            logging.error(f"JSON inválido: {e}")
            return self._error_result(user_message, "Erro de processamento.")
        except Exception as e:
            logging.error(f"Erro na IA: {e}")
            return self._error_result(user_message, "Erro de comunicação.")

    def _try_local_processing(self, user_message: str, target_field: str, valid_options: Optional[List[str]]) -> Optional[Dict[str, Any]]:
        message_lower = user_message.lower().strip()

        if any(q in message_lower for q in ['que', 'qual', 'quando', 'como', 'onde', 'opções', '?']):
            return {"intent": "ASK_QUESTION", "is_valid": True, "extracted_value": None, "error_message": None}

        if target_field == "cpf":
            cpf_digits = re.sub(r'\D', '', user_message)
            if len(cpf_digits) == 11:
                return {"intent": "PROVIDE_INFO", "is_valid": True, "extracted_value": cpf_digits, "error_message": None}
            else:
                return {"intent": "PROVIDE_INFO", "is_valid": False, "extracted_value": user_message, "error_message": "CPF deve ter 11 dígitos."}

        if target_field == "sexo":
            sexo_map = {
                'masculino': 'M', 'homem': 'M', 'macho': 'M', 'm': 'M',
                'feminino': 'F', 'mulher': 'F', 'femea': 'F', 'f': 'F',
                'outro': 'O', 'nenhum': 'O', 'prefiro não informar': 'O', 'o': 'O'
            }
            for key, value in sexo_map.items():
                if key in message_lower:
                    return {"intent": "PROVIDE_INFO", "is_valid": True, "extracted_value": value, "error_message": None}

        if target_field == "data_nascimento":
            date_patterns = [r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})']
            for pattern in date_patterns:
                match = re.search(pattern, user_message)
                if match:
                    day, month, year = match.groups()
                    try:
                        day, month, year = int(day), int(month), int(year)
                        if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2024:
                            return {"intent": "PROVIDE_INFO", "is_valid": True,
                                    "extracted_value": f"{year:04d}-{month:02d}-{day:02d}", "error_message": None}
                    except:
                        pass

        if target_field == "telefone":
            phone_digits = re.sub(r'\D', '', user_message)
            if 10 <= len(phone_digits) <= 11:
                return {"intent": "PROVIDE_INFO", "is_valid": True, "extracted_value": phone_digits, "error_message": None}
            else:
                return {"intent": "PROVIDE_INFO", "is_valid": False, "extracted_value": user_message, "error_message": "Telefone inválido."}

        if target_field == "email":
            if any(phrase in message_lower for phrase in ['não tenho', 'skip', 'pular']):
                return {"intent": "PROVIDE_INFO", "is_valid": True, "extracted_value": "Não informado", "error_message": None}
            if '@' in user_message and '.' in user_message.split('@')[-1]:
                return {"intent": "PROVIDE_INFO", "is_valid": True, "extracted_value": user_message.strip(), "error_message": None}

        if target_field == "convenio":
            if any(word in message_lower for word in ['particular', 'sem convenio', 'não tenho', 'não']):
                return {"intent": "PROVIDE_INFO", "is_valid": True, "extracted_value": "Particular", "error_message": None}
            elif len(user_message.strip()) > 2:
                return {"intent": "PROVIDE_INFO", "is_valid": True, "extracted_value": user_message.strip(), "error_message": None}

        if valid_options and target_field == "especialidade":
            for option in valid_options:
                if option.lower() in message_lower or message_lower in option.lower():
                    return {"intent": "PROVIDE_INFO", "is_valid": True, "extracted_value": option, "error_message": None}

        if target_field in ["nome", "paciente", "nome_exame", "horario_preferencia"]:
            if len(user_message.strip()) > 2:
                return {"intent": "PROVIDE_INFO", "is_valid": True, "extracted_value": user_message.strip(), "error_message": None}

        return None

    def extract_consultation_data(self, message: str) -> Dict[str, Any]:
        try:
            prompt = self.extraction_prompt.format(mensagem=message)
            response = self.model.generate_content(prompt)
            data = self._parse_json_response(response.text)
            return self._process_extracted_data(data)
        except Exception as e:
            logger.error(f"Erro ao extrair dados: {e}")
            return self._get_empty_response()

    def generate_missing_data_questions(self, extracted_data: Dict[str, Any]) -> str:
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

            for campo in ['paciente.nome','paciente.cpf','agendamento.tipo_agendamento','agendamento.especialidade']:
                if campo in missing_fields:
                    perguntas.append(f'<b>{nomes_amigaveis[campo]}</b>')

            extras = [campo for campo in missing_fields if campo not in perguntas]
            if extras:
                perguntas.append('<b>Outros dados:</b><ul>' + ''.join(f'<li>{nomes_amigaveis.get(c, c)}</li>' for c in extras) + '</ul>')

            return 'Por favor, informe os seguintes dados:<br>' + '<ul>' + ''.join(f'<li>{p}</li>' for p in perguntas) + '</ul>'
        except Exception as e:
            logger.error(f"Erro ao gerar perguntas: {e}")
            return "Desculpe, ocorreu um erro. Por favor, tente novamente."

    def validate_essential_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        essential_fields = ["paciente.nome", "agendamento.tipo_agendamento", "agendamento.especialidade"]
        missing_essential = [f for f in essential_fields if f not in extracted_data.get('dados_extraidos', [])]

        return {
            "is_valid": len(missing_essential) == 0,
            "missing_essential": missing_essential,
            "can_proceed": len(missing_essential) <= 1,
            "completion_percentage": (len(essential_fields) - len(missing_essential)) / len(essential_fields) * 100
        }

    def merge_extracted_data(self, previous: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        result = previous.copy() if previous else {}
        for section in ['paciente', 'agendamento_info', 'preferencias']:
            if section not in result or not isinstance(result[section], dict):
                result[section] = {}
            for key, value in new.get(section, {}).items():
                if value not in [None, '', []]:
                    result[section][key] = value
                elif key not in result[section]:
                    result[section][key] = None
        return self._process_extracted_data(result)

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        try:
            clean_response = response_text.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            return json.loads(clean_response.strip())
        except Exception as e:
            logger.error(f"Erro ao fazer parse do JSON: {e}\nResposta: {response_text}")
            return self._get_empty_response()

    def _process_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        dados_extraidos = []
        dados_faltantes = []

        for section_name, fields in {
            "paciente": ['nome', 'cpf', 'data_nascimento', 'sexo'],
            "agendamento_info": ['tipo_agendamento', 'especialidade', 'tem_convenio'],
            "preferencias": ['data_preferencia', 'observacoes']
        }.items():
            section = data.get(section_name, {})
            for campo in fields:
                valor = section.get(campo)
                if isinstance(valor, str) and valor.strip() == '':
                    section[campo] = None
                if section.get(campo) is not None:
                    dados_extraidos.append(f"{section_name}.{campo}")
                else:
                    dados_faltantes.append(f"{section_name}.{campo}")

        data['dados_extraidos'] = dados_extraidos
        data['dados_faltantes'] = dados_faltantes
        return data

    def _get_empty_response(self) -> Dict[str, Any]:
        return {
            "paciente": {"nome": None, "cpf": None, "data_nascimento": None, "sexo": None},
            "agendamento_info": {
                "tipo_agendamento": None, "tipo_consulta": None, "nome_exame": None,
                "especialidade": None, "tem_convenio": None, "nome_convenio": None
            },
            "preferencias": {
                "data_preferencia": None, "horario_preferencia": None,
                "periodo_preferencia": None, "local_preferencia": None, "observacoes": None
            },
            "dados_extraidos": [],
            "dados_faltantes": [
                "paciente.nome", "paciente.cpf", "agendamento.tipo_agendamento",
                "agendamento.especialidade", "preferencias.data_preferencia"
            ]
        }

    def _generate_cache_key(self, user_message: str, target_field: str, valid_options: Optional[List[str]]) -> str:
        normalized_message = user_message.lower().strip()
        options_str = str(sorted(valid_options)) if valid_options else "none"
        combined = f"{normalized_message}|{target_field}|{options_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _error_result(self, user_message: str, msg: str) -> Dict[str, Any]:
        return {
            "intent": "PROVIDE_INFO",
            "is_valid": False,
            "extracted_value": user_message,
            "error_message": msg
        }

    def get_cache_stats(self) -> Dict[str, int]:
        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "api_calls": self._api_calls,
            "hit_ratio": round(self._cache_hits / max(1, self._cache_hits + self._api_calls) * 100, 2)
        }
