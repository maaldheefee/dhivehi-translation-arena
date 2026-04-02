/**
 * Settings Management for Dhivehi Translation Arena
 * Handles model visibility and auto-selection configuration.
 */

const Settings = {
    // Default values
    defaults: {
        hiddenModels: [],    // Array of model keys to hide
        autoSelectCount: 6,  // Number of models to auto-select
    },

    // Current state
    state: {
        hiddenModels: [],
        autoSelectCount: 6,
    },

    // Storage key
    STORAGE_KEY: 'arena_settings',

    /**
     * Initialize settings from localStorage and setup UI
     */
    init() {
        this.load();
        this.setupModal();
        this.bindEvents();
    },

    /**
     * Load settings from localStorage
     */
    load() {
        try {
            const saved = localStorage.getItem(this.STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                this.state = { ...this.defaults, ...parsed };
                // Ensure hiddenModels is always an array
                if (!Array.isArray(this.state.hiddenModels)) {
                    this.state.hiddenModels = [];
                }
            } else {
                this.state = { ...this.defaults };
            }
        } catch (e) {
            console.error('Failed to load settings:', e);
            this.state = { ...this.defaults };
        }
    },

    /**
     * Save current state to localStorage
     */
    save() {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.state));
        } catch (e) {
            console.error('Failed to save settings:', e);
        }
    },

    /**
     * Get settings for API requests
     */
    getQueryParams() {
        return {
            hidden: this.state.hiddenModels.join(','),
            count: this.state.autoSelectCount
        };
    },

    /**
     * Toggle model visibility
     */
    toggleModel(modelKey) {
        const index = this.state.hiddenModels.indexOf(modelKey);
        if (index > -1) {
            this.state.hiddenModels.splice(index, 1);
        } else {
            this.state.hiddenModels.push(modelKey);
        }
        this.save();
        this.updateVisibilityUI(modelKey);
    },

    /**
     * Check if a model is hidden
     */
    isHidden(modelKey) {
        return this.state.hiddenModels.includes(modelKey);
    },

    /**
     * Create and inject the settings modal into the DOM
     */
    setupModal() {
        if (document.getElementById('settings-modal')) return;

        const modalHtml = `
            <div id="settings-modal" class="modal-overlay hidden">
                <div class="modal-container scrollable">
                    <div class="modal-header">
                        <h3>${window.t('settings_header') || 'Settings'}</h3>
                        <button id="close-settings" class="icon-btn">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="settings-section">
                            <label class="settings-label">
                                ${window.t('auto_select_count') || 'Number of models to auto-select'}:
                                <input type="number" id="auto-select-input" min="1" max="20" value="${this.state.autoSelectCount}" class="form-input sm-input">
                            </label>
                        </div>
                        <div class="settings-section">
                            <h4>${window.t('model_visibility') || 'Model Visibility'}</h4>
                            <p class="settings-help">${window.t('model_visibility_help') || 'Uncheck models to hide them from the main page and stats.'}</p>
                            <div id="settings-model-list" class="settings-list">
                                <div class="loader-sm">${window.t('loading_models') || 'Loading models...'}</div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button id="save-settings" class="btn primary full-width">${window.t('save_and_reload') || 'Save & Reload'}</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    },

    /**
     * Populate the model list in the settings modal
     */
    async populateModelList() {
        const listContainer = document.getElementById('settings-model-list');
        if (!listContainer) return;

        try {
            const res = await fetch('/get_available_models');
            const data = await res.json();
            
            if (!data.models) throw new Error('No models found');

            listContainer.innerHTML = '';
            
            // Group models by base_model for better UI
            const groups = {};
            Object.entries(data.models).forEach(([key, model]) => {
                const groupName = model.base_model || 'Other';
                if (!groups[groupName]) groups[groupName] = [];
                groups[groupName].push({ key, ...model });
            });

            Object.entries(groups).forEach(([groupName, models]) => {
                const groupEl = document.createElement('div');
                groupEl.className = 'settings-group';
                groupEl.innerHTML = `<h5>${groupName}</h5>`;
                
                models.forEach(model => {
                    const row = document.createElement('div');
                    row.className = 'settings-row';
                    const isChecked = !this.isHidden(model.key);
                    
                    row.innerHTML = `
                        <span class="settings-model-name">${model.name || model.key}</span>
                        <label class="toggle-switch">
                            <input type="checkbox" class="model-toggle" data-key="${model.key}" ${isChecked ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                        </label>
                    `;
                    groupEl.appendChild(row);
                });
                listContainer.appendChild(groupEl);
            });
        } catch (e) {
            console.error('Failed to populate model list:', e);
            listContainer.innerHTML = '<p class="error-msg">Failed to load models.</p>';
        }
    },

    /**
     * Bind DOM events
     */
    bindEvents() {
        const modal = document.getElementById('settings-modal');
        const openBtn = document.getElementById('open-settings-btn');
        const closeBtn = document.getElementById('close-settings');
        const saveBtn = document.getElementById('save-settings');
        const countInput = document.getElementById('auto-select-input');

        if (openBtn) {
            openBtn.addEventListener('click', (e) => {
                e.preventDefault();
                modal.classList.remove('hidden');
                this.populateModelList();
                document.body.style.overflow = 'hidden'; // Prevent scroll
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.classList.add('hidden');
                document.body.style.overflow = '';
            });
        }

        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.add('hidden');
                    document.body.style.overflow = '';
                }
            });
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                // Update count
                const count = parseInt(countInput.value, 10);
                if (!Number.isNaN(count) && count >= 1) {
                    this.state.autoSelectCount = count;
                }

                // Update hidden models from checkboxes
                const checkboxes = document.querySelectorAll('.model-toggle');
                const hidden = [];
                checkboxes.forEach(cb => {
                    if (!cb.checked) {
                        hidden.push(cb.getAttribute('data-key'));
                    }
                });
                this.state.hiddenModels = hidden;

                this.save();
                window.location.reload();
            });
        }
    },
    
    updateVisibilityUI() {
        // Not implemented: usually we just reload because many things change
    }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    Settings.init();
});

// Export for global use
window.Settings = Settings;
