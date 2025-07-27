"""
Extrator de dados para agendamento de consultas usando API do Gemini
"""

import os
import json
import logging
from typing import Dict, Any, Optional
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
        Gera perguntas para completar dados faltantes
        
        Args:
            extracted_data: Dados já extraídos
            
        Returns:
            String com perguntas para dados faltantes
        """
        try:
            missing_fields = extracted_data.get('dados_faltantes', [])
            
            if not missing_fields:
                return "Perfeito! Tenho todas as informações necessárias para o agendamento."
            
            questions_prompt = f"""
            Você é um assistente médico que precisa coletar informações faltantes para agendamento.
            
            Dados já coletados: {json.dumps(extracted_data, indent=2, ensure_ascii=False)}
            
            Campos faltantes: {missing_fields}
            
            Gere perguntas amigáveis e profissionais para coletar APENAS os dados faltantes mais importantes.
            Priorize: nome, tipo de agendamento (consulta/exame), especialidade, data preferencial.
            
            Seja cordial e específico. Não pergunte tudo de uma vez, foque nos dados essenciais primeiro.
            """
            
            response = self.model.generate_content(questions_prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Erro ao gerar perguntas: {e}")
            return "Para continuar com o agendamento, preciso de mais algumas informações. Pode me ajudar?"
    
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
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON: {e}")
            logger.error(f"Resposta recebida: {response_text}")
            return self._get_empty_response()
    
    def _process_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa e valida os dados extraídos"""
        dados_extraidos = []
        dados_faltantes = []
        
        # Verificar dados do paciente
        paciente = data.get('paciente', {})
        for campo in ['nome', 'cpf', 'data_nascimento', 'sexo']:
            if paciente.get(campo):
                dados_extraidos.append(f"paciente.{campo}")
            else:
                dados_faltantes.append(f"paciente.{campo}")
        
        # Verificar dados do agendamento
        agendamento_info = data.get('agendamento_info', {})
        for campo in ['tipo_agendamento', 'especialidade', 'tem_convenio']:
            if agendamento_info.get(campo) is not None:
                dados_extraidos.append(f"agendamento.{campo}")
            else:
                dados_faltantes.append(f"agendamento.{campo}")
        
        # Verificar preferências
        preferencias = data.get('preferencias', {})
        for campo in ['data_preferencia', 'observacoes']:
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
