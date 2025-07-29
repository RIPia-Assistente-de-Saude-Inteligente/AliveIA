// ui.js
import { conversationState, resetState } from './state.js';

export const chatMessages = document.getElementById('chatMessages');
export const messageInput = document.getElementById('messageInput');
export const sendButton = document.getElementById('sendButton');
export const statusValue = document.getElementById('statusValue');
export const progressValue = document.getElementById('progressValue');
export const extractedDataDiv = document.getElementById('extractedData');
export const createAppointmentBtn = document.getElementById('createAppointment');
export const clearChatBtn = document.getElementById('clearChat');
export const viewPatientsBtn = document.getElementById('viewPatients');
export const patientsModal = document.getElementById('patientsModal');
export const loadingOverlay = document.getElementById('loadingOverlay');

export function addMessage(text, type = 'bot') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    if (type === 'user') {
        contentDiv.innerHTML = `<strong>👤 Você:</strong> ${text}`;
    } else {
        contentDiv.innerHTML = text;
    }
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

export function updateUI() {
    if (conversationState.isProcessing) {
        statusValue.textContent = 'Processando...';
        statusValue.style.color = '#ffa500';
    } else if (conversationState.canCreateAppointment) {
        statusValue.textContent = 'Pronto para agendar';
        statusValue.style.color = '#28a745';
    } else {
        statusValue.textContent = 'Coletando dados';
        statusValue.style.color = '#6c757d';
    }
    if (conversationState.validationStatus) {
        const progress = Math.round(conversationState.validationStatus.completion_percentage);
        progressValue.textContent = `${progress}%`;
        progressValue.style.color = progress === 100 ? '#28a745' : '#ffa500';
    } else {
        progressValue.textContent = '0%';
        progressValue.style.color = '#6c757d';
    }
    if (conversationState.extractedData) {
        displayExtractedData(conversationState.extractedData);
    } else {
        extractedDataDiv.innerHTML = '<p class="no-data">Nenhum dado coletado ainda</p>';
    }
    sendButton.disabled = conversationState.isProcessing;
    createAppointmentBtn.disabled = !conversationState.canCreateAppointment;
}

export function displayExtractedData(data) {
    let html = '';
    if (data.paciente && Object.values(data.paciente).some(v => v !== null)) {
        html += '<div class="data-section"><strong>👤 Paciente:</strong><br>';
        if (data.paciente.nome) html += `<span class="data-label">Nome:</span> ${data.paciente.nome}<br>`;
        if (data.paciente.cpf) html += `<span class="data-label">CPF:</span> ${data.paciente.cpf}<br>`;
        if (data.paciente.data_nascimento) html += `<span class="data-label">Nascimento:</span> ${data.paciente.data_nascimento}<br>`;
        if (data.paciente.sexo) html += `<span class="data-label">Sexo:</span> ${data.paciente.sexo}<br>`;
        html += '</div><br>';
    }
    if (data.agendamento_info && Object.values(data.agendamento_info).some(v => v !== null)) {
        html += '<div class="data-section"><strong>🏥 Agendamento:</strong><br>';
        if (data.agendamento_info.tipo) html += `<span class="data-label">Tipo:</span> ${data.agendamento_info.tipo}<br>`;
        if (data.agendamento_info.especialidade) html += `<span class="data-label">Especialidade:</span> ${data.agendamento_info.especialidade}<br>`;
        if (data.agendamento_info.nome_exame) html += `<span class="data-label">Exame:</span> ${data.agendamento_info.nome_exame}<br>`;
        if (data.agendamento_info.local) html += `<span class="data-label">Local:</span> ${data.agendamento_info.local}<br>`;
        if (data.agendamento_info.convenio) html += `<span class="data-label">Convênio:</span> ${data.agendamento_info.convenio}<br>`;
        html += '</div><br>';
    }
    if (data.contato && Object.values(data.contato).some(v => v !== null)) {
        html += '<div class="data-section"><strong>📞 Contato:</strong><br>';
        if (data.contato.telefone) html += `<span class="data-label">Telefone:</span> ${data.contato.telefone}<br>`;
        if (data.contato.email) html += `<span class="data-label">Email:</span> ${data.contato.email}<br>`;
        html += '</div><br>';
    }
    if (data.preferencias && Object.values(data.preferencias).some(v => v !== null)) {
        html += '<div class="data-section"><strong>📅 Preferências:</strong><br>';
        if (data.preferencias.data_preferencia) html += `<span class="data-label">Data:</span> ${data.preferencias.data_preferencia}<br>`;
        if (data.preferencias.horario_preferencia) html += `<span class="data-label">Horário:</span> ${data.preferencias.horario_preferencia}<br>`;
        if (data.preferencias.observacoes) html += `<span class="data-label">Observações:</span> ${data.preferencias.observacoes}<br>`;
        html += '</div>';
    }
    extractedDataDiv.innerHTML = html || '<p class="no-data">Nenhum dado coletado ainda</p>';
}

export function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

export function displayPatients(patients) {
    const patientsList = document.getElementById('patientsList');
    if (patients.length === 0) {
        patientsList.innerHTML = '<p class="no-data">Nenhum paciente cadastrado</p>';
        return;
    }
    const patientsHTML = patients.map(patient => `
        <div class="patient-item">
            <div class="patient-name">👤 ${patient.nome}</div>
            <div class="patient-details">
                <strong>CPF:</strong> ${patient.cpf || 'Não informado'}<br>
                <strong>Nascimento:</strong> ${formatDate(patient.data_nascimento)}<br>
                <strong>Sexo:</strong> ${patient.sexo}<br>
                <strong>ID:</strong> ${patient.id_paciente}
            </div>
        </div>
    `).join('');
    patientsList.innerHTML = patientsHTML;
}

export function handleAIResponse(data) {
    conversationState.extractedData = data.extracted_data;
    conversationState.validationStatus = data.validation;
    conversationState.canCreateAppointment = data.can_proceed;
    
    if (data.status === 'need_more_info') {
        // Formatar mensagem com quebras de linha e detalhes em negrito
        let formatted = data.next_question
            .replace(/\n/g, '<br>')
            .replace(/(nome|cpf|data de nascimento|sexo|tipo de agendamento|especialidade|convênio|data|horário|observações)/gi, match => `<strong>${match}</strong>`);
        addMessage('🤖 ' + formatted, 'bot');
    } else if (data.status === 'ready_to_book') {
        // Se estamos no estado de confirmação, mostra a mensagem mas NÃO cria automaticamente
        if (data.current_state === 'CONFIRMATION') {
            let formatted = data.next_question
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            addMessage('🤖 ' + formatted, 'bot');
        } else {
            // Só mostra a mensagem de sucesso após confirmação do usuário
            addMessage('✅ ' + data.next_question + '\n\n📋 Dados coletados com sucesso! Você pode revisar as informações no painel lateral e criar o agendamento.', 'success');
        }
    } else if (data.status === 'appointment_created') {
        // Agendamento foi criado com sucesso
        let formatted = data.next_question
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        addMessage(formatted, 'success');
        
        // Resetar o estado para permitir novo agendamento
        conversationState.canCreateAppointment = false;
        conversationState.extractedData = null;
    } else if (data.status === 'error') {
        // Erro ao criar agendamento
        addMessage(data.next_question, 'error');
    }
    updateUI();
}
