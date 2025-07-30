// api.js
import { conversationState } from './state.js';
import { handleAIResponse, addMessage, showLoading, updateUI, displayPatients } from './ui.js';

const API_BASE_URL = 'http://localhost:8000/api/v1';

function markdownToHtml(text) {
    // Negrito: **texto**
    let html = text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    // Quebra de linha: \n
    html = html.replace(/\n/g, '<br>');
    return html;
}

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
        console.log('🔍 Enviando dados para o backend:', {
            extracted_data: {
                ...conversationState.extractedData,
                dados_extraidos: ['paciente.nome', 'agendamento.tipo_agendamento', 'agendamento.especialidade'],
                dados_faltantes: []
            }
        });

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

        console.log('🔍 Response status:', response.status);
        console.log('🔍 Response ok:', response.ok);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('🔍 Response error text:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const contentType = response.headers.get('content-type');
        console.log('🔍 Response content-type:', contentType);
        
        if (!contentType || !contentType.includes('application/json')) {
            const responseText = await response.text();
            console.error('🔍 Response não é JSON:', responseText);
            throw new Error('Resposta do servidor não é JSON válido');
        }

        const data = await response.json();
        console.log('🔍 Response data:', data);

        if (data.success) {
            const appointment = data.appointment_data;
            console.log('🔍 Appointment data:', appointment);
            const successMessage = `\n🎉 <b>Agendamento criado com sucesso!</b>\n\n📋 <b>Detalhes do Agendamento:</b><br>
• <b>ID:</b> ${appointment.id_agendamento}<br>
• <b>Paciente:</b> ${appointment.nome_paciente}<br>
• <b>Médico:</b> ${appointment.nome_medico}<br>
• <b>Especialidade:</b> ${appointment.especialidade}<br>
• <b>Data/Hora:</b> ${appointment.data_agendamento || 'Não informado'}<br>
• <b>Local:</b> ${appointment.local}<br>
• <b>Convênio:</b> ${appointment.convenio}<br>
• <b>Observações:</b> ${appointment.observacoes}<br>\n\n✅ <b>Seu agendamento foi confirmado!</b><br>`;
            addMessage(successMessage, 'success');
            conversationState.canCreateAppointment = false;
            updateUI();
        } else {
            console.error('🔍 Backend retornou success=false:', data);
            addMessage('❌ Erro ao criar agendamento: ' + (data.detail || data.message || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('🔍 Erro no catch:', error);
        console.error('🔍 Erro stack trace:', error.stack);
        addMessage('❌ Erro ao criar agendamento. Tente novamente. Detalhes: ' + error.message, 'error');
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
