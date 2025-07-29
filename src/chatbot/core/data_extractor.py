# src/chatbot/core/data_extractor.py
import json
import hashlib
from typing import Dict, Any, List, Optional
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConsultationDataExtractor:
    def __init__(self, model):
        self.model = model
        # OTIMIZAÇÃO: Cache para evitar chamadas repetidas à API
        self._cache = {}
        self._cache_hits = 0
        self._api_calls = 0

    def analyze_user_response(self, chatbot_question: str, user_message: str, target_field: str, valid_options: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analisa a resposta do usuário com prompt otimizado, cache e fallback inteligente.
        """
        # OTIMIZAÇÃO: Verifica cache primeiro
        cache_key = self._generate_cache_key(user_message, target_field, valid_options)
        if cache_key in self._cache:
            self._cache_hits += 1
            logging.info(f"✅ Cache HIT para '{user_message}' (hits: {self._cache_hits})")
            return self._cache[cache_key]
        
        # OTIMIZAÇÃO: Tenta processamento local primeiro para casos simples
        local_result = self._try_local_processing(user_message, target_field, valid_options)
        if local_result:
            logging.info(f"⚡ Processamento LOCAL para '{user_message}'")
            self._cache[cache_key] = local_result
            return local_result
        
        # OTIMIZAÇÃO: Prompt mais conciso para reduzir tempo de processamento
        if valid_options:
            validation_text = f"Opções válidas: {valid_options}"
        else:
            validation_text = "Sem validação específica"

        # Prompt otimizado - mais direto e conciso
        prompt = f"""Analise rapidamente:
Pergunta: "{chatbot_question}"
Resposta: "{user_message}"
Campo: {target_field}
{validation_text}

Retorne JSON:
- "intent": "PROVIDE_INFO" (responde) ou "ASK_QUESTION" (pergunta)
- "is_valid": true/false (válido se PROVIDE_INFO e corresponde às opções, ou se ASK_QUESTION)
- "extracted_value": valor principal ou null
- "error_message": mensagem de erro ou null

JSON:"""

        try:
            self._api_calls += 1
            logging.info(f"🔄 API call #{self._api_calls} para '{user_message[:30]}...'")
            
            # OTIMIZAÇÃO: Configurações para resposta mais rápida
            generation_config = {
                "temperature": 0.1,  # Menor criatividade = resposta mais rápida
                "max_output_tokens": 200,  # Limita tamanho da resposta
                "top_p": 0.8,
                "top_k": 10
            }
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            raw_response_text = response.text
            logging.info(f"✅ IA respondeu ({len(raw_response_text)} chars)")

            clean_response = raw_response_text.strip().replace("```json", "").replace("```", "")
            analysis = json.loads(clean_response)
            
            # OTIMIZAÇÃO: Salva no cache
            self._cache[cache_key] = analysis
            logging.info(f"💾 Resultado salvo no cache (total: {len(self._cache)} entradas)")
            
            return analysis
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON inválido: {e}")
            result = {"intent": "PROVIDE_INFO", "is_valid": False, "extracted_value": user_message, "error_message": "Erro de processamento."}
            self._cache[cache_key] = result
            return result
        except Exception as e:
            logging.error(f"Erro na IA: {e}")
            result = {"intent": "PROVIDE_INFO", "is_valid": False, "extracted_value": user_message, "error_message": "Erro de comunicação."}
            self._cache[cache_key] = result
            return result
    
    def _try_local_processing(self, user_message: str, target_field: str, valid_options: Optional[List[str]]) -> Optional[Dict[str, Any]]:
        """Tenta processar localmente casos simples para evitar API."""
        import re
        
        message_lower = user_message.lower().strip()
        
        # Detecta perguntas óbvias
        question_patterns = [
            'que', 'qual', 'quais', 'como', 'onde', 'quando', 'opções', 'opcoes', 
            'lista', 'disponível', 'disponivel', 'tem', '?'
        ]
        if any(pattern in message_lower for pattern in question_patterns):
            return {
                "intent": "ASK_QUESTION",
                "is_valid": True,
                "extracted_value": None,
                "error_message": None
            }
        
        # Validação de CPF
        if target_field == "cpf":
            # Remove tudo que não é número
            cpf_digits = re.sub(r'\D', '', user_message)
            if len(cpf_digits) == 11:
                return {
                    "intent": "PROVIDE_INFO",
                    "is_valid": True,
                    "extracted_value": cpf_digits,
                    "error_message": None
                }
            else:
                return {
                    "intent": "PROVIDE_INFO",
                    "is_valid": False,
                    "extracted_value": user_message,
                    "error_message": "CPF deve ter exatamente 11 dígitos."
                }
        
        # Validação de sexo
        if target_field == "sexo":
            sexo_map = {
                'masculino': 'M', 'homem': 'M', 'macho': 'M', 'm': 'M',
                'feminino': 'F', 'mulher': 'F', 'femea': 'F', 'f': 'F',
                'outro': 'O', 'nenhum': 'O', 'prefiro não informar': 'O', 'o': 'O'
            }
            for key, value in sexo_map.items():
                if key in message_lower:
                    return {
                        "intent": "PROVIDE_INFO",
                        "is_valid": True,
                        "extracted_value": value,
                        "error_message": None
                    }
        
        # Validação de data de nascimento (formatos comuns)
        if target_field == "data_nascimento":
            # Tenta formatos de data comuns: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy
            date_patterns = [
                r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})',  # dd/mm/yyyy
                r'(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})'   # yyyy/mm/dd
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, user_message)
                if match:
                    parts = match.groups()
                    if len(parts[2]) == 4:  # dd/mm/yyyy
                        day, month, year = parts
                    else:  # yyyy/mm/dd
                        year, month, day = parts
                    
                    # Validação básica
                    try:
                        day_int, month_int, year_int = int(day), int(month), int(year)
                        if 1 <= day_int <= 31 and 1 <= month_int <= 12 and 1900 <= year_int <= 2024:
                            formatted_date = f"{year_int:04d}-{month_int:02d}-{day_int:02d}"
                            return {
                                "intent": "PROVIDE_INFO",
                                "is_valid": True,
                                "extracted_value": formatted_date,
                                "error_message": None
                            }
                    except ValueError:
                        pass
        
        # Validação de telefone
        if target_field == "telefone":
            # Remove tudo que não é número
            phone_digits = re.sub(r'\D', '', user_message)
            if 10 <= len(phone_digits) <= 11:  # Telefone com/sem 9 e com DDD
                return {
                    "intent": "PROVIDE_INFO",
                    "is_valid": True,
                    "extracted_value": phone_digits,
                    "error_message": None
                }
            else:
                return {
                    "intent": "PROVIDE_INFO",
                    "is_valid": False,
                    "extracted_value": user_message,
                    "error_message": "Telefone deve ter entre 10 e 11 dígitos (com DDD)."
                }
        
        # Validação de email
        if target_field == "email":
            # Verifica se quer pular o email
            skip_email = any(phrase in message_lower for phrase in ['não tenho', 'não', 'nenhum', 'skip', 'pular'])
            if skip_email:
                return {
                    "intent": "PROVIDE_INFO",
                    "is_valid": True,
                    "extracted_value": "Não informado",
                    "error_message": None
                }
            
            # Validação básica de email
            if '@' in user_message and '.' in user_message.split('@')[-1]:
                return {
                    "intent": "PROVIDE_INFO",
                    "is_valid": True,
                    "extracted_value": user_message.strip(),
                    "error_message": None
                }
        
        # Validação de convênio
        if target_field == "convenio":
            # Verifica se é particular
            if any(word in message_lower for word in ['particular', 'sem convenio', 'não tenho', 'não']):
                return {
                    "intent": "PROVIDE_INFO",
                    "is_valid": True,
                    "extracted_value": "Particular",
                    "error_message": None
                }
            # Se tem texto, aceita como nome do convênio
            elif len(user_message.strip()) > 2:
                return {
                    "intent": "PROVIDE_INFO",
                    "is_valid": True,
                    "extracted_value": user_message.strip(),
                    "error_message": None
                }
        
        # Valida opções localmente se disponíveis
        if valid_options and target_field == "especialidade":
            for option in valid_options:
                if option.lower() in message_lower or message_lower in option.lower():
                    return {
                        "intent": "PROVIDE_INFO",
                        "is_valid": True,
                        "extracted_value": option,
                        "error_message": None
                    }
        
        # Campos simples (nome, etc.) - aceita qualquer texto não vazio
        if target_field in ["nome", "paciente", "nome_exame", "horario_preferencia"]:
            if len(user_message.strip()) > 2:  # Nome mínimo
                return {
                    "intent": "PROVIDE_INFO",
                    "is_valid": True,
                    "extracted_value": user_message.strip(),
                    "error_message": None
                }
        
        return None  # Não conseguiu processar localmente
    
    def _generate_cache_key(self, user_message: str, target_field: str, valid_options: Optional[List[str]]) -> str:
        """Gera chave única para cache baseada nos parâmetros de entrada."""
        # Normaliza a mensagem para evitar duplicatas por diferenças mínimas
        normalized_message = user_message.lower().strip()
        options_str = str(sorted(valid_options)) if valid_options else "none"
        
        # Cria hash para chave compacta
        combined = f"{normalized_message}|{target_field}|{options_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Retorna estatísticas do cache para monitoramento."""
        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "api_calls": self._api_calls,
            "hit_ratio": round(self._cache_hits / max(1, self._cache_hits + self._api_calls) * 100, 2)
        }