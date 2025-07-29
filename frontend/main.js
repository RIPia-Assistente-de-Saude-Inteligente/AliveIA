// main.js
import { initializeEventListeners } from './events.js';
import { updateUI } from './ui.js';

document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    updateUI();
});
