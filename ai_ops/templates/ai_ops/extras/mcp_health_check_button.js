// MCP Health Check Button JavaScript
// This script is automatically wrapped in <script> tags by Nautobot

console.log('MCP Health Check script loaded');

async function checkMCPHealth(event) {
    console.log('=== checkMCPHealth FUNCTION CALLED ===');
    console.log('Event:', event);
    const button = event?.target?.closest('button') || event?.currentTarget;
    if (!button) {
        console.error('Button not found');
        return;
    }
    
    const serverId = button.getAttribute('data-server-id');
    console.log('Server ID:', serverId);
    
    if (!serverId) {
        console.error('No server ID found');
        showMCPNotification('error', 'Configuration error: No server ID');
        return;
    }
    
    // Disable button and show loading
    button.disabled = true;
    const originalHTML = button.innerHTML;
    button.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Checking...';

    try {
        const response = await fetch(`/api/plugins/ai-ops/mcp-servers/${serverId}/health-check/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        console.log('Response data:', data);

        if (data.success) {
            // Update status badge if present
            const statusBadge = document.querySelector('.object-status');
            if (statusBadge) {
                statusBadge.className = 'badge bg-success object-status';
                statusBadge.textContent = 'Healthy';
            }
            // Show success notification
            const message = data.details ? `${data.message}\n${data.details}` : data.message;
            showMCPNotification('success', message);
        } else {
            const statusBadge = document.querySelector('.object-status');
            if (statusBadge) {
                statusBadge.className = 'badge bg-danger object-status';
                statusBadge.textContent = 'Unhealthy';
            }
            // Show error notification
            const message = data.details ? `${data.message}\n${data.details}` : data.message;
            showMCPNotification('error', message);
        }
    } catch (error) {
        console.error('Error in checkMCPHealth:', error);
        showMCPNotification('error', `Health Check Error: ${error.message}`);
    } finally {
        // Re-enable button
        button.disabled = false;
        button.innerHTML = originalHTML;
    }
}

function showMCPNotification(type, message) {
    console.log('=== showMCPNotification CALLED ===');
    console.log('Type:', type);
    console.log('Message:', message);
    
    // Get or create the container
    let container = document.getElementById('mcp-health-toast-container');
    console.log('Container found:', container);
    
    if (!container) {
        console.log('Container not found, creating it');
        container = document.createElement('div');
        container.id = 'mcp-health-toast-container';
        container.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 99999; min-width: 400px; max-width: 600px;';
        document.body.appendChild(container);
        console.log('Container created and added to body');
    }
    
    // Clear existing toasts
    container.innerHTML = '';
    console.log('Container cleared');
    
    // Map notification types to Bootstrap alert classes
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    const icon = type === 'success' ? 'mdi-check-circle' : 'mdi-alert-circle';
    const bgColor = type === 'success' ? '#d1e7dd' : '#f8d7da';
    const borderColor = type === 'success' ? '#badbcc' : '#f5c2c7';
    const textColor = type === 'success' ? '#0f5132' : '#842029';
    
    // Format message: replace newlines with <br>
    const formattedMessage = message.replace(/\n/g, '<br>');
    
    // Create alert element
    const alertId = `mcp-alert-${Date.now()}`;
    const alertDiv = document.createElement('div');
    alertDiv.id = alertId;
    alertDiv.className = `alert ${alertClass} alert-dismissible`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.style.cssText = `
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: ${bgColor};
        border: 1px solid ${borderColor};
        color: ${textColor};
        display: flex;
        align-items: center;
        gap: 0.5rem;
        opacity: 1;
        visibility: visible;
    `;
    
    alertDiv.innerHTML = `
        <span class="mdi ${icon}" style="font-size: 1.5rem; flex-shrink: 0;"></span>
        <div style="flex: 1;">
            <strong>${formattedMessage}</strong>
        </div>
        <button type="button" 
                onclick="document.getElementById('${alertId}').remove()"
                aria-label="Close"
                style="flex-shrink: 0; 
                       background: rgba(0,0,0,0.1);
                       border: 1px solid rgba(0,0,0,0.2);
                       border-radius: 3px;
                       width: 24px;
                       height: 24px;
                       display: flex;
                       align-items: center;
                       justify-content: center;
                       cursor: pointer;
                       opacity: 0.8;
                       padding: 0;
                       margin: 0;
                       color: inherit;
                       font-size: 16px;
                       font-weight: bold;"
                onmouseover="this.style.opacity='1'; this.style.background='rgba(0,0,0,0.15)'"
                onmouseout="this.style.opacity='0.8'; this.style.background='rgba(0,0,0,0.1)'">×</button>
    `;
    
    container.appendChild(alertDiv);
    console.log('Alert element created and appended');
    console.log('Alert div:', alertDiv);
    console.log('Alert in DOM:', document.getElementById(alertId));
    console.log('Container position:', container.getBoundingClientRect());
    
    // Auto-dismiss after 8 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement && alertElement.parentElement) {
            alertElement.style.transition = 'opacity 0.5s';
            alertElement.style.opacity = '0';
            setTimeout(() => {
                if (alertElement && alertElement.parentElement) {
                    alertElement.remove();
                }
            }, 500);
        }
    }, 8000);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
