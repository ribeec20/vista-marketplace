/**
 * Notion-style Architecture Chat - Shared JavaScript
 * Use this for architecture.html and diagram_expand.html
 */

// =========================================================================
// Architecture Chat Module
// =========================================================================

const ArchChat = {
    // Configuration (set before init)
    projectId: null,
    featureName: null,
    
    // State
    currentSessionId: null,
    eventSource: null,
    isStreaming: false,
    streamingMsgEl: null,
    streamingText: '',
    _allSessions: [],
    _modelFetchId: 0,
    _lastServiceHealth: {},
    
    // DOM Element references (populated during init)
    elements: {},
    
    /**
     * Initialize the chat module
     * @param {Object} config - { projectId, featureName, providers }
     */
    init(config) {
        this.projectId = config.projectId;
        this.featureName = config.featureName;
        this.providers = config.providers || [];
        
        this._cacheElements();
        this._attachEventListeners();
        this.loadSessions();
        this.pollServiceHealth();
        setInterval(() => this.pollServiceHealth(), 10000);
        
        if (this.providers.length > 0) {
            this.fetchModels(this.providers[0].name);
        }
    },
    
    /**
     * Cache DOM element references
     */
    _cacheElements() {
        this.elements = {
            panel: document.getElementById('arch-chat-panel'),
            fab: document.getElementById('arch-chat-fab'),
            messages: document.getElementById('arch-chat-messages'),
            input: document.getElementById('arch-chat-input'),
            sendBtn: document.getElementById('arch-chat-send-btn'),
            cancelBtn: document.getElementById('arch-chat-cancel-btn'),
            sessionPopup: document.getElementById('arch-session-popup'),
            sessionList: document.getElementById('arch-session-list'),
            sessionName: document.getElementById('arch-session-name'),
            providerSelect: document.getElementById('arch-chat-provider'),
            modelSelect: document.getElementById('arch-chat-model'),
            attachedContext: document.getElementById('arch-attached-context'),
            attachedList: document.getElementById('arch-attached-list'),
            inputContext: document.getElementById('arch-input-context'),
            contextCount: document.getElementById('arch-context-count'),
            selectedElementsBar: document.getElementById('arch-selected-elements-bar'),
            selectedElementsList: document.getElementById('arch-selected-elements-list'),
            welcome: document.getElementById('arch-chat-welcome'),
        };
    },
    
    /**
     * Attach event listeners
     */
    _attachEventListeners() {
        // Enter to send
        this.elements.input?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!this.isStreaming && this.currentSessionId) this.sendChat();
            }
        });
        
        // Auto-resize textarea
        this.elements.input?.addEventListener('input', (e) => {
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
        });
        
        // Close popup when clicking outside
        document.addEventListener('click', (e) => {
            const popup = this.elements.sessionPopup;
            const dropdown = document.querySelector('.arch-chat-header-dropdown');
            if (popup && dropdown && !popup.contains(e.target) && !dropdown.contains(e.target)) {
                popup.classList.remove('open');
            }
        });
    },
    
    // =========================================================================
    // UI Actions
    // =========================================================================
    
    togglePanel() {
        const isOpen = this.elements.panel?.classList.toggle('open');
        this.elements.fab?.classList.toggle('hidden-fab', isOpen);
        if (isOpen && !this.currentSessionId) {
            this.loadSessions();
        }
    },
    
    toggleSessionPopup() {
        this.elements.sessionPopup?.classList.toggle('open');
    },
    
    setInput(text) {
        if (this.elements.input) {
            this.elements.input.value = text;
            this.elements.input.focus();
        }
    },
    
    // =========================================================================
    // Session Management
    // =========================================================================
    
    async loadSessions() {
        try {
            const resp = await fetch(`/api/projects/${this.projectId}/chat/sessions?feature=${this.featureName}`);
            const sessions = await resp.json();
            this._allSessions = sessions;
            this._renderSessionList();
            
            if (sessions.length > 0 && !this.currentSessionId) {
                await this.loadSession(sessions[0].id);
            }
        } catch (err) {
            console.error('Failed to load sessions:', err);
        }
    },
    
    _renderSessionList() {
        const list = this.elements.sessionList;
        if (!list) return;
        
        if (this._allSessions.length === 0) {
            list.innerHTML = '<div style="padding: 20px; text-align: center; color: #737373; font-size: 0.875rem;">No sessions yet</div>';
            return;
        }
        
        list.innerHTML = this._allSessions.map(s => {
            const date = new Date(s.updated_at).toLocaleDateString();
            const isActive = s.id === this.currentSessionId;
            return `
                <div class="arch-session-item ${isActive ? 'active' : ''}" onclick="ArchChat.selectSession('${s.id}')">
                    <div class="arch-session-item-info">
                        <div class="arch-session-item-name">${this._escapeHtml(s.name)}</div>
                        <div class="arch-session-item-meta">${s.message_count} messages · ${date}</div>
                    </div>
                    <button class="arch-session-item-delete" onclick="event.stopPropagation(); ArchChat.deleteSession('${s.id}')" title="Delete">
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4l8 8M12 4l-8 8"/></svg>
                    </button>
                </div>
            `;
        }).join('');
    },
    
    async selectSession(sessionId) {
        this.toggleSessionPopup();
        if (sessionId === this.currentSessionId) return;
        await this.loadSession(sessionId);
    },
    
    async loadSession(sessionId) {
        try {
            if (this.currentSessionId && this.currentSessionId !== sessionId) {
                fetch(`/api/projects/${this.projectId}/chat/sessions/${this.currentSessionId}/cancel`, { method: 'POST' }).catch(() => {});
            }
            
            const resp = await fetch(`/api/projects/${this.projectId}/chat/sessions/${sessionId}`);
            if (!resp.ok) throw new Error('Session not found');
            const session = await resp.json();
            
            this.currentSessionId = sessionId;
            
            // Update header
            if (this.elements.sessionName) {
                this.elements.sessionName.textContent = session.name;
            }
            
            // Sync provider/model dropdowns
            if (session.provider && this.elements.providerSelect) {
                this.elements.providerSelect.value = session.provider;
                await this.fetchModels(session.provider);
                if (session.model && this.elements.modelSelect) {
                    this.elements.modelSelect.value = session.model;
                }
            }
            
            // Render messages
            if (this.elements.welcome) this.elements.welcome.style.display = 'none';
            if (this.elements.messages) this.elements.messages.innerHTML = '';
            
            session.messages.forEach(m => {
                this.appendMessage(m.role, m.content, false);
            });
            
            this.setChatEnabled(true);
            this.connectSSE(sessionId);
            this._renderSessionList();
        } catch (err) {
            console.error('Failed to load session:', err);
        }
    },
    
    async createNewSession() {
        const provider = this.getSelectedProvider();
        const model = this.elements.modelSelect?.value;
        if (!model) { alert('Select a model first'); return; }
        
        try {
            const resp = await fetch(`/api/projects/${this.projectId}/chat/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    feature_name: this.featureName,
                    provider: provider,
                    model: model,
                }),
            });
            const session = await resp.json();
            
            await this.loadSessions();
            await this.loadSession(session.id);
        } catch (err) {
            console.error('Failed to create session:', err);
        }
    },
    
    async deleteSession(sessionId) {
        if (!confirm('Delete this chat session?')) return;
        try {
            await fetch(`/api/projects/${this.projectId}/chat/sessions/${sessionId}`, { method: 'DELETE' });
            
            if (this.currentSessionId === sessionId) {
                this.disconnectSSE();
                this.currentSessionId = null;
                this.setChatEnabled(false);
                
                // Show welcome state
                if (this.elements.messages) this.elements.messages.innerHTML = '';
                if (this.elements.welcome) this.elements.welcome.style.display = 'flex';
                if (this.elements.sessionName) this.elements.sessionName.textContent = 'New AI chat';
            }
            
            await this.loadSessions();
        } catch (err) {
            console.error('Failed to delete session:', err);
        }
    },
    
    // =========================================================================
    // Provider & Model
    // =========================================================================
    
    getSelectedProvider() {
        return this.elements.providerSelect?.value || 'claude';
    },
    
    onProviderChange() {
        this.fetchModels(this.getSelectedProvider());
    },
    
    async fetchModels(providerName) {
        const thisId = ++this._modelFetchId;
        if (this.elements.modelSelect) {
            this.elements.modelSelect.innerHTML = '<option disabled selected>Loading models...</option>';
        }
        
        try {
            const resp = await fetch(`/api/providers/${providerName}/models`);
            if (thisId !== this._modelFetchId) return;
            if (!resp.ok) throw new Error('Failed');
            const data = await resp.json();
            if (thisId !== this._modelFetchId) return;
            
            if (data.error) {
                if (this.elements.modelSelect) {
                    this.elements.modelSelect.innerHTML = '<option disabled selected>Timed out</option>';
                }
                return;
            }
            
            if (this.elements.modelSelect) {
                this.elements.modelSelect.innerHTML = '';
                data.models.forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m;
                    opt.textContent = m;
                    this.elements.modelSelect.appendChild(opt);
                });
            }
        } catch {
            if (thisId !== this._modelFetchId) return;
            if (this.elements.modelSelect) {
                this.elements.modelSelect.innerHTML = '<option disabled selected>Failed</option>';
            }
        }
    },
    
    // =========================================================================
    // Service Health
    // =========================================================================
    
    async pollServiceHealth() {
        try {
            const resp = await fetch('/api/services/health');
            if (!resp.ok) return;
            const data = await resp.json();
            const services = data.services || [];
            
            this._lastServiceHealth = {};
            services.forEach(svc => {
                this._lastServiceHealth[svc.name] = svc;
                const dotId = svc.name === 'companion' ? 'arch-status-companion' : `arch-status-${svc.name}`;
                const dot = document.getElementById(dotId);
                if (dot) {
                    dot.classList.toggle('online', svc.status === 'running');
                }
            });
            
            this.updateProviderAvailability(services);
        } catch (e) {
            // Silently fail
        }
    },
    
    updateProviderAvailability(services) {
        if (!this.elements.providerSelect || !this.elements.providerSelect.options) return;
        
        for (const opt of this.elements.providerSelect.options) {
            const svcName = opt.value === 'claude' ? 'companion' : opt.value;
            const svc = services.find(s => s.name === svcName);
            if (svc && svc.status !== 'running') {
                opt.disabled = true;
                opt.textContent = opt.textContent.replace(/ \(offline\)$/, '') + ' (offline)';
            } else {
                opt.disabled = false;
                opt.textContent = opt.textContent.replace(/ \(offline\)$/, '');
            }
        }
    },
    
    // =========================================================================
    // SSE Connection
    // =========================================================================
    
    connectSSE(sessionId) {
        this.disconnectSSE();
        const url = `/api/projects/${this.projectId}/chat/sessions/${sessionId}/stream`;
        this.eventSource = new EventSource(url);
        
        this.eventSource.addEventListener('token', (e) => {
            const data = JSON.parse(e.data);
            this.appendStreamToken(data.text);
        });
        
        this.eventSource.addEventListener('message_done', (e) => {
            const data = JSON.parse(e.data);
            this.finalizeStreamMessage(data.content);
        });
        
        this.eventSource.addEventListener('chat_error', (e) => {
            const data = JSON.parse(e.data);
            this.finishStreaming();
            this.appendMessage('error', data.detail, false);
        });
        
        this.eventSource.addEventListener('diagram_changed', (e) => {
            const data = JSON.parse(e.data);
            if (typeof onDiagramChanged === 'function') {
                onDiagramChanged(data.file, data.content);
            }
        });
        
        this.eventSource.addEventListener('diagram_added', (e) => {
            const data = JSON.parse(e.data);
            if (typeof onDiagramAdded === 'function') {
                onDiagramAdded(data.file, data.content);
            }
        });
        
        this.eventSource.addEventListener('diagram_removed', (e) => {
            const data = JSON.parse(e.data);
            if (typeof onDiagramRemoved === 'function') {
                onDiagramRemoved(data.file);
            }
        });
        
        this.eventSource.addEventListener('ping', () => {});
        
        this.eventSource.onerror = () => {
            // Auto-reconnect is handled by EventSource
        };
    },
    
    disconnectSSE() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    },
    
    // =========================================================================
    // Messaging
    // =========================================================================
    
    appendMessage(role, content, scroll = true) {
        if (this.elements.welcome) this.elements.welcome.style.display = 'none';
        if (!this.elements.messages) return;
        
        const div = document.createElement('div');
        div.className = `arch-chat-msg ${role}`;
        
        if (role === 'assistant') {
            div.innerHTML = `
                <div class="arch-msg-avatar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 3c-4.5 0-8 3.5-8 8 0 2.5 1.5 4.5 3 6l-1 4 4-1c1.5.5 3 .5 4.5.5 4.5 0 8-3.5 8-8s-3.5-8-8-8z"/>
                    </svg>
                </div>
                <div class="arch-msg-content">${marked.parse(content)}</div>
            `;
        } else if (role === 'user') {
            div.innerHTML = `<div class="arch-msg-bubble">${this._escapeHtml(content)}</div>`;
        } else if (role === 'error') {
            div.innerHTML = `
                <div class="arch-msg-avatar" style="background: #ef4444;">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 8v4M12 16h.01"/>
                    </svg>
                </div>
                <div class="arch-msg-content">${this._escapeHtml(content)}</div>
            `;
        }
        
        this.elements.messages.appendChild(div);
        if (scroll) this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
        return div;
    },
    
    showThinking() {
        this.hideThinking();
        if (this.elements.welcome) this.elements.welcome.style.display = 'none';
        if (!this.elements.messages) return;
        
        const el = document.createElement('div');
        el.className = 'arch-chat-thinking';
        el.id = 'arch-thinking-indicator';
        el.innerHTML = `
            <div class="arch-thinking-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 3c-4.5 0-8 3.5-8 8 0 2.5 1.5 4.5 3 6l-1 4 4-1c1.5.5 3 .5 4.5.5 4.5 0 8-3.5 8-8s-3.5-8-8-8z"/>
                </svg>
            </div>
            <div class="arch-thinking-content">
                <span>Thinking</span>
                <div class="arch-thinking-dots">
                    <div class="arch-thinking-dot"></div>
                    <div class="arch-thinking-dot"></div>
                    <div class="arch-thinking-dot"></div>
                </div>
            </div>
        `;
        this.elements.messages.appendChild(el);
        this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
    },
    
    hideThinking() {
        const el = document.getElementById('arch-thinking-indicator');
        if (el) el.remove();
    },
    
    appendStreamToken(text) {
        this.hideThinking();
        if (this.elements.welcome) this.elements.welcome.style.display = 'none';
        if (!this.elements.messages) return;
        
        if (!this.streamingMsgEl) {
            this.streamingMsgEl = document.createElement('div');
            this.streamingMsgEl.className = 'arch-chat-msg assistant';
            this.streamingMsgEl.innerHTML = `
                <div class="arch-msg-avatar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 3c-4.5 0-8 3.5-8 8 0 2.5 1.5 4.5 3 6l-1 4 4-1c1.5.5 3 .5 4.5.5 4.5 0 8-3.5 8-8s-3.5-8-8-8z"/>
                    </svg>
                </div>
                <div class="arch-msg-content"></div>
            `;
            this.elements.messages.appendChild(this.streamingMsgEl);
            this.streamingText = '';
            this.isStreaming = true;
        }
        
        this.streamingText += text;
        const contentEl = this.streamingMsgEl.querySelector('.arch-msg-content');
        if (contentEl) {
            contentEl.innerHTML = marked.parse(this.streamingText);
        }
        this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
    },
    
    finalizeStreamMessage(fullContent) {
        if (this.streamingMsgEl) {
            const content = fullContent || this.streamingText;
            const contentEl = this.streamingMsgEl.querySelector('.arch-msg-content');
            if (contentEl) {
                contentEl.innerHTML = marked.parse(content);
            }
        }
        this.finishStreaming();
    },
    
    finishStreaming() {
        this.hideThinking();
        this.streamingMsgEl = null;
        this.streamingText = '';
        this.isStreaming = false;
        this.setChatBusy(false);
    },
    
    async sendChat() {
        if (!this.elements.input || !this.currentSessionId) return;
        
        const message = this.elements.input.value.trim();
        if (!message) return;
        
        this.elements.input.value = '';
        this.appendMessage('user', message);
        this.showThinking();
        
        // Build context (override this in page-specific code)
        const context = this.buildContext ? this.buildContext() : '';
        
        this.setChatBusy(true);
        
        try {
            const resp = await fetch(`/api/projects/${this.projectId}/chat/sessions/${this.currentSessionId}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    context: context || null,
                    provider: this.getSelectedProvider(),
                    model: this.elements.modelSelect?.value || null,
                }),
            });
            
            if (!resp.ok) {
                const detail = await resp.json().catch(() => null);
                this.finishStreaming();
                this.appendMessage('error', detail?.detail || 'Failed to send message');
                this.setChatEnabled(true);
                return;
            }
            // Response streams via SSE
        } catch (err) {
            this.finishStreaming();
            this.appendMessage('error', err.message);
            this.setChatEnabled(true);
        }
    },
    
    async cancelChat() {
        if (!this.currentSessionId) return;
        try {
            await fetch(`/api/projects/${this.projectId}/chat/sessions/${this.currentSessionId}/cancel`, { method: 'POST' });
        } catch {}
        this.finishStreaming();
        if (this.elements.input) this.elements.input.disabled = false;
    },
    
    setChatEnabled(enabled) {
        if (this.elements.input) this.elements.input.disabled = !enabled;
        if (this.elements.sendBtn) this.elements.sendBtn.disabled = !enabled;
    },
    
    setChatBusy(busy) {
        if (this.elements.sendBtn) {
            this.elements.sendBtn.style.display = busy ? 'none' : 'flex';
        }
        if (this.elements.cancelBtn) {
            this.elements.cancelBtn.style.display = busy ? 'flex' : 'none';
        }
        if (this.elements.input) this.elements.input.disabled = busy;
    },
    
    // =========================================================================
    // Utilities
    // =========================================================================
    
    _escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;')
                  .replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;')
                  .replace(/'/g, '&#039;');
    }
};

// Export for use in templates
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ArchChat;
}
