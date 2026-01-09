/**
 * Dynamic middleware configuration loader
 * Fetches and displays default configuration templates when user selects a middleware type
 */
(function() {
    'use strict';
    
    document.addEventListener('DOMContentLoaded', function() {
        // Get the middleware select element
        const middlewareSelect = document.querySelector('select[name="middleware"]');
        const defaultConfigTextarea = document.querySelector('textarea[name="default_config_display"]');
        
        if (!middlewareSelect || !defaultConfigTextarea) {
            console.log('Middleware select or default_config_display textarea not found');
            return;
        }
        
        console.log('Middleware config loader initialized');
        
        /**
         * Fetch and display default configuration for selected middleware type
         * @param {string} middlewareTypeId - The ID of the selected middleware type
         */
        async function loadDefaultConfig(middlewareTypeId) {
            if (!middlewareTypeId) {
                defaultConfigTextarea.value = 'Select a middleware type above to see example configuration';
                return;
            }
            
            try {
                // Fetch default config from API
                const response = await fetch(`/api/plugins/ai-ops/middleware-types/${middlewareTypeId}/default-config/`);
                
                if (!response.ok) {
                    console.error('Failed to fetch default config:', response.statusText);
                    defaultConfigTextarea.value = 'Error loading configuration';
                    return;
                }
                
                const data = await response.json();
                
                // Update the readonly display field
                if (data.default_config) {
                    defaultConfigTextarea.value = JSON.stringify(data.default_config, null, 2);
                } else {
                    defaultConfigTextarea.value = 'No default configuration available for this middleware type';
                }
            } catch (error) {
                console.error('Error loading default config:', error);
                defaultConfigTextarea.value = 'Error loading configuration';
            }
        }
        
        // Load default config when middleware type changes
        middlewareSelect.addEventListener('change', function() {
            const selectedId = this.value;
            console.log('Middleware changed to:', selectedId);
            loadDefaultConfig(selectedId);
        });
        
        // Load default config on page load if middleware is pre-selected
        if (middlewareSelect.value) {
            console.log('Pre-selected middleware:', middlewareSelect.value);
            loadDefaultConfig(middlewareSelect.value);
        }
    });
})();
