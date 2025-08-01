// Configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';

// State management
let conversationState = {
    extractedData: null,
    validationStatus: null,
    isProcessing: false,
    canCreateAppointment: false
};

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const statusValue = document.getElementById('statusValue');
const progressValue = document.getElementById('progressValue');
const extractedDataDiv = document.getElementById('extractedData');
const createAppointmentBtn = document.getElementById('createAppointment');
const clearChatBtn = document.getElementById('clearChat');
const viewPatientsBtn = document.getElementById('viewPatients');
const patientsModal = document.getElementById('patientsModal');
const loadingOverlay = document.getElementById('loadingOverlay');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    updateUI();
});

// Event Listeners
function initializeEventListeners() {
    // Send message on button click
    sendButton.addEventListener('click', sendMessage);
    
    // Send message on Enter key
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Clear chat
    clearChatBtn.addEventListener('click', clearChat);
    
    // View patients
    viewPatientsBtn.addEventListener('click', showPatientsModal);
    
    // Create appointment
    createAppointmentBtn.addEventListener('click', createAppointment);
    
    // Modal close
    document.querySelector('.close').addEventListener('click', closeModal);
    window.addEventListener('click', function(e) {
        if (e.target === patientsModal) {
            closeModal();
        }
    });
}

// Main Functions
async function sendMessage() {
    const message = messageInput.value.trim();
    
    // Proteção extra contra mensagens vazias ou undefined
    if (!message || message === 'undefined' || message === 'null' || conversationState.isProcessing) {
        console.warn('Tentativa de enviar mensagem inválida:', message);
        return;
    }
    
    // Add user message to chat
    addMessage(message, 'user');
    messageInput.value = '';
    
    // Show loading
    showLoading(true);
    conversationState.isProcessing = true;
    updateUI();
    
    try {
        // Volta a enviar apenas a mensagem, sem estado acumulado
        const response = await fetch(`${API_BASE_URL}/ai-booking/process-message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        if (data.success) {
            handleAIResponse(data);
        } else {
            addMessage('❌ Erro ao processar mensagem: ' + data.detail, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('❌ Erro de conexão. Verifique se o servidor está rodando.', 'error');
    } finally {
        showLoading(false);
        conversationState.isProcessing = false;
        updateUI();
    }
}

document.getElementById("uploadPdf").addEventListener("change", async function (event) {
    const file = event.target.files[0];
    if (!file) return;

    // Mostra overlay de carregamento
    document.getElementById("loadingOverlay").style.display = "flex";

    const formData = new FormData();
    formData.append("pdf_file", file);

    try {
        const response = await fetch("/api/v1/ai-booking/process-pdf", {
            method: "POST",
            body: formData,
        });

        const result = await response.json();
        console.log("📥 Resposta completa do PDF:", result);
        
        if (result.success) {
            console.log("✅ PDF processado com sucesso!");
            console.log("📊 Dados extraídos:", result.extracted_data);
            console.log("📈 Validação:", result.validation);
            
            // Atualiza o estado da conversa com os dados extraídos
            conversationState.extractedData = result.extracted_data;
            conversationState.validationStatus = result.validation;
            conversationState.canCreateAppointment = result.can_proceed;
            
            // Se o agendamento foi criado automaticamente, não mostra mensagem redundante
            if (result.status === 'appointment_created') {
                // Apenas processa a resposta - a mensagem de sucesso virá do handleAIResponse
                handleAIResponse(result);
            } else {
                // Para outros casos, mostra mensagem de processamento
                addMessage("📄 PDF processado com sucesso! Agendamento sendo criado...", 'user');
                handleAIResponse(result);
            }
            
            // Atualiza a UI
            updateUI();
            
        } else {
            console.error("❌ Erro ao processar PDF:", result);
            alert("Falha ao processar o PDF: " + (result.detail || result.message || "Erro desconhecido"));
        }
    } catch (err) {
        console.error("Erro ao enviar PDF:", err);
        alert("Erro ao processar o PDF.");
    } finally {
        document.getElementById("loadingOverlay").style.display = "none";
    }
});


function handleAIResponse(data) {
    // Update conversation state
    conversationState.extractedData = data.extracted_data;
    conversationState.validationStatus = data.validation;
    conversationState.canCreateAppointment = data.can_proceed;
    
    // Add bot response
    if (data.status === 'need_more_info') {
        if (data.next_question) {
            addMessage('🤖 ' + data.next_question, 'bot');
        }
    } else if (data.status === 'ready_to_book') {
        addMessage('✅ ' + '\n\n Informações coletadas, pronto para agendar!', 'success');
    } else if (data.status === 'appointment_created') {
        // Agendamento foi criado automaticamente - usa a mensagem do backend
        if (data.next_question) {
            addMessage(data.next_question, 'success');
        } else {
            addMessage('✅ Agendamento criado com sucesso!', 'success');
        }
        
        // Reset state
        conversationState.canCreateAppointment = false;
        conversationState.extractedData = null;
    }
    
    updateUI();
}

async function createAppointment() {
    if (!conversationState.canCreateAppointment || !conversationState.extractedData) {
        addMessage('❌ Não é possível criar agendamento. Dados insuficientes.', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/ai-booking/create-from-ai`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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
            const successMessage = `
🎉 **Agendamento criado com sucesso!**

📋 **Detalhes do Agendamento:**
• **ID:** ${appointment.id_agendamento}
• **Paciente:** ${appointment.nome_paciente}
• **Médico:** ${appointment.nome_medico}
• **Especialidade:** ${appointment.especialidade}
• **Data/Hora:** ${appointment.data_agendamento}
• **Local:** ${appointment.local}
• **Convênio:** ${appointment.convenio || 'Particular'}
• **Observações:** ${appointment.observacoes || 'Nenhuma'}

✅ Seu agendamento foi confirmado!
            `;
            addMessage(successMessage, 'success');
            
            // Reset state
            conversationState.canCreateAppointment = false;
            updateUI();
        } else {
            addMessage('❌ Erro ao criar agendamento: ' + data.detail, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('❌ Erro ao criar agendamento. Tente novamente.', 'error');
    } finally {
        showLoading(false);
    }
}

async function showPatientsModal() {
    patientsModal.style.display = 'block';
    
    try {
        const response = await fetch(`${API_BASE_URL}/patients/`);
        if (!response.ok) {
            // Se a resposta não for 2xx, mostre erro específico
            const errorText = await response.text();
            document.getElementById('patientsList').innerHTML = `<p>❌ Erro ao carregar pacientes: ${response.status} - ${errorText}</p>`;
            return;
        }
        const data = await response.json();
        if ((data.success || Array.isArray(data)) && (data.data || Array.isArray(data))) {
            // Suporta resposta como { success: true, data: [...] } ou apenas [...]
            displayPatients(data.data || data);
        } else {
            document.getElementById('patientsList').innerHTML = '<p>❌ Erro ao carregar pacientes</p>';
        }
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('patientsList').innerHTML = `<p>❌ Erro de conexão: ${error.message}</p>`;
    }
}

function displayPatients(patients) {
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

function clearChat() {
    chatMessages.innerHTML = `
        <div class="message bot-message">
            <div class="message-content">
                <strong>🤖 Assistente:</strong> Olá! Sou seu assistente para agendamento médico. Como posso ajudá-lo hoje?
            </div>
        </div>
    `;
    
    // Reset state
    conversationState = {
        extractedData: null,
        validationStatus: null,
        isProcessing: false,
        canCreateAppointment: false
    };
    
    updateUI();
}

function closeModal() {
    patientsModal.style.display = 'none';
}

// UI Helper Functions
function addMessage(text, type = 'bot') {
    // Verificação para evitar undefined
    if (!text || text === 'undefined') {
        console.warn('Tentativa de adicionar mensagem vazia ou undefined:', text);
        return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (type === 'user') {
        contentDiv.innerHTML = `<strong>👤 Você:</strong> ${text}`;
    } else if (type === 'bot') {
        contentDiv.innerHTML = text;
    } else if (type === 'error') {
        contentDiv.innerHTML = text;
    } else if (type === 'success') {
        contentDiv.innerHTML = text;
    }
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateUI() {
    // Update status
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
    
    // Update progress
    if (conversationState.validationStatus) {
        const progress = Math.round(conversationState.validationStatus.completion_percentage);
        progressValue.textContent = `${progress}%`;
        progressValue.style.color = progress === 100 ? '#28a745' : '#ffa500';
    } else {
        progressValue.textContent = '0%';
        progressValue.style.color = '#6c757d';
    }
    
    // Update extracted data display
    if (conversationState.extractedData) {
        displayExtractedData(conversationState.extractedData);
    } else {
        extractedDataDiv.innerHTML = '<p class="no-data">Nenhum dado coletado ainda</p>';
    }
    
    // Update buttons
    sendButton.disabled = conversationState.isProcessing;
    createAppointmentBtn.disabled = !conversationState.canCreateAppointment;
}

function displayExtractedData(data) {
    let html = '';
    
    // Patient data
    if (data.paciente && Object.values(data.paciente).some(v => v !== null)) {
        html += '<div class="data-section"><strong>👤 Paciente:</strong><br>';
        if (data.paciente.nome) html += `<span class="data-label">Nome:</span> ${data.paciente.nome}<br>`;
        if (data.paciente.cpf) html += `<span class="data-label">CPF:</span> ${data.paciente.cpf}<br>`;
        if (data.paciente.data_nascimento) html += `<span class="data-label">Nascimento:</span> ${data.paciente.data_nascimento}<br>`;
        if (data.paciente.sexo) html += `<span class="data-label">Sexo:</span> ${data.paciente.sexo}<br>`;
        html += '</div><br>';
    }
    
    // Appointment data
    if (data.agendamento_info && Object.values(data.agendamento_info).some(v => v !== null)) {
        html += '<div class="data-section"><strong>🏥 Agendamento:</strong><br>';
        if (data.agendamento_info.tipo_agendamento) html += `<span class="data-label">Tipo:</span> ${data.agendamento_info.tipo_agendamento}<br>`;
        if (data.agendamento_info.especialidade) html += `<span class="data-label">Especialidade:</span> ${data.agendamento_info.especialidade}<br>`;
        if (data.agendamento_info.tem_convenio !== null) html += `<span class="data-label">Convênio:</span> ${data.agendamento_info.tem_convenio ? 'Sim' : 'Não'}<br>`;
        if (data.agendamento_info.nome_convenio) html += `<span class="data-label">Nome do Convênio:</span> ${data.agendamento_info.nome_convenio}<br>`;
        html += '</div><br>';
    }
    
    // Preferences
    if (data.preferencias && Object.values(data.preferencias).some(v => v !== null)) {
        html += '<div class="data-section"><strong>📅 Preferências:</strong><br>';
        if (data.preferencias.data_preferencia) html += `<span class="data-label">Data:</span> ${data.preferencias.data_preferencia}<br>`;
        if (data.preferencias.horario_preferencia) html += `<span class="data-label">Horário:</span> ${data.preferencias.horario_preferencia}<br>`;
        if (data.preferencias.observacoes) html += `<span class="data-label">Observações:</span> ${data.preferencias.observacoes}<br>`;
        html += '</div>';
    }
    
    extractedDataDiv.innerHTML = html || '<p class="no-data">Nenhum dado coletado ainda</p>';
}

function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

// Utility Functions
function formatDate(dateString) {
    if (!dateString) return 'Não informado';
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

function formatDateTime(dateTimeString) {
    if (!dateTimeString) return 'Não informado';
    const date = new Date(dateTimeString);
    return date.toLocaleString('pt-BR');
}
