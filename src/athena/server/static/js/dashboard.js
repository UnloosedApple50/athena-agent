/**
 * Athena Agent Dashboard - Single Page Application
 * Real-time WebSocket communication, charts, and interactive UI.
 */

(function () {
    'use strict';

    // === State ===
    const state = {
        currentPage: 'dashboard',
        sessionId: null,
        ws: null,
        wsConnected: false,
        reconnectAttempts: 0,
        maxReconnectAttempts: 10,
        isProcessing: false,
        metrics: {
            cpuHistory: [],
            memoryHistory: [],
            networkRxHistory: [],
            networkTxHistory: [],
            throughputHistory: [],
            maxDataPoints: 60,
        },
        charts: {},
    };

    // === DOM Elements ===
    const elements = {
        sidebar: document.getElementById('sidebar'),
        menuToggle: document.getElementById('menu-toggle'),
        pageTitle: document.getElementById('page-title'),
        wsStatusDot: document.getElementById('ws-status-dot'),
        wsStatusText: document.getElementById('ws-status-text'),
        uptimeDisplay: document.getElementById('uptime-display'),
        notificationBadge: document.getElementById('notification-badge'),
        notificationsBtn: document.getElementById('notifications-btn'),
        refreshBtn: document.getElementById('refresh-btn'),
        navItems: document.querySelectorAll('.nav-item'),
        pages: document.querySelectorAll('.page'),
        modalOverlay: document.getElementById('modal-overlay'),
        modalTitle: document.getElementById('modal-title'),
        modalBody: document.getElementById('modal-body'),
        modalFooter: document.getElementById('modal-footer'),
        modalClose: document.getElementById('modal-close'),
    };

    // === Navigation ===
    function navigateTo(pageName) {
        // Update nav items
        elements.navItems.forEach(item => {
            item.classList.toggle('active', item.dataset.page === pageName);
        });

        // Update pages
        elements.pages.forEach(page => {
            page.classList.toggle('active', page.id === `page-${pageName}`);
        });

        // Update title
        const titles = {
            dashboard: 'Dashboard',
            chat: 'Chat',
            memory: 'Memory',
            decisions: 'Decisions',
            knowledge: 'Knowledge',
            integrations: 'Integrations',
            training: 'Training',
            system: 'System',
            settings: 'Settings',
        };
        elements.pageTitle.textContent = titles[pageName] || 'Athena';
        state.currentPage = pageName;

        // Load page data
        loadPageData(pageName);
    }

    function loadPageData(pageName) {
        switch (pageName) {
            case 'dashboard':
                fetchDashboardData();
                break;
            case 'chat':
                // Chat is handled by WebSocket
                break;
            case 'memory':
                fetchMemoryData();
                break;
            case 'decisions':
                fetchDecisionsData();
                break;
            case 'knowledge':
                fetchKnowledgeData();
                break;
            case 'integrations':
                fetchIntegrationsData();
                break;
            case 'training':
                fetchTrainingData();
                break;
            case 'system':
                fetchSystemData();
                break;
            case 'settings':
                fetchSettingsData();
                break;
        }
    }

    // === WebSocket Connection ===
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
                if (state.reconnectAttempts < state.maxReconnectAttempts) {
                    state.reconnectAttempts++;
                    const delay = Math.min(1000 * Math.pow(1.5, state.reconnectAttempts), 15000);
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
                displayChatResponse(data.payload);
                state.isProcessing = false;
                updateSendButton();
                break;
            case 'processing':
                // Already handled by typing indicator
                break;
            case 'pong':
                break;
            case 'health':
                updateHealth(data.payload);
                break;
            case 'metrics':
                updateRealtimeMetrics(data.payload);
                break;
            case 'system_metrics':
                updateSystemMetrics(data.payload);
                break;
            case 'notification':
                handleNotification(data.payload);
                break;
            case 'error':
                hideTyping();
                displayChatError(data.payload.message);
                state.isProcessing = false;
                updateSendButton();
                break;
            default:
                console.log('Unknown message type:', data.type, data);
        }
    }

    function sendWSMessage(type, payload) {
        if (state.wsConnected && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ type, payload }));
        }
    }

    function updateConnectionStatus(status) {
        elements.wsStatusDot.className = 'status-dot ' + status;
        const texts = {
            connected: 'Connected',
            disconnected: 'Disconnected',
            error: 'Error',
        };
        elements.wsStatusText.textContent = texts[status] || 'Connecting...';
    }

    // === Dashboard Data ===
    async function fetchDashboardData() {
        try {
            // Fetch system metrics
            const sysResponse = await fetch('/api/v1/system/metrics');
            if (sysResponse.ok) {
                const sysData = await sysResponse.json();
                updateDashboardMetrics(sysData);
            }

            // Fetch throughput metrics
            const metricsResponse = await fetch('/api/v1/metrics/throughput');
            if (metricsResponse.ok) {
                const metricsData = await metricsResponse.json();
                updateThroughputMetrics(metricsData);
            }

            // Fetch health
            const healthResponse = await fetch('/api/v1/health');
            if (healthResponse.ok) {
                const healthData = await healthResponse.json();
                updateQuickStats(healthData);
            }
        } catch (e) {
            console.error('Failed to fetch dashboard data:', e);
        }
    }

    function updateDashboardMetrics(data) {
        // CPU
        if (data.cpu) {
            const cpu = data.cpu.overall_percent || 0;
            document.getElementById('cpu-percent').textContent = `${Math.round(cpu)}%`;
            document.getElementById('cpu-cores').textContent = `${data.cpu.core_count || '--'} cores`;
            const cpuProgress = document.getElementById('cpu-progress');
            cpuProgress.style.width = `${cpu}%`;
            cpuProgress.className = 'progress-fill' + (cpu > 80 ? ' danger' : cpu > 60 ? ' warning' : '');
            
            // Store history
            state.metrics.cpuHistory.push(cpu);
            if (state.metrics.cpuHistory.length > state.metrics.maxDataPoints) {
                state.metrics.cpuHistory.shift();
            }
        }

        // RAM
        if (data.ram) {
            const ram = data.ram.percent_used || 0;
            document.getElementById('ram-percent').textContent = `${Math.round(ram)}%`;
            document.getElementById('ram-detail').textContent = 
                `${data.ram.used_human || '--'} / ${data.ram.total_human || '--'}`;
            const ramProgress = document.getElementById('ram-progress');
            ramProgress.style.width = `${ram}%`;
            ramProgress.className = 'progress-fill' + (ram > 85 ? ' danger' : ram > 70 ? ' warning' : '');
            
            state.metrics.memoryHistory.push(ram);
            if (state.metrics.memoryHistory.length > state.metrics.maxDataPoints) {
                state.metrics.memoryHistory.shift();
            }
        }

        // Disk
        if (data.disks && data.disks.length > 0) {
            const disk = data.disks[0];
            const pct = disk.percent_used || 0;
            document.getElementById('disk-percent').textContent = `${Math.round(pct)}%`;
            document.getElementById('disk-detail').textContent = 
                `${disk.used_human} / ${disk.total_human}`;
            const diskProgress = document.getElementById('disk-progress');
            diskProgress.style.width = `${pct}%`;
            diskProgress.className = 'progress-fill' + (pct > 90 ? ' danger' : pct > 75 ? ' warning' : '');
        }

        // Network
        if (data.network) {
            document.getElementById('net-throughput').textContent = 
                `${formatBytes(data.network.bytes_received + data.network.bytes_sent)}/s`;
            document.getElementById('net-detail').textContent = 
                `↓ ${data.network.bytes_received_human} ↑ ${data.network.bytes_sent_human}`;
        }

        // Uptime
        if (data.uptime_human) {
            elements.uptimeDisplay.textContent = data.uptime_human;
        }
    }

    function updateThroughputMetrics(data) {
        document.getElementById('tps-value').textContent = `${data.rolling_avg_tps || 0} tok/s`;
        document.getElementById('total-tokens').textContent = `${data.total_tokens || 0} total`;
        document.getElementById('avg-latency').textContent = `${data.avg_latency_ms || 0} ms avg`;
        
        // Update throughput chart
        if (data.recent_records) {
            state.metrics.throughputHistory = data.recent_records.map(r => r.tokens_per_second || 0);
            drawThroughputChart();
        }
    }

    function updateQuickStats(data) {
        document.getElementById('stat-memories').textContent = data.memory_count || '--';
        document.getElementById('stat-sessions').textContent = '--'; // TODO
    }

    function updateSystemMetrics(data) {
        updateDashboardMetrics(data);
    }

    function updateRealtimeMetrics(data) {
        if (data.cpu_percent !== undefined) {
            state.metrics.cpuHistory.push(data.cpu_percent);
            if (state.metrics.cpuHistory.length > state.metrics.maxDataPoints) {
                state.metrics.cpuHistory.shift();
            }
            drawCpuChart();
        }
        if (data.memory_percent !== undefined) {
            state.metrics.memoryHistory.push(data.memory_percent);
            if (state.metrics.memoryHistory.length > state.metrics.maxDataPoints) {
                state.metrics.memoryHistory.shift();
            }
            drawMemoryChart();
        }
    }

    // === Charts (Canvas) ===
    function drawThroughputChart() {
        const canvas = document.getElementById('throughput-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.parentElement.clientWidth;
        const height = canvas.height = canvas.parentElement.clientHeight;
        
        ctx.clearRect(0, 0, width, height);
        
        const data = state.metrics.throughputHistory;
        if (data.length < 2) return;
        
        const max = Math.max(...data, 10);
        const min = Math.min(...data, 0);
        const range = max - min || 1;
        
        // Draw grid
        ctx.strokeStyle = '#2a2e3d';
        ctx.lineWidth = 1;
        for (let i = 0; i < 5; i++) {
            const y = (height / 5) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
        
        // Draw line
        ctx.strokeStyle = '#6366f1';
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        data.forEach((val, i) => {
            const x = (width / (data.length - 1)) * i;
            const y = height - ((val - min) / range) * height * 0.9 - height * 0.05;
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // Draw gradient fill
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, 'rgba(99, 102, 241, 0.3)');
        gradient.addColorStop(1, 'rgba(99, 102, 241, 0)');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        data.forEach((val, i) => {
            const x = (width / (data.length - 1)) * i;
            const y = height - ((val - min) / range) * height * 0.9 - height * 0.05;
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.closePath();
        ctx.fill();
    }

    function drawCpuChart() {
        const canvas = document.getElementById('cpu-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.parentElement.clientWidth;
        const height = canvas.height = canvas.parentElement.clientHeight;
        
        ctx.clearRect(0, 0, width, height);
        
        const data = state.metrics.cpuHistory;
        if (data.length < 2) return;
        
        drawLineChart(ctx, width, height, data, 100, '#ef4444');
    }

    function drawMemoryChart() {
        const canvas = document.getElementById('memory-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.parentElement.clientWidth;
        const height = canvas.height = canvas.parentElement.clientHeight;
        
        ctx.clearRect(0, 0, width, height);
        
        const data = state.metrics.memoryHistory;
        if (data.length < 2) return;
        
        drawLineChart(ctx, width, height, data, 100, '#8b5cf6');
    }

    function drawNetworkChart() {
        const canvas = document.getElementById('network-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.parentElement.clientWidth;
        const height = canvas.height = canvas.parentElement.clientHeight;
        
        ctx.clearRect(0, 0, width, height);
        
        const rxData = state.metrics.networkRxHistory;
        const txData = state.metrics.networkTxHistory;
        
        if (rxData.length < 2) return;
        
        const max = Math.max(...rxData, ...txData, 100);
        
        drawLineChart(ctx, width, height, rxData, max, '#3b82f6');
        drawLineChart(ctx, width, height, txData, max, '#10b981');
    }

    function drawLineChart(ctx, width, height, data, maxValue, color) {
        const padding = 10;
        const chartWidth = width - padding * 2;
        const chartHeight = height - padding * 2;
        
        // Grid
        ctx.strokeStyle = '#2a2e3d';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding + (chartHeight / 4) * i;
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - padding, y);
            ctx.stroke();
        }
        
        // Line
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        data.forEach((val, i) => {
            const x = padding + (chartWidth / (data.length - 1)) * i;
            const y = padding + chartHeight - (val / maxValue) * chartHeight;
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // Fill
        const gradient = ctx.createLinearGradient(0, padding, 0, height - padding);
        gradient.addColorStop(0, color.replace(')', ', 0.3)').replace('rgb', 'rgba'));
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        data.forEach((val, i) => {
            const x = padding + (chartWidth / (data.length - 1)) * i;
            const y = padding + chartHeight - (val / maxValue) * chartHeight;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.lineTo(width - padding, height - padding);
        ctx.lineTo(padding, height - padding);
        ctx.closePath();
        ctx.fill();
    }

    // === Chat ===
    function initChat() {
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const chatModule = document.getElementById('chat-module');

        if (chatInput) {
            chatInput.addEventListener('input', function() {
                document.getElementById('input-count').textContent = `${this.value.length}/10000`;
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 120) + 'px';
            });

            chatInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage();
                }
            });
        }

        if (sendBtn) {
            sendBtn.addEventListener('click', sendChatMessage);
        }

        if (chatModule) {
            chatModule.addEventListener('change', function() {
                // Module changed - could show indicator
            });
        }

        // New chat button
        const newChatBtn = document.getElementById('new-chat-btn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', clearChat);
        }
    }

    function sendChatMessage() {
        const input = document.getElementById('chat-input');
        const module = document.getElementById('chat-module').value;
        const message = input.value.trim();

        if (!message || state.isProcessing) return;

        // Display user message
        displayUserMessage(message);
        input.value = '';
        input.style.height = 'auto';
        document.getElementById('input-count').textContent = '0/10000';
        state.isProcessing = true;
        updateSendButton();

        // Send via WebSocket or REST
        if (state.wsConnected) {
            sendWSMessage('chat', {
                message,
                module,
                session_id: state.sessionId,
            });
        } else {
            sendChatRest(message, module);
        }

        showTyping();
    }

    async function sendChatRest(message, module) {
        try {
            const response = await fetch('/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, module, session_id: state.sessionId }),
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            hideTyping();
            displayChatResponse(data);
        } catch (error) {
            hideTyping();
            displayChatError(error.message);
        } finally {
            state.isProcessing = false;
            updateSendButton();
        }
    }

    function displayUserMessage(text) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'message user';
        div.innerHTML = `
            <div class="message-avatar">👤</div>
            <div class="message-content">${escapeHtml(text)}</div>
        `;
        container.appendChild(div);
        scrollChatToBottom();
    }

    function displayChatResponse(data) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'message assistant';

        const conf = Math.round((data.confidence || 0) * 100);
        const confColor = conf > 70 ? 'var(--success)' : conf > 40 ? 'var(--warning)' : 'var(--error)';
        const confBg = conf > 70 ? 'var(--success-bg)' : conf > 40 ? 'var(--warning-bg)' : 'var(--error-bg)';

        div.innerHTML = `
            <div class="message-avatar">✦</div>
            <div class="message-content">
                ${formatMessage(data.response || '')}
                <div class="message-meta">
                    <span class="confidence-badge" style="background: ${confBg}; color: ${confColor}">
                        ${conf}% confidence
                    </span>
                    ${data.fallback ? '<span class="fallback-badge">Rule-based</span>' : ''}
                </div>
            </div>
        `;
        container.appendChild(div);

        if (data.session_id) {
            state.sessionId = data.session_id;
        }

        scrollChatToBottom();
    }

    function displayChatError(message) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.innerHTML = `
            <div class="message-avatar">⚠</div>
            <div class="message-content" style="border-color: var(--error);">
                <p style="color: var(--error);">${escapeHtml(message)}</p>
            </div>
        `;
        container.appendChild(div);
        scrollChatToBottom();
    }

    function showTyping() {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.id = 'typing-indicator';
        div.innerHTML = `
            <div class="message-avatar">✦</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        container.appendChild(div);
        scrollChatToBottom();
    }

    function hideTyping() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    function scrollChatToBottom() {
        const container = document.getElementById('chat-messages');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    function clearChat() {
        const container = document.getElementById('chat-messages');
        container.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">✦</div>
                <h2>Welcome to Athena</h2>
                <p>Ask about sales strategies, trading analysis, or general advisory.</p>
            </div>
        `;
        state.sessionId = null;
    }

    function updateSendButton() {
        const btn = document.getElementById('send-btn');
        if (btn) btn.disabled = state.isProcessing;
    }

    // === Memory Page ===
    async function fetchMemoryData() {
        const container = document.getElementById('memory-list');
        container.innerHTML = '<div class="loading-spinner">Loading memories...</div>';

        try {
            const typeFilter = document.getElementById('memory-type-filter').value;
            const moduleFilter = document.getElementById('memory-module-filter').value;
            const search = document.getElementById('memory-search').value;

            let memories = [];

            if (typeFilter === 'all' || typeFilter === 'episodic') {
                let url = '/api/v1/memory/episodic?limit=50';
                if (moduleFilter !== 'all') url += `&module=${moduleFilter}`;
                const resp = await fetch(url);
                if (resp.ok) {
                    const data = await resp.json();
                    memories = memories.concat(data.map(m => ({ ...m, type: 'episodic' })));
                }
            }

            if (typeFilter === 'all' || typeFilter === 'semantic') {
                let url = '/api/v1/memory/semantic?limit=50';
                if (moduleFilter !== 'all') url += `&module=${moduleFilter}`;
                const resp = await fetch(url);
                if (resp.ok) {
                    const data = await resp.json();
                    memories = memories.concat(data.map(m => ({ ...m, type: 'semantic' })));
                }
            }

            // Apply search filter
            if (search) {
                const searchLower = search.toLowerCase();
                memories = memories.filter(m =>
                    (m.query && m.query.toLowerCase().includes(searchLower)) ||
                    (m.response && m.response.toLowerCase().includes(searchLower)) ||
                    (m.key && m.key.toLowerCase().includes(searchLower)) ||
                    (m.value && m.value.toLowerCase().includes(searchLower))
                );
            }

            renderMemoryList(memories);
        } catch (e) {
            container.innerHTML = `<div class="loading-spinner">Error loading memories: ${e.message}</div>`;
        }
    }

    function renderMemoryList(memories) {
        const container = document.getElementById('memory-list');
        if (memories.length === 0) {
            container.innerHTML = '<div class="loading-spinner">No memories found.</div>';
            return;
        }

        container.innerHTML = memories.map(m => `
            <div class="memory-item">
                <div class="memory-item-header">
                    <span class="memory-type-badge">${m.type}</span>
                    <span class="text-muted">${m.module || 'general'}</span>
                </div>
                <div class="memory-item-content">
                    ${m.type === 'episodic' 
                        ? `<strong>Q:</strong> ${escapeHtml(m.query?.substring(0, 100) || '')}...<br>
                           <strong>A:</strong> ${escapeHtml(m.response?.substring(0, 150) || '')}...`
                        : `<strong>${escapeHtml(m.key || '')}:</strong> ${escapeHtml(m.value?.substring(0, 200) || '')}`
                    }
                </div>
            </div>
        `).join('');
    }

    // === Decisions Page ===
    async function fetchDecisionsData() {
        const container = document.getElementById('decisions-list');
        container.innerHTML = '<div class="loading-spinner">Loading decisions...</div>';

        try {
            const resp = await fetch('/api/v1/decisions');
            if (resp.ok) {
                const decisions = await resp.json();
                renderDecisionsList(decisions);
            } else {
                container.innerHTML = '<div class="loading-spinner">No decisions recorded yet.</div>';
            }
        } catch (e) {
            container.innerHTML = `<div class="loading-spinner">Error: ${e.message}</div>`;
        }
    }

    function renderDecisionsList(decisions) {
        const container = document.getElementById('decisions-list');
        if (decisions.length === 0) {
            container.innerHTML = '<div class="loading-spinner">No decisions found.</div>';
            return;
        }

        container.innerHTML = decisions.map(d => `
            <div class="decision-item">
                <div class="decision-item-header">
                    <span class="decision-module-badge">${d.module || 'general'}</span>
                    <span class="text-muted">${d.selected_option || 'pending'}</span>
                </div>
                <div class="decision-item-content">
                    <strong>Context:</strong> ${escapeHtml(d.context?.substring(0, 150) || '')}...<br>
                    <strong>Confidence:</strong> ${Math.round((d.confidence || 0) * 100)}%
                </div>
            </div>
        `).join('');
    }

    // === Knowledge Page ===
    async function fetchKnowledgeData() {
        const container = document.getElementById('knowledge-grid');
        container.innerHTML = '<div class="loading-spinner">Loading knowledge...</div>';

        try {
            const resp = await fetch('/api/v1/memory/semantic?limit=100');
            if (resp.ok) {
                const knowledge = await resp.json();
                renderKnowledgeGrid(knowledge);
            }
        } catch (e) {
            container.innerHTML = `<div class="loading-spinner">Error: ${e.message}</div>`;
        }
    }

    function renderKnowledgeGrid(knowledge) {
        const container = document.getElementById('knowledge-grid');
        if (knowledge.length === 0) {
            container.innerHTML = '<div class="loading-spinner">No knowledge entries found.</div>';
            return;
        }

        container.innerHTML = knowledge.map(k => `
            <div class="knowledge-card">
                <div class="knowledge-card-header">
                    <span class="knowledge-card-category">${k.category}</span>
                    <span class="text-muted">${k.module}</span>
                </div>
                <div class="knowledge-card-key">${escapeHtml(k.key)}</div>
                <div class="knowledge-card-value">${escapeHtml(k.value?.substring(0, 200) || '')}</div>
            </div>
        `).join('');
    }

    // === Integrations Page ===
    async function fetchIntegrationsData() {
        // Load webhooks
        try {
            const resp = await fetch('/api/v1/integrations/webhooks');
            if (resp.ok) {
                const webhooks = await resp.json();
                renderWebhooksList(webhooks);
            }
        } catch (e) {
            console.error('Failed to load webhooks:', e);
        }
    }

    function renderWebhooksList(webhooks) {
        const container = document.getElementById('webhooks-list');
        if (webhooks.length === 0) {
            container.innerHTML = '<div class="text-muted">No webhooks registered.</div>';
            return;
        }

        container.innerHTML = webhooks.map(w => `
            <div class="memory-item">
                <div class="memory-item-header">
                    <span class="memory-type-badge">${w.id}</span>
                    <span class="text-muted">${w.active ? 'Active' : 'Inactive'}</span>
                </div>
                <div class="memory-item-content">
                    <strong>URL:</strong> ${escapeHtml(w.url)}<br>
                    <strong>Events:</strong> ${w.events?.join(', ') || 'None'}
                </div>
            </div>
        `).join('');
    }

    // === Training Page ===
    async function fetchTrainingData() {
        try {
            const resp = await fetch('/api/v1/training/stats');
            if (resp.ok) {
                const stats = await resp.json();
                document.getElementById('total-feedback').textContent = stats.total_feedback || 0;
                document.getElementById('avg-rating').textContent = stats.avg_rating || '0.0';
                document.getElementById('corrections-count').textContent = stats.corrections || 0;
            }
        } catch (e) {
            console.error('Failed to load training stats:', e);
        }
    }

    // === System Page ===
    async function fetchSystemData() {
        try {
            const resp = await fetch('/api/v1/system/metrics');
            if (resp.ok) {
                const data = await resp.json();
                
                document.getElementById('sys-platform').textContent = 
                    `${data.platform?.system || '--'} ${data.platform?.release || ''}`;
                document.getElementById('sys-arch').textContent = data.platform?.machine || '--';
                document.getElementById('sys-python').textContent = data.platform?.python || '--';
                document.getElementById('sys-uptime').textContent = data.uptime_human || '--';
                document.getElementById('sys-processes').textContent = data.process_count || '--';
            }
        } catch (e) {
            console.error('Failed to load system data:', e);
        }
    }

    // === Settings Page ===
    async function fetchSettingsData() {
        // Load current settings from server
        try {
            const resp = await fetch('/api/v1/settings');
            if (resp.ok) {
                const settings = await resp.json();
                if (settings.llm_base_url) document.getElementById('setting-llm-url').value = settings.llm_base_url;
                if (settings.llm_model) document.getElementById('setting-llm-model').value = settings.llm_model;
                if (settings.host) document.getElementById('setting-host').value = settings.host;
                if (settings.port) document.getElementById('setting-port').value = settings.port;
            }
        } catch (e) {
            console.log('Settings endpoint not available');
        }
    }

    // === Utility Functions ===
    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatMessage(text) {
        let html = escapeHtml(text);
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\n/g, '<br>');
        html = html.replace(/^[-\*] (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        return html;
    }

    function handleNotification(data) {
        const badge = elements.notificationBadge;
        const currentCount = parseInt(badge.textContent) || 0;
        badge.textContent = currentCount + 1;
        badge.style.display = 'flex';
    }

    function showModal(title, body, footer) {
        elements.modalTitle.textContent = title;
        elements.modalBody.innerHTML = body;
        elements.modalFooter.innerHTML = footer || '';
        elements.modalOverlay.style.display = 'flex';
    }

    function hideModal() {
        elements.modalOverlay.style.display = 'none';
    }

    // === Event Listeners ===
    function setupEventListeners() {
        // Navigation
        elements.navItems.forEach(item => {
            item.addEventListener('click', () => navigateTo(item.dataset.page));
        });

        // Menu toggle (mobile)
        if (elements.menuToggle) {
            elements.menuToggle.addEventListener('click', () => {
                elements.sidebar.classList.toggle('open');
            });
        }

        // Refresh button
        if (elements.refreshBtn) {
            elements.refreshBtn.addEventListener('click', () => {
                loadPageData(state.currentPage);
            });
        }

        // Modal close
        if (elements.modalClose) {
            elements.modalClose.addEventListener('click', hideModal);
        }
        if (elements.modalOverlay) {
            elements.modalOverlay.addEventListener('click', (e) => {
                if (e.target === elements.modalOverlay) hideModal();
            });
        }

        // Memory filters
        document.getElementById('memory-type-filter')?.addEventListener('change', fetchMemoryData);
        document.getElementById('memory-module-filter')?.addEventListener('change', fetchMemoryData);
        document.getElementById('memory-search')?.addEventListener('input', debounce(fetchMemoryData, 300));
        document.getElementById('refresh-memories')?.addEventListener('click', fetchMemoryData);

        // Integrations
        document.getElementById('register-webhook-btn')?.addEventListener('click', registerWebhook);
        document.getElementById('generate-key-btn')?.addEventListener('click', generateApiKey);

        // Training
        document.getElementById('adapt-btn')?.addEventListener('click', runAdaptation);
        document.getElementById('replay-session-btn')?.addEventListener('click', replaySession);

        // Settings
        document.getElementById('test-llm-btn')?.addEventListener('click', testLlmConnection);

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') hideModal();
            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                document.getElementById('global-search')?.focus();
            }
        });
    }

    async function registerWebhook() {
        const url = document.getElementById('webhook-url').value;
        const eventsSelect = document.getElementById('webhook-events');
        const events = Array.from(eventsSelect.selectedOptions).map(o => o.value);

        if (!url) {
            showModal('Error', '<p>Please enter a webhook URL.</p>');
            return;
        }

        try {
            const resp = await fetch('/api/v1/integrations/webhooks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, events }),
            });

            if (resp.ok) {
                showModal('Success', '<p>Webhook registered successfully!</p>');
                fetchIntegrationsData();
            } else {
                const err = await resp.json();
                showModal('Error', `<p>${err.detail || 'Failed to register webhook'}</p>`);
            }
        } catch (e) {
            showModal('Error', `<p>${e.message}</p>`);
        }
    }

    async function generateApiKey() {
        const name = document.getElementById('api-key-name').value;
        const scopesSelect = document.getElementById('api-key-scopes');
        const scopes = Array.from(scopesSelect.selectedOptions).map(o => o.value);

        if (!name) {
            showModal('Error', '<p>Please enter a key name.</p>');
            return;
        }

        try {
            const resp = await fetch('/api/v1/integrations/api-keys', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, scopes }),
            });

            if (resp.ok) {
                const data = await resp.json();
                showModal('API Key Generated', 
                    `<p>Your API key (copy it now, it won't be shown again):</p>
                     <code style="display:block;padding:12px;background:var(--bg-input);border-radius:8px;margin:12px 0;word-break:break-all;">${data.key}</code>`,
                    '<button class="btn btn-primary" onclick="hideModal()">Done</button>'
                );
            } else {
                const err = await resp.json();
                showModal('Error', `<p>${err.detail || 'Failed to generate key'}</p>`);
            }
        } catch (e) {
            showModal('Error', `<p>${e.message}</p>`);
        }
    }

    async function runAdaptation() {
        try {
            const resp = await fetch('/api/v1/training/adapt', { method: 'POST' });
            if (resp.ok) {
                const data = await resp.json();
                document.getElementById('adaptation-results').innerHTML = 
                    `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            }
        } catch (e) {
            console.error('Adaptation failed:', e);
        }
    }

    async function replaySession() {
        if (!state.sessionId) {
            showModal('Error', '<p>No active session to replay.</p>');
            return;
        }
        try {
            const resp = await fetch(`/api/v1/training/replay/${state.sessionId}`, { method: 'POST' });
            if (resp.ok) {
                const data = await resp.json();
                showModal('Replay Results', `<pre>${JSON.stringify(data, null, 2)}</pre>`);
            }
        } catch (e) {
            console.error('Replay failed:', e);
        }
    }

    async function testLlmConnection() {
        const btn = document.getElementById('test-llm-btn');
        btn.textContent = 'Testing...';
        btn.disabled = true;

        try {
            const resp = await fetch('/api/v1/health');
            if (resp.ok) {
                const data = await resp.json();
                showModal('LLM Status', 
                    `<p>Status: <strong>${data.status}</strong></p>
                     <p>LLM Connected: <strong>${data.llm_connected ? 'Yes' : 'No'}</strong></p>`
                );
            }
        } catch (e) {
            showModal('Error', `<p>Connection test failed: ${e.message}</p>`);
        } finally {
            btn.textContent = 'Test Connection';
            btn.disabled = false;
        }
    }

    function debounce(fn, delay) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    // === Initialization ===
    function init() {
        setupEventListeners();
        connectWebSocket();
        initChat();
        fetchDashboardData();

        // Periodic refresh for non-WS data
        setInterval(() => {
            if (state.currentPage === 'dashboard') {
                fetchDashboardData();
            }
        }, 5000);

        // Draw initial charts
        setTimeout(() => {
            drawThroughputChart();
            drawCpuChart();
            drawMemoryChart();
            drawNetworkChart();
        }, 500);
    }

    // Start
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
