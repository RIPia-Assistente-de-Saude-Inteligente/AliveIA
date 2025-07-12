"""
Teste básico da API do Gemini - Apenas conexão
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Carregar variáveis de ambiente
load_dotenv()

def test_gemini_basic():
    """Teste básico da API do Gemini"""
    print("🤖 Testando API do Gemini...")
    
    try:
        # Pegar a chave da API
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            print("❌ GEMINI_API_KEY não encontrada no arquivo .env")
            return False
        
        print(f"✅ Chave da API encontrada: {api_key[:10]}...")
        
        # Configurar o Gemini
        genai.configure(api_key=api_key)
        
        # Criar modelo (usando versão mais recente)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        print("✅ Modelo Gemini configurado!")
        
        # Teste simples
        print("\n📝 Enviando mensagem de teste...")
        
        response = model.generate_content("Diga apenas 'Olá! Conexão funcionando!' se você conseguir me ouvir.")
        
        print(f"🎯 Resposta do Gemini: {response.text}")
        
        # Teste com contexto médico
        print("\n🩺 Testando contexto médico...")
        
        medical_prompt = """
        Você é um assistente médico virtual.
        Um paciente disse: "Estou com dor de cabeça há 2 dias"
        Responda de forma profissional e empática, sugerindo que ele procure atendimento médico.
        """
        
        medical_response = model.generate_content(medical_prompt)
        
        print(f"💬 Resposta médica: {medical_response.text}")
        
        print("\n✅ Teste concluído com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("🏥 Teste Básico - API do Gemini")
    print("=" * 40)
    
    success = test_gemini_basic()
    
    if success:
        print("\n🎉 API do Gemini está funcionando!")
    else:
        print("\n🔧 Verifique o arquivo .env e a chave da API")