/**
 * MCP Cache Clear Button - Admin functionality for clearing MCP client cache
 * 
 * Features:
 * - 30-second UI lock with countdown timer
 * - Persists lock state across page refreshes using localStorage
 * - Integrates with Nautobot toast notifications
 * - CSRF token handling for secure POST requests
 */

const LOCK_KEY = 'mcp_cache_clear_lock';
const LOCK_DURATION = 30000; // 30 seconds

/**
 * Check if the button should be locked and update UI accordingly
 * @returns {boolean} True if button is locked, false otherwise
 */
function checkButtonLock() {
    const lockTimestamp = localStorage.getItem(LOCK_KEY);
    if (lockTimestamp) {
        const elapsed = Date.now() - parseInt(lockTimestamp);
        if (elapsed < LOCK_DURATION) {
            const remaining = Math.ceil((LOCK_DURATION - elapsed) / 1000);
            const btn = document.getElementById('clear-mcp-cache-btn');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<i class="mdi mdi-timer-sand"></i> Wait ${remaining}s`;
                
                // Schedule re-check
                setTimeout(checkButtonLock, 1000);
            }
            return true;
        }
        // Lock expired, remove it
        localStorage.removeItem(LOCK_KEY);
    }
    return false;
}

/**
 * Handle MCP cache clear button click
 * @param {Event} event - Click event
 */
async function clearMCPCache(event) {
    event.preventDefault();
    const btn = event.currentTarget;
    
    // Check if locked
    if (checkButtonLock()) {
        return;
    }
    
    if (!confirm('Clear MCP client cache? This will force reconnection to all healthy MCP servers.')) {
        return;
    }
    
    // Lock the button
    localStorage.setItem(LOCK_KEY, Date.now().toString());
    btn.disabled = true;
    btn.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Clearing...';
    
    try {
        // Get CSRF token from page
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                         document.querySelector('meta[name="csrf-token"]')?.content || '';
        
        // Get clear cache URL from button's data attribute
        const clearCacheUrl = btn.getAttribute('data-clear-cache-url');
        
        const response = await fetch(clearCacheUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show success toast (Nautobot style)
            const message = `Successfully cleared cache for ${data.cleared_count} server(s)`;
            if (window.Nautobot && window.Nautobot.showToast) {
                window.Nautobot.showToast('success', message);
            } else {
                alert(message);
            }
            
            // Start countdown
            checkButtonLock();
        } else {
            throw new Error(data.error || 'Unknown error');
        }
    } catch (error) {
        localStorage.removeItem(LOCK_KEY);
        btn.disabled = false;
        btn.innerHTML = '<i class="mdi mdi-delete-sweep"></i> Clear MCP Cache';
        
        const errorMsg = 'Failed to clear cache: ' + error.message;
        if (window.Nautobot && window.Nautobot.showToast) {
            window.Nautobot.showToast('error', errorMsg);
        } else {
            alert(errorMsg);
        }
    }
}

// Check lock status on page load
document.addEventListener('DOMContentLoaded', function() {
    checkButtonLock();
});
