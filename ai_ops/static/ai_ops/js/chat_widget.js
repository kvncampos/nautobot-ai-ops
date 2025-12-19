// LangGraph Agent Integration
// IIFE pattern used to avoid global scope pollution
(function() {
    // Chat state management
    let chatHistory = [];
    let inactivityTimer = null;
    const INACTIVITY_TIMEOUT = 300000; // 5 minutes in milliseconds
    
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
                chatHistory = JSON.parse(saved);
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
    
    // Parse markdown to HTML using Marked.js library
    function parseMarkdown(text) {
        // Configure marked options
        marked.setOptions({
            breaks: true,        // Convert \n to <br>
            gfm: true,          // GitHub Flavored Markdown
            headerIds: false,   // Don't add IDs to headers
            mangle: false,      // Don't escape autolinked email addresses
            sanitize: false     // DOMPurify handles sanitization if needed
        });
        
        try {
            return marked.parse(text);
        } catch (e) {
            console.error('Markdown parsing error:', e);
            // Fallback to escaped text if parsing fails
            return text.replace(/&/g, '&amp;')
                      .replace(/</g, '&lt;')
                      .replace(/>/g, '&gt;')
                      .replace(/\n/g, '<br>');
        }
    }
    
    // Render a single message
    function renderMessage(message) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper ' + message.type;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message ' + message.type + '-message';
        
        // Apply error styling if needed
        if (message.isError) {
            messageDiv.style.backgroundColor = '#ffebee';
            messageDiv.style.borderColor = '#ef5350';
            messageDiv.style.color = '#c62828';
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
            // Auto-clear after 5 minutes of inactivity
            clearChatWithMessage('Session timed out after 5 minutes of inactivity.');
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
        
        try {
            // Call backend API
            const formData = new FormData();
            formData.append('message', message);
            formData.append('csrfmiddlewaretoken', getCSRFToken());
            
            const response = await fetch('/plugins/ai-ops/chat/message/', {
                method: 'POST',
                body: formData,
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
            addMessage(`ERROR: Failed to communicate with server: ${error.message}`, 'ai', true);
        } finally {
            // Re-enable input and button
            chatInput.disabled = false;
            sendButton.disabled = false;
            sendButton.innerHTML = '<i class="mdi mdi-send"></i> Send';
            chatInput.focus();
        }
    }
    
    // Clear chat history with custom message
    async function clearChatWithMessage(message) {
        try {
            // Call backend to clear server-side cache
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', getCSRFToken());
            
            await fetch('/plugins/ai-ops/chat/clear/', {
                method: 'POST',
                body: formData,
            });
        } catch (error) {
            console.error('Error clearing chat on server:', error);
        }
        
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
    loadChatHistory();
    
    // If no messages, show welcome message
    if (chatHistory.length === 0) {
        // Check if chat is enabled (set by template)
        const chatEnabled = window.CHAT_ENABLED !== undefined ? window.CHAT_ENABLED : true;
        
        if (chatEnabled) {
            addMessage("Welcome to Nautobot GPT! I can help you query and interact with Nautobot APIs. Type a message to get started.", 'ai');
        } else {
            // Determine what's missing and show appropriate error message
            const hasDefaultModel = window.HAS_DEFAULT_MODEL !== undefined ? window.HAS_DEFAULT_MODEL : true;
            const hasHealthyMcp = window.HAS_HEALTHY_MCP !== undefined ? window.HAS_HEALTHY_MCP : true;
            
            let errorMessage = "Chat is currently disabled. ";
            
            if (!hasDefaultModel && !hasHealthyMcp) {
                errorMessage += "Please configure a default LLM model and ensure at least one MCP server has a 'Healthy' status to enable the AI Chat Agent.";
            } else if (!hasDefaultModel) {
                errorMessage += "Please configure a default LLM model to enable the AI Chat Agent.";
            } else if (!hasHealthyMcp) {
                errorMessage += "No healthy MCP servers are available. Please ensure at least one MCP server has a 'Healthy' status to enable the AI Chat Agent.";
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
