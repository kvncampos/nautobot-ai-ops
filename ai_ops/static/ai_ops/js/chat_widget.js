// LangGraph Agent Integration
// IIFE pattern used to avoid global scope pollution
(function() {
    // Chat state management
    let chatHistory = [];
    let inactivityTimer = null;
    // AbortController for cancelling in-flight fetch requests
    // When user clears history, we abort any pending request to avoid orphaned operations
    let currentRequestController = null;
    // Get TTL from server config (default 5 minutes if not set)
    const INACTIVITY_TIMEOUT = (window.CHAT_TTL_MINUTES || 5) * 60000; // Convert minutes to milliseconds
    const GRACE_PERIOD = 30000; // 30 seconds grace period
    
    // DOM elements
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-message');
    const clearButton = document.getElementById('clear-chat');
    
    // Get CSRF token
    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
    
    // Load chat history from localStorage on page load
    // NOTE: localStorage is used for POC purposes only. 
    // Production implementation should use server-side storage with proper data retention policies.
    function loadChatHistory() {
        try {
            const saved = localStorage.getItem('nautobot_gpt_chat_history');
            if (saved) {
                const parsed = JSON.parse(saved);
                const now = new Date();
                const ttlMs = (window.CHAT_TTL_MINUTES || 5) * 60000 + GRACE_PERIOD;
                
                // Filter out messages older than TTL + grace period
                const originalLength = parsed.length;
                chatHistory = parsed.filter(msg => {
                    const messageAge = now - new Date(msg.timestamp);
                    return messageAge < ttlMs;
                });
                
                // If messages were filtered out due to expiry, clear backend and show message
                if (chatHistory.length < originalLength && chatHistory.length === 0) {
                    const expiredMinutes = window.CHAT_TTL_MINUTES || 5;
                    clearChatWithMessage(`Previous conversation expired (older than ${expiredMinutes} minutes).`);
                } else if (chatHistory.length < originalLength) {
                    // Some messages expired, update storage
                    saveChatHistory();
                }
                
                renderMessages();
            }
        } catch (e) {
            console.error('Error loading chat history:', e);
        }
    }
    
    // Save chat history to localStorage
    function saveChatHistory() {
        try {
            localStorage.setItem('nautobot_gpt_chat_history', JSON.stringify(chatHistory));
        } catch (e) {
            console.error('Error saving chat history:', e);
        }
    }
    
    // Add a message to the chat
    function addMessage(content, type, isError = false) {
        const message = {
            content: content,
            type: type, // 'human' or 'ai'
            timestamp: new Date().toISOString(),
            isError: isError
        };
        
        chatHistory.push(message);
        saveChatHistory();
        renderMessage(message);
        scrollToBottom();
    }
    
    // Parse markdown to HTML using Marked.js and sanitize output
    function parseMarkdown(text) {
        // Configure marked when available to support GFM (tables, lists, task lists)
        let html = '';
        try {
            if (window.marked && typeof window.marked.parse === 'function') {
                window.marked.setOptions({
                    breaks: true,
                    gfm: true,
                    headerIds: false,
                    mangle: false,
                    smartLists: true
                });
                html = window.marked.parse(text || '');
            } else {
                // Fallback: escape HTML and preserve newlines
                html = (text || '').replace(/&/g, '&amp;')
                                   .replace(/</g, '&lt;')
                                   .replace(/>/g, '&gt;')
                                   .replace(/\n/g, '<br>');
            }
        } catch (e) {
            console.error('Markdown parsing error:', e);
            html = (text || '').replace(/&/g, '&amp;')
                               .replace(/</g, '&lt;')
                               .replace(/>/g, '&gt;')
                               .replace(/\n/g, '<br>');
        }
        // Sanitize HTML output (requires sanitize-html library)
        // Sanitize HTML output if sanitize-html is present. Keep table/list tags.
        if (window.sanitizeHtml) {
            html = window.sanitizeHtml(html, {
                allowedTags: [
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'p', 'a', 'ul', 'ol', 'nl', 'li',
                    'b', 'i', 'strong', 'em', 'strike', 'code', 'hr', 'br', 'div', 'table', 'thead', 'caption',
                    'tbody', 'tr', 'th', 'td', 'pre', 'img', 'span', 'input'
                ],
                allowedAttributes: {
                    a: ['href', 'name', 'target', 'title', 'rel'],
                    img: ['src', 'alt', 'title', 'width', 'height', 'style'],
                    th: ['colspan', 'rowspan', 'style'],
                    td: ['colspan', 'rowspan', 'style'],
                    span: ['class', 'style'],
                    div: ['class', 'style'],
                    input: ['type', 'checked', 'disabled'],
                    '*': ['style']
                },
                allowedSchemes: ['http', 'https', 'mailto'],
                allowProtocolRelative: true
            });
        }
            // Post-process: re-parse fenced code blocks that look like pipe tables
            // (or are tagged as mermaid) so tables render instead of remaining as
            // literal code blocks. This helps when upstream formatting wraps
            // table markdown inside ``` blocks.
            try {
                if (typeof window.DOMParser !== 'undefined') {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const codes = Array.from(doc.querySelectorAll('pre > code'));
                    codes.forEach(code => {
                        const codeText = code.textContent || '';
                        const className = (code.className || '').toLowerCase();

                        const hasPipe = /\|/.test(codeText);
                        const hasSeparator = /(^|\n)\s*[:\-]*[:\-\s]*\|/.test(codeText) || /---/.test(codeText);
                        const looksLikeTable = hasPipe && (hasSeparator || /^\s*\|/.test(codeText));
                        const isMermaid = className.indexOf('language-mermaid') !== -1 || className.indexOf('lang-mermaid') !== -1;

                        if (looksLikeTable || isMermaid) {
                            // Re-parse the inner text as Markdown
                            let replacementHtml = '';
                            try {
                                if (window.marked && typeof window.marked.parse === 'function') {
                                    replacementHtml = window.marked.parse(codeText);
                                } else {
                                    replacementHtml = codeText.replace(/&/g, '&amp;')
                                                               .replace(/</g, '&lt;')
                                                               .replace(/>/g, '&gt;')
                                                               .replace(/\n/g, '<br>');
                                }
                            } catch (err) {
                                replacementHtml = codeText.replace(/&/g, '&amp;')
                                                           .replace(/</g, '&lt;')
                                                           .replace(/>/g, '&gt;')
                                                           .replace(/\n/g, '<br>');
                            }

                            const wrapper = doc.createElement('div');
                            wrapper.innerHTML = replacementHtml;
                            const pre = code.parentElement;
                            if (pre && pre.parentNode) pre.parentNode.replaceChild(wrapper, pre);
                        }
                    });
                    html = doc.body.innerHTML;
                }
            } catch (e) {
                console.warn('Post-processing markdown failed', e);
            }
        return html;
    }
    
    // Render a single message
    function renderMessage(message) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper ' + message.type;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message ' + message.type + '-message';
        
        // Apply error styling if needed
        if (message.isError) {
            messageDiv.classList.add('error-message');
        }
        
        const label = document.createElement('div');
        label.className = 'message-label';
        label.textContent = message.type === 'human' ? 'You' : 'Nautobot Agent';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        // Use pre-wrap for error messages to preserve formatting
        if (message.isError) {
            content.style.whiteSpace = 'pre-wrap';
            content.style.fontFamily = 'monospace';
            content.textContent = message.content;
        } else {
            // Parse markdown for normal messages
            content.innerHTML = parseMarkdown(message.content);

            // --- UI/UX Enhancement: Bootstrap 5 best practices for tables/images ---
            // Make tables responsive and beautiful
            content.querySelectorAll('table').forEach(table => {
                // Wrap table in .table-responsive if not already wrapped
                if (!table.parentElement.classList.contains('table-responsive')) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'table-responsive';
                    table.parentNode.insertBefore(wrapper, table);
                    wrapper.appendChild(table);
                }
                table.classList.add('table', 'table-striped', 'table-hover', 'table-bordered', 'align-middle');
            });
            // Make images responsive and rounded
            content.querySelectorAll('img').forEach(img => {
                img.classList.add('img-fluid', 'rounded');
                img.style.maxWidth = '100%';
                img.style.height = 'auto';
            });
            // Minimal code styling: let CSS handle colors
            content.querySelectorAll('pre').forEach(pre => {
                pre.classList.add('rounded');
                pre.style.overflowX = 'auto';
            });
            content.querySelectorAll('code').forEach(code => {
                code.classList.add('rounded');
            });
        }
        
        messageDiv.appendChild(label);
        messageDiv.appendChild(content);
        wrapper.appendChild(messageDiv);
        
        chatMessages.appendChild(wrapper);
    }
    
    // Render all messages
    function renderMessages() {
        chatMessages.innerHTML = '';
        chatHistory.forEach(message => renderMessage(message));
        scrollToBottom();
    }
    
    // Scroll chat to bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Reset inactivity timer
    function resetInactivityTimer() {
        // Don't set timer if chat is disabled
        if (window.CHAT_ENABLED === false) {
            return;
        }
        
        if (inactivityTimer) {
            clearTimeout(inactivityTimer);
        }
        inactivityTimer = setTimeout(() => {
            // Auto-clear after configured minutes of inactivity
            const ttlMinutes = window.CHAT_TTL_MINUTES || 5;
            clearChatWithMessage(`Session timed out after ${ttlMinutes} minutes of inactivity.`);
        }, INACTIVITY_TIMEOUT);
    }
    
    // Handle sending a message
    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;
        
        // Check if input is disabled (chat not enabled)
        if (chatInput.disabled) return;
        
        // Reset inactivity timer
        resetInactivityTimer();
        
        // Add human message
        addMessage(message, 'human');
        chatInput.value = '';
        
        // Disable input and button, show loading
        chatInput.disabled = true;
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Thinking...';
        
        // Create new AbortController for this request
        currentRequestController = new AbortController();
        
        try {
            // Call backend API
            const formData = new FormData();
            formData.append('message', message);
            formData.append('csrfmiddlewaretoken', getCSRFToken());
            
            const response = await fetch('/plugins/ai-ops/chat/message/', {
                method: 'POST',
                body: formData,
                signal: currentRequestController.signal,
            });
            
            const data = await response.json();
            
            if (data.error) {
                // Display technical error in red
                addMessage(`ERROR: ${data.error}`, 'ai', true);
            } else {
                // Display agent response
                addMessage(data.response, 'ai');
            }
        } catch (error) {
            // Handle abort gracefully - don't show error if request was cancelled
            if (error.name === 'AbortError') {
                console.log('Request was cancelled by user');
                // Don't show error message - clearChatWithMessage will handle the UI
            } else {
                addMessage(`ERROR: Failed to communicate with server: ${error.message}`, 'ai', true);
            }
        } finally {
            // Clear the controller reference
            currentRequestController = null;
            // Re-enable input and button
            chatInput.disabled = false;
            sendButton.disabled = false;
            sendButton.innerHTML = '<i class="mdi mdi-send"></i> Send';
            chatInput.focus();
        }
    }
    
    // Clear chat history with custom message
    async function clearChatWithMessage(message) {
        // Abort any pending request before clearing
        // This ensures we don't leave orphaned requests running on the server
        if (currentRequestController) {
            currentRequestController.abort();
            currentRequestController = null;
        }
        
        // Update clear button to show stopping state
        const originalClearButtonHTML = clearButton.innerHTML;
        clearButton.disabled = true;
        clearButton.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Stopping...';
        
        try {
            // Call backend to clear server-side cache
            // This also signals cancellation to any in-progress request
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', getCSRFToken());
            
            await fetch('/plugins/ai-ops/chat/clear/', {
                method: 'POST',
                body: formData,
            });
        } catch (error) {
            console.error('Error clearing chat on server:', error);
        } finally {
            // Restore clear button state
            clearButton.disabled = false;
            clearButton.innerHTML = originalClearButtonHTML;
        }
        
        // Re-enable send button and input if they were disabled during a request
        chatInput.disabled = false;
        sendButton.disabled = false;
        sendButton.innerHTML = '<i class="mdi mdi-send"></i> Send';
        
        // Clear local storage
        chatHistory = [];
        saveChatHistory();
        chatMessages.innerHTML = '';
        
        // Reset inactivity timer
        resetInactivityTimer();
        
        // Show message
        addMessage(message, 'ai');
    }
    
    // Clear chat history
    function clearChat() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            clearChatWithMessage('Chat history cleared. How can I help you today?');
        }
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    clearButton.addEventListener('click', clearChat);
    
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Initialize

    // Ensure Marked.js is available before rendering markdown-heavy content.
    function loadMarkedScript() {
        return new Promise((resolve, reject) => {
            if (window.marked) return resolve(window.marked);
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js';
            script.async = true;
            script.onload = () => resolve(window.marked);
            script.onerror = () => reject(new Error('Failed to load Marked.js'));
            document.head.appendChild(script);
        });
    }

    // Try to load marked (if not already present) and then initialize rendering.
    loadMarkedScript().catch((err) => {
        console.warn('Marked.js not available, messages will use plain text fallback.', err);
    }).finally(() => {
        loadChatHistory();
        // Start inactivity timer only if chat is enabled
        if (window.CHAT_ENABLED !== false) {
            resetInactivityTimer();
        }
    });

    // Theme sync: update chat widget dark/light mode based on Nautobot core theme
    function updateChatTheme() {
        // Nautobot sets data-bs-theme or data-theme on <body> or <html>
        const theme = document.body.getAttribute('data-bs-theme') || document.body.getAttribute('data-theme') || document.documentElement.getAttribute('data-bs-theme') || document.documentElement.getAttribute('data-theme');
        const container = document.getElementById('chat-messages');
        if (!container) return;
        if (theme === 'dark') {
            container.setAttribute('data-theme', 'dark');
        } else if (theme === 'light') {
            container.setAttribute('data-theme', 'light');
        } else {
            // Remove explicit attribute to inherit defaults
            container.removeAttribute('data-theme');
        }
    }

    // Initial theme sync
    updateChatTheme();

    // Listen for theme changes (MutationObserver)
    const themeObserver = new MutationObserver(updateChatTheme);
    themeObserver.observe(document.body, { attributes: true, attributeFilter: ['data-bs-theme', 'data-theme'] });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-bs-theme', 'data-theme'] });

    // If no messages, show welcome message
    if (chatHistory.length === 0) {
        // Check if chat is enabled (set by template)
        const chatEnabled = window.CHAT_ENABLED !== undefined ? window.CHAT_ENABLED : true;

        if (chatEnabled) {
            addMessage("Welcome to Nautobot GPT! I can help you query and interact with Nautobot APIs. Type a message to get started.", 'ai');
        } else {
            // Determine what's missing and show appropriate error message
            const hasDefaultModel = window.HAS_DEFAULT_MODEL !== undefined ? window.HAS_DEFAULT_MODEL : true;

            let errorMessage = "Chat is currently disabled. ";

            if (!hasDefaultModel) {
                errorMessage += "Please configure a default LLM model to enable the AI Chat Agent.";
            } else {
                errorMessage += "Please check your configuration.";
            }

            addMessage(errorMessage, 'ai', true);
        }
    }

    // Start inactivity timer only if chat is enabled
    if (window.CHAT_ENABLED !== false) {
        resetInactivityTimer();
    }
})();
