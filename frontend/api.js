// api.js
import { conversationState } from './state.js';
import { handleAIResponse, addMessage, showLoading, updateUI, displayPatients } from './ui.js';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export async function sendMessageToAI(message) {
    showLoading(true);
    conversationState.isProcessing = true;
    updateUI();
    try {
        const response = await fetch(`${API_BASE_URL}/ai-booking/process-message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await response.json();
        if (data.success) {
            handleAIResponse(data);
        } else {
            addMessage('❌ Erro ao processar mensagem: ' + data.detail, 'error');
        }
    } catch (error) {
        addMessage('❌ Erro de conexão. Verifique se o servidor está rodando.', 'error');
    } finally {
        showLoading(false);
        conversationState.isProcessing = false;
        updateUI();
    }
}

export async function createAppointmentFromAI() {
    if (!conversationState.canCreateAppointment || !conversationState.extractedData) {
        addMessage('❌ Não é possível criar agendamento. Dados insuficientes.', 'error');
        return;
    }
    showLoading(true);
    try {
        const response = await fetch(`${API_BASE_URL}/ai-booking/create-from-ai`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                extracted_data: {
                    ...conversationState.extractedData,
                    dados_extraidos: ['paciente.nome', 'agendamento.tipo_agendamento', 'agendamento.especialidade'],
                    dados_faltantes: []
                }
            })
        });
        const data = await response.json();
        if (data.success) {
            const appointment = data.appointment_data;
            const successMessage = `\n🎉 **Agendamento criado com sucesso!**\n\n📋 **Detalhes do Agendamento:**\n• **ID:** ${appointment.id_agendamento}\n• **Paciente:** ${appointment.paciente_nome}\n• **Médico:** ${appointment.medico_nome}\n• **Especialidade:** ${appointment.especialidade_nome}\n• **Data/Hora:** ${formatDateTime(appointment.data_hora_inicio)}\n• **Local:** ${appointment.local_nome}\n• **Convênio:** ${appointment.convenio_nome || 'Particular'}\n• **Observações:** ${appointment.observacoes || 'Nenhuma'}\n\n✅ Seu agendamento foi confirmado!\n            `;
            addMessage(successMessage, 'success');
            conversationState.canCreateAppointment = false;
            updateUI();
        } else {
            addMessage('❌ Erro ao criar agendamento: ' + data.detail, 'error');
        }
    } catch (error) {
        addMessage('❌ Erro ao criar agendamento. Tente novamente.', 'error');
    } finally {
        showLoading(false);
    }
}

export async function fetchPatients() {
    patientsModal.style.display = 'block';
    try {
        const response = await fetch(`${API_BASE_URL}/patients/`);
        const data = await response.json();
        if (data.success && data.data) {
            displayPatients(data.data);
        } else {
            document.getElementById('patientsList').innerHTML = '<p>❌ Erro ao carregar pacientes</p>';
        }
    } catch (error) {
        document.getElementById('patientsList').innerHTML = '<p>❌ Erro de conexão</p>';
    }
}

async function showPatientsModal() {
    patientsModal.style.display = 'block';
    
    try {
        const response = await fetch(`${API_BASE_URL}/patients/`);
        const data = await response.json();
        
        if (data.success && data.data) {
            displayPatients(data.data);
        } else {
            document.getElementById('patientsList').innerHTML = '<p>❌ Erro ao carregar pacientes</p>';
        }
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('patientsList').innerHTML = '<p>❌ Erro de conexão</p>';
    }
}

// Utilitário local
function formatDateTime(dateTimeString) {
    if (!dateTimeString) return 'Não informado';
    const date = new Date(dateTimeString);
    return date.toLocaleString('pt-BR');
}
