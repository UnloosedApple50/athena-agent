/**
 * Athena Agent - Main Application JavaScript
 * Handles chat interface, WebSocket connection, and UI interactions.
 */

(function() {
    'use strict';

    // === State ===
    const state = {
        sessionId: null,
        currentModule: 'general',
        ws: null,
        wsConnected: false,
        isProcessing: false,
        reconnectAttempts: 0,
        maxReconnectAttempts: 5,
    };

    // === DOM Elements ===
    const elements = {
        chatMessages: document.getElementById('chat-messages'),
        chatForm: document.getElementById('chat-form'),
        chatInput: document.getElementById('chat-input'),
        sendBtn: document.getElementById('send-btn'),
        charCount: document.getElementById('char-count'),
        currentModule: document.getElementById('current-module'),
        sessionStatus: document.getElementById('session-status'),
        llmStatus: document.getElementById('llm-status'),
        memoryCount: document.getElementById('memory-count'),
        chatTitle: document.getElementById('chat-title'),
        clearChat: document.getElementById('clear-chat'),
        newSession: document.getElementById('new-session'),
        moduleBtns: document.querySelectorAll('.module-btn'),
    };

    // === Templates ===
    const templates = {
        userMessage: document.getElementById('user-message-template'),
        assistantMessage: document.getElementById('assistant-message-template'),
        typing: document.getElementById('typing-template'),
    };

    // === Initialization ===
    function init() {
        setupEventListeners();
        connectWebSocket();
        fetchHealth();
        // Periodic health check
        setInterval(fetchHealth, 30000);
    }

    // === WebSocket ===
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            state.ws = new WebSocket(wsUrl);

            state.ws.onopen = () => {
                state.wsConnected = true;
                state.reconnectAttempts = 0;
                updateConnectionStatus('connected');
                console.log('WebSocket connected');
            };

            state.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                } catch (e) {
                    console.error('Failed to parse WS message:', e);
                }
            };

            state.ws.onclose = () => {
                state.wsConnected = false;
                updateConnectionStatus('disconnected');
                // Attempt reconnection
                if (state.reconnectAttempts < state.maxReconnectAttempts) {
                    state.reconnectAttempts++;
                    const delay = Math.min(1000 * Math.pow(2, state.reconnectAttempts), 10000);
                    setTimeout(connectWebSocket, delay);
                }
            };

            state.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                state.wsConnected = false;
                updateConnectionStatus('error');
            };
        } catch (e) {
            console.error('Failed to create WebSocket:', e);
            updateConnectionStatus('error');
        }
    }

    function handleWebSocketMessage(data) {
        switch (data.type) {
            case 'connected':
                console.log('Connected:', data.payload);
                break;
            case 'response':
                hideTyping();
                displayResponse(data.payload);
                state.isProcessing = false;
                updateSendButton();
                break;
            case 'processing':
                // Already showing typing indicator
                break;
            case 'pong':
                break;
            case 'health':
                updateHealth(data.payload);
                break;
            case 'error':
                hideTyping();
                displayError(data.payload.message);
                state.isProcessing = false;
                updateSendButton();
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    // === UI Functions ===
    function displayUserMessage(text) {
        const clone = templates.userMessage.content.cloneNode(true);
        clone.querySelector('.message-text').textContent = text;
        elements.chatMessages.appendChild(clone);
        scrollToBottom();
    }

    function displayResponse(payload) {
        const clone = templates.assistantMessage.content.cloneNode(true);
        const contentEl = clone.querySelector('.message-content');
        const textEl = clone.querySelector('.message-text');

        // Format response text with simple markdown-like rendering
        textEl.innerHTML = formatMessage(payload.response);

        // Confidence badge
        const badge = clone.querySelector('.confidence-badge');
        const conf = Math.round(payload.confidence * 100);
        badge.textContent = `${conf}% confidence`;
        badge.style.background = conf > 70 ? 'rgba(16, 185, 129, 0.2)' :
                                   conf > 40 ? 'rgba(245, 158, 11, 0.2)' :
                                   'rgba(239, 68, 68, 0.2)';
        badge.style.color = conf > 70 ? 'var(--success)' :
                            conf > 40 ? 'var(--warning)' :
                            'var(--error)';

        // Fallback badge
        if (payload.fallback) {
            clone.querySelector('.fallback-badge').style.display = 'inline-block';
        }

        elements.chatMessages.appendChild(clone);

        // Update session ID
        if (payload.session_id) {
            state.sessionId = payload.sessionId;
        }

        scrollToBottom();
    }

    function showTyping() {
        const clone = templates.typing.content.cloneNode(true);
        clone.id = 'typing-indicator';
        elements.chatMessages.appendChild(clone);
        scrollToBottom();
    }

    function hideTyping() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    function displayError(message) {
        const div = document.createElement('div');
        div.className = 'message assistant-message';
        div.innerHTML = `
            <div class="message-avatar">&#x26A0;</div>
            <div class="message-content" style="border-color: var(--error);">
                <p style="color: var(--error);">${escapeHtml(message)}</p>
            </div>
        `;
        elements.chatMessages.appendChild(div);
        scrollToBottom();
    }

    function formatMessage(text) {
        // Escape HTML first
        let html = escapeHtml(text);

        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Line breaks
        html = html.replace(/\n/g, '<br>');

        // Bullet points
        html = html.replace(/^[-\*] (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

        // Numbered lists
        html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

        return html;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function scrollToBottom() {
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }

    function updateConnectionStatus(status) {
        const statusEl = elements.sessionStatus;
        statusEl.className = 'stat-value ' + status;

        switch (status) {
            case 'connected':
                statusEl.textContent = 'Connected';
                break;
            case 'disconnected':
            case 'error':
                statusEl.textContent = 'Disconnected';
                break;
            default:
                statusEl.textContent = 'Connecting...';
        }
    }

    function updateSendButton() {
        elements.sendBtn.disabled = state.isProcessing;
    }

    function updateHealth(payload) {
        if (payload.status === 'healthy') {
            if (payload.llm_connected !== undefined) {
                elements.llmStatus.textContent = payload.llm_connected ? 'Active' : 'Offline';
                elements.llmStatus.className = 'stat-value ' + (payload.llm_connected ? 'connected' : 'disconnected');
            }
            if (payload.memory_count !== undefined) {
                elements.memoryCount.textContent = payload.memory_count.toLocaleString();
            }
        }
    }

    // === Event Handlers ===
    function setupEventListeners() {
        // Form submission
        elements.chatForm.addEventListener('submit', handleSubmit);

        // Input character count
        elements.chatInput.addEventListener('input', handleInput);

        // Enter to send (Shift+Enter for newline)
        elements.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
            }
        });

        // Module switching
        elements.moduleBtns.forEach(btn => {
            btn.addEventListener('click', () => switchModule(btn));
        });

        // Clear chat
        elements.clearChat.addEventListener('click', clearChat);

        // New session
        elements.newSession.addEventListener('click', startNewSession);
    }

    function handleSubmit(e) {
        e.preventDefault();

        const message = elements.chatInput.value.trim();
        if (!message || state.isProcessing) return;

        // Display user message
        displayUserMessage(message);

        // Show typing indicator
        showTyping();
        state.isProcessing = true;
        updateSendButton();

        // Clear input
        elements.chatInput.value = '';
        elements.charCount.textContent = '0/10000';

        // Send via WebSocket or REST API fallback
        if (state.wsConnected && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({
                type: 'chat',
                payload: {
                    message: message,
                    module: state.currentModule,
                    session_id: state.sessionId,
                }
            }));
        } else {
            // Fallback to REST API
            sendViaRest(message);
        }
    }

    async function sendViaRest(message) {
        try {
            const response = await fetch('/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    module: state.currentModule,
                    session_id: state.sessionId,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            hideTyping();
            displayResponse(data);
        } catch (error) {
            hideTyping();
            displayError(`Failed to send message: ${error.message}`);
        } finally {
            state.isProcessing = false;
            updateSendButton();
        }
    }

    function handleInput() {
        const len = elements.chatInput.value.length;
        elements.charCount.textContent = `${len}/10000`;
    }

    function switchModule(btn) {
        // Update active state
        elements.moduleBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Update state
        const moduleNames = {
            general: 'General Assistant',
            sales: 'Sales Strategist',
            trading: 'Trading Analyst',
        };
        state.currentModule = btn.dataset.module;
        elements.currentModule.textContent = btn.querySelector('span:last-child').textContent;
        elements.chatTitle.textContent = moduleNames[state.currentModule] || 'Athena';

        // Add system message
        addSystemMessage(`Switched to <strong>${elements.chatTitle.textContent}</strong> module.`);
    }

    function clearChat() {
        elements.chatMessages.innerHTML = '';
        state.sessionId = null;
    }

    function startNewSession() {
        clearChat();
        addSystemMessage('New session started. Ready to assist!');
    }

    function addSystemMessage(text) {
        const div = document.createElement('div');
        div.className = 'message assistant-message';
        div.innerHTML = `
            <div class="message-avatar">&#x1F31F;</div>
            <div class="message-content">
                <p>${text}</p>
            </div>
        `;
        elements.chatMessages.appendChild(div);
        scrollToBottom();
    }

    async function fetchHealth() {
        try {
            const response = await fetch('/api/v1/health');
            if (response.ok) {
                const data = await response.json();
                updateHealth(data);
            }
        } catch (e) {
            // Silently fail
        }
    }

    // === Start ===
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
