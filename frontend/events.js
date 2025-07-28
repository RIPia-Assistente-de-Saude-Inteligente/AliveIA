// events.js
import { sendMessageToAI, createAppointmentFromAI, fetchPatients } from './api.js';
import { messageInput, sendButton, clearChatBtn, viewPatientsBtn, createAppointmentBtn, patientsModal, addMessage, updateUI } from './ui.js';
import { resetState } from './state.js';

export function initializeEventListeners() {
    sendButton.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (!message) return;
        addMessage(message, 'user');
        messageInput.value = '';
        sendMessageToAI(message);
    });
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendButton.click();
        }
    });
    clearChatBtn.addEventListener('click', () => {
        document.getElementById('chatMessages').innerHTML = `<div class="message bot-message"><div class="message-content"><strong>🤖 Assistente:</strong> Olá! Sou seu assistente para agendamento médico. Como posso ajudá-lo hoje?</div></div>`;
        resetState();
        updateUI();
    });
    viewPatientsBtn.addEventListener('click', () => {
        
        fetchPatients();
    });
    createAppointmentBtn.addEventListener('click', createAppointmentFromAI);
    document.querySelector('.close').addEventListener('click', () => {
        patientsModal.style.display = 'none';
    });
    window.addEventListener('click', function(e) {
        if (e.target === patientsModal) {
            patientsModal.style.display = 'none';
        }
    });
}
