# 📋 TESTE DO ENDPOINT /create-from-ai

## 🔗 URL 
```
POST http://localhost:8000/api/v1/ai-booking/create-from-ai
Content-Type: application/json
```

## 📨 Exemplo de Payload JSON

```json
{
  "paciente": {
    "nome": "Maria Silva Santos",
    "cpf": "12345678900",
    "data_nascimento": "1985-08-25",
    "sexo": "F"
  },
  "contato": {
    "telefone": "11987654321", 
    "email": "maria@email.com"
  },
  "agendamento_info": {
    "tipo": "consulta",
    "especialidade": "Cardiologia",
    "convenio": "Unimed"
  },
  "preferencias": {
    "data_preferencia": "2025-12-20",
    "horario_preferencia": "14:30"
  }
}
```

## ✅ Resposta de Sucesso (201)

```json
{
  "success": true,
  "message": "Agendamento criado com sucesso!",
  "data": {
    "appointment_id": 123,
    "patient_id": 456,
    "patient_name": "Maria Silva Santos",
    "appointment_date": "2025-12-20",
    "appointment_time": "14:30",
    "type": "consulta",
    "specialty_or_exam": "Cardiologia",
    "contact_phone": "11987654321",
    "contact_email": "maria@email.com"
  }
}
```

## ❌ Exemplo de Erro (400)

```json
{
  "detail": "Campo obrigatório ausente: paciente.nome"
}
```

## 🔧 FUNCIONALIDADES PRINCIPAIS

- ✅ Validação de dados obrigatórios
- ✅ Verificação de paciente existente por CPF  
- ✅ Criação automática de paciente novo
- ✅ Processamento inteligente de horários
- ✅ Criação do agendamento no banco
- ✅ Retorno com IDs para confirmação

## 🚀 STATUS: PRONTO PARA PRODUÇÃO!

### Como testar:

1. **Iniciar o servidor:**
   ```bash
   cd /home/Giovanni/Documents/AliveIA
   python main.py
   ```

2. **Fazer requisição (usando curl):**
   ```bash
   curl -X POST http://localhost:8000/api/v1/ai-booking/create-from-ai \
     -H "Content-Type: application/json" \
     -d @payload_exemplo.json
   ```

3. **Ou usar Postman/Insomnia** com o JSON acima

### Fluxo Completo do Chatbot:

1. 🤖 **Chatbot coleta dados** através do flow de 10 estados
2. 📤 **Frontend envia** dados para `/create-from-ai`
3. 🔍 **Sistema verifica** se paciente existe (por CPF)
4. 👤 **Cria paciente** se não existir
5. 📅 **Cria agendamento** com dados validados
6. ✅ **Retorna confirmação** com IDs gerados
