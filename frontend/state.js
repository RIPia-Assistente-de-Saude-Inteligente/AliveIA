// state.js
export let conversationState = {
    extractedData: null,
    validationStatus: null,
    isProcessing: false,
    canCreateAppointment: false
};

export function resetState() {
    conversationState = {
        extractedData: null,
        validationStatus: null,
        isProcessing: false,
        canCreateAppointment: false
    };
}
